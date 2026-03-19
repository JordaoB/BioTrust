from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from starlette.testclient import TestClient

from backend.database import get_database
from backend.main import app
from backend.routes import liveness as liveness_routes
from backend.routes import transactions as transactions_routes
from backend.services.transaction_settlement import settle_transaction_by_id
from src.core.risk_engine import RiskEngine


@dataclass
class FakeInsertOneResult:
    inserted_id: Any


@dataclass
class FakeUpdateResult:
    matched_count: int
    modified_count: int


class FakeCursor:
    def __init__(self, docs: List[Dict[str, Any]]):
        self.docs = docs
        self._skip = 0
        self._limit: Optional[int] = None

    def sort(self, field: str, direction: int) -> "FakeCursor":
        reverse = direction == -1
        self.docs.sort(key=lambda d: _get_by_path(d, field), reverse=reverse)
        return self

    def skip(self, n: int) -> "FakeCursor":
        self._skip = n
        return self

    def limit(self, n: int) -> "FakeCursor":
        self._limit = n
        return self

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        docs = self.docs[self._skip :]
        if self._limit is not None:
            docs = docs[: self._limit]
        if length is not None:
            docs = docs[:length]
        return [copy.deepcopy(d) for d in docs]


class FakeCollection:
    def __init__(self, seed: Optional[List[Dict[str, Any]]] = None):
        self.docs: List[Dict[str, Any]] = [copy.deepcopy(d) for d in (seed or [])]
        self._id_counter = 1000

    async def find_one(self, query: Dict[str, Any], sort=None):
        matches = [d for d in self.docs if _matches_query(d, query)]
        if sort:
            field, direction = sort[0]
            reverse = direction == -1
            matches.sort(key=lambda d: _get_by_path(d, field), reverse=reverse)
        return copy.deepcopy(matches[0]) if matches else None

    async def insert_one(self, doc: Dict[str, Any]):
        to_insert = copy.deepcopy(doc)
        if "_id" not in to_insert:
            self._id_counter += 1
            to_insert["_id"] = f"tx_{self._id_counter}"
        self.docs.append(to_insert)
        return FakeInsertOneResult(inserted_id=to_insert["_id"])

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        for idx, current in enumerate(self.docs):
            if _matches_query(current, query):
                before = copy.deepcopy(current)
                _apply_update(current, update)
                self.docs[idx] = current
                modified = 1 if before != current else 0
                return FakeUpdateResult(matched_count=1, modified_count=modified)
        return FakeUpdateResult(matched_count=0, modified_count=0)

    async def find_one_and_update(self, query: Dict[str, Any], update: Dict[str, Any]):
        for idx, current in enumerate(self.docs):
            if _matches_query(current, query):
                _apply_update(current, update)
                self.docs[idx] = current
                return copy.deepcopy(current)
        return None

    async def count_documents(self, query: Dict[str, Any]):
        return sum(1 for d in self.docs if _matches_query(d, query))

    def find(self, query: Dict[str, Any]):
        return FakeCursor([copy.deepcopy(d) for d in self.docs if _matches_query(d, query)])


class FakeDB:
    def __init__(self):
        sender = {
            "_id": "user_sender",
            "email": "sender@example.com",
            "name": "Sender",
            "home_location": {"city": "Lisboa", "country": "Portugal", "lat": 38.7223, "lon": -9.1393},
            "average_transaction": 50.0,
            "max_transaction": 500.0,
            "transactions_today": 0,
            "cards": [
                {
                    "is_default": True,
                    "balance": 1000.0,
                    "daily_spent": 0.0,
                    "daily_limit": 5000.0,
                    "max_transaction": 2000.0,
                    "last_reset": datetime.utcnow().date().isoformat(),
                }
            ],
            "location_history": [],
            "liveness_verifications_count": 0,
        }

        recipient = {
            "_id": "user_recipient",
            "email": "recipient@example.com",
            "name": "Recipient",
            "home_location": {"city": "Porto", "country": "Portugal", "lat": 41.1579, "lon": -8.6291},
            "cards": [
                {
                    "is_default": True,
                    "balance": 500.0,
                    "daily_spent": 0.0,
                    "daily_limit": 5000.0,
                    "max_transaction": 2000.0,
                    "last_reset": datetime.utcnow().date().isoformat(),
                }
            ],
            "location_history": [],
            "liveness_verifications_count": 0,
        }

        self.users = FakeCollection([sender, recipient])
        self.transactions = FakeCollection([])
        self.merchants = FakeCollection([])
        self.sessions = FakeCollection([])


class FakeDetectorSuccess:
    def verify(self, **kwargs):
        return {
            "success": True,
            "message": "ok",
            "challenges_completed": ["blink", "smile"],
            "heart_rate": 70.0,
            "heart_rate_confidence": 0.92,
            "anti_spoofing": {"ok": True},
        }


class FakeDetectorFail:
    def verify(self, **kwargs):
        return {
            "success": False,
            "message": "failed",
            "challenges_completed": ["blink"],
            "heart_rate": 68.0,
            "heart_rate_confidence": 0.88,
            "anti_spoofing": {"ok": True},
        }


async def _noop_async(*args, **kwargs):
    return None


def _make_client(monkeypatch, fake_db: FakeDB) -> TestClient:
    from backend import main as main_module

    monkeypatch.setattr(main_module, "connect_to_mongo", _noop_async)
    monkeypatch.setattr(main_module, "close_mongo_connection", _noop_async)
    monkeypatch.setattr(transactions_routes, "ANOMALY_DETECTOR_AVAILABLE", False)

    app.dependency_overrides[get_database] = lambda: fake_db
    return TestClient(app)


def _cleanup_client(client: TestClient):
    client.close()
    app.dependency_overrides.clear()


def _base_transaction_payload(amount: float) -> Dict[str, Any]:
    return {
        "user_id": "user_sender",
        "card_index": 0,
        "amount": amount,
        "type": "transfer",
        "recipient_email": "recipient@example.com",
        "user_location": {"city": "Lisboa", "lat": 38.7223, "lon": -9.1393},
    }


def test_auto_approved_transaction_debits_card(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(
        transactions_routes.risk_engine,
        "analyze_transaction",
        lambda tx: {"risk_score": 10},
    )

    client = _make_client(monkeypatch, fake_db)
    try:
        resp = client.post("/api/transactions/", json=_base_transaction_payload(50.0))
        assert resp.status_code == 201

        body = resp.json()
        assert body["status"] == "approved"
        assert body["liveness_required"] is False

        sender = asyncio.run(fake_db.users.find_one({"_id": "user_sender"}))
        assert sender["cards"][0]["balance"] == 950.0

        tx = asyncio.run(fake_db.transactions.find_one({"_id": body["_id"]}))
        assert tx["settlement"]["applied"] is True
        assert tx["settlement"]["state"] == "completed"
    finally:
        _cleanup_client(client)


def test_liveness_success_debits_sender_and_credits_recipient(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(
        transactions_routes.risk_engine,
        "analyze_transaction",
        lambda tx: {"risk_score": 50},
    )
    monkeypatch.setattr(liveness_routes, "LivenessDetectorV3", FakeDetectorSuccess)

    client = _make_client(monkeypatch, fake_db)
    try:
        create_resp = client.post("/api/transactions/", json=_base_transaction_payload(200.0))
        assert create_resp.status_code == 201
        tx = create_resp.json()
        assert tx["status"] == "pending"
        assert tx["liveness_required"] is True

        verify_resp = client.post(f"/api/liveness/verify/{tx['_id']}")
        assert verify_resp.status_code == 200
        assert verify_resp.json()["success"] is True

        sender = asyncio.run(fake_db.users.find_one({"_id": "user_sender"}))
        recipient = asyncio.run(fake_db.users.find_one({"_id": "user_recipient"}))

        assert sender["cards"][0]["balance"] == 800.0
        assert recipient["cards"][0]["balance"] == 700.0
    finally:
        _cleanup_client(client)


def test_liveness_failure_does_not_change_balances(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(
        transactions_routes.risk_engine,
        "analyze_transaction",
        lambda tx: {"risk_score": 55},
    )
    monkeypatch.setattr(liveness_routes, "LivenessDetectorV3", FakeDetectorFail)

    client = _make_client(monkeypatch, fake_db)
    try:
        create_resp = client.post("/api/transactions/", json=_base_transaction_payload(120.0))
        assert create_resp.status_code == 201
        tx = create_resp.json()

        verify_resp = client.post(f"/api/liveness/verify/{tx['_id']}")
        assert verify_resp.status_code == 200
        assert verify_resp.json()["success"] is False

        sender = asyncio.run(fake_db.users.find_one({"_id": "user_sender"}))
        recipient = asyncio.run(fake_db.users.find_one({"_id": "user_recipient"}))
        latest_tx = asyncio.run(fake_db.transactions.find_one({"_id": tx["_id"]}))

        assert sender["cards"][0]["balance"] == 1000.0
        assert recipient["cards"][0]["balance"] == 500.0
        assert latest_tx["status"] == "rejected"
        assert latest_tx["settlement"]["applied"] is False
    finally:
        _cleanup_client(client)


def test_settlement_is_idempotent_no_double_debit(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(
        transactions_routes.risk_engine,
        "analyze_transaction",
        lambda tx: {"risk_score": 10},
    )

    client = _make_client(monkeypatch, fake_db)
    try:
        create_resp = client.post("/api/transactions/", json=_base_transaction_payload(25.0))
        assert create_resp.status_code == 201
        tx_id = create_resp.json()["_id"]

        sender_before = asyncio.run(fake_db.users.find_one({"_id": "user_sender"}))
        assert sender_before["cards"][0]["balance"] == 975.0

        result = asyncio.run(
            settle_transaction_by_id(
                db=fake_db,
                transaction_id=tx_id,
                source="idempotency_test",
            )
        )
        assert result["settled"] is False
        assert result["reason"] == "already_settled"

        sender_after = asyncio.run(fake_db.users.find_one({"_id": "user_sender"}))
        assert sender_after["cards"][0]["balance"] == 975.0
    finally:
        _cleanup_client(client)


def test_risk_engine_thresholds_new_rules():
    engine = RiskEngine()

    low_risk = engine.analyze_transaction(
        {
            "amount": 10.0,
            "location": {"city": "Lisboa", "country": "Portugal", "lat": 38.7223, "lon": -9.1393},
            "timestamp": datetime.utcnow().replace(hour=14, minute=0, second=0, microsecond=0),
            "recipient_email": "trusted@example.com",
            "user_profile": {
                "average_transaction": 20.0,
                "home_location": {"city": "Lisboa", "country": "Portugal", "lat": 38.7223, "lon": -9.1393},
                "last_transaction_location": {"city": "Lisboa", "country": "Portugal", "lat": 38.7223, "lon": -9.1393},
                "last_transaction_time": datetime.utcnow() - timedelta(hours=5),
                "recent_transactions": [],
                "recipient_history": {"trusted@example.com": 12},
                "merchant_history": {},
            },
        }
    )

    assert low_risk["risk_score"] <= 25
    assert low_risk["risk_level"] == "low"
    assert low_risk["liveness_required"] is False

    now = datetime.utcnow()
    high_risk = engine.analyze_transaction(
        {
            "amount": 650.0,
            "location": {"city": "Paris", "country": "France", "lat": 48.8566, "lon": 2.3522},
            "timestamp": now.replace(hour=3, minute=0, second=0, microsecond=0),
            "recipient_email": "new@example.com",
            "user_profile": {
                "average_transaction": 50.0,
                "home_location": {"city": "Lisboa", "country": "Portugal", "lat": 38.7223, "lon": -9.1393},
                "last_transaction_location": {"city": "Lisboa", "country": "Portugal", "lat": 38.7223, "lon": -9.1393},
                "last_transaction_time": now - timedelta(minutes=5),
                "recent_transactions": [
                    {"created_at": now - timedelta(minutes=50), "recipient_email": "new@example.com"},
                    {"created_at": now - timedelta(minutes=40), "recipient_email": "new@example.com"},
                    {"created_at": now - timedelta(minutes=30), "recipient_email": "new@example.com"},
                    {"created_at": now - timedelta(minutes=20), "recipient_email": "other@example.com"},
                ],
                "recipient_history": {},
                "merchant_history": {},
            },
        }
    )

    assert high_risk["risk_score"] >= 60
    assert high_risk["risk_level"] in {"medium", "high"}
    assert high_risk["liveness_required"] is True


# ---- Helpers ----

def _get_by_path(doc: Dict[str, Any], path: str) -> Any:
    current = doc
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _set_by_path(doc: Dict[str, Any], path: str, value: Any):
    parts = path.split(".")
    current: Any = doc

    for i, part in enumerate(parts[:-1]):
        next_part = parts[i + 1]
        if isinstance(current, list):
            idx = int(part)
            while len(current) <= idx:
                current.append({})
            current = current[idx]
            continue

        if part not in current or current[part] is None:
            current[part] = [] if next_part.isdigit() else {}
        current = current[part]

    last = parts[-1]
    if isinstance(current, list):
        idx = int(last)
        while len(current) <= idx:
            current.append(None)
        current[idx] = value
    else:
        current[last] = value


def _inc_by_path(doc: Dict[str, Any], path: str, amount: float):
    current = _get_by_path(doc, path)
    if current is None:
        current = 0
    _set_by_path(doc, path, current + amount)


def _matches_query(doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches_query(doc, sub) for sub in expected):
                return False
            continue

        actual = _get_by_path(doc, key)

        if isinstance(expected, dict):
            for op, val in expected.items():
                if op == "$gte":
                    if actual is None or actual < val:
                        return False
                elif op == "$ne":
                    if actual == val:
                        return False
                elif op == "$exists":
                    exists = actual is not None
                    if bool(val) != exists:
                        return False
                else:
                    raise AssertionError(f"Unsupported query operator: {op}")
        else:
            if actual != expected:
                return False

    return True


def _apply_update(doc: Dict[str, Any], update: Dict[str, Any]):
    for op, values in update.items():
        if op == "$set":
            for path, value in values.items():
                _set_by_path(doc, path, value)
        elif op == "$inc":
            for path, value in values.items():
                _inc_by_path(doc, path, value)
        elif op == "$push":
            for path, value in values.items():
                arr = _get_by_path(doc, path)
                if arr is None:
                    arr = []
                    _set_by_path(doc, path, arr)
                arr.append(value)
        else:
            raise AssertionError(f"Unsupported update operator: {op}")
