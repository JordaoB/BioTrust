from __future__ import annotations

from collections import deque
from datetime import datetime
from threading import Lock
from time import perf_counter
from typing import Any, Dict, Optional


class MetricsRegistry:
    """In-memory metrics registry for production observability."""

    def __init__(self) -> None:
        self._lock = Lock()

        self.counters = {
            "transactions_total": 0,
            "transactions_approved": 0,
            "transactions_pending": 0,
            "transactions_rejected": 0,
            "liveness_total": 0,
            "liveness_passed": 0,
            "liveness_failed": 0,
            "settlement_total": 0,
            "settlement_success": 0,
            "settlement_failed": 0,
            "db_errors": 0,
        }

        self.durations = {
            "transaction_ms_total": 0.0,
            "liveness_ms_total": 0.0,
            "settlement_ms_total": 0.0,
        }

        self.windows = {
            "tx_outcomes": deque(maxlen=500),
            "liveness_outcomes": deque(maxlen=500),
            "settlement_outcomes": deque(maxlen=500),
            "db_errors": deque(maxlen=500),
        }

    @staticmethod
    def start_timer() -> float:
        return perf_counter()

    @staticmethod
    def elapsed_ms(start: float) -> float:
        return max(0.0, (perf_counter() - start) * 1000.0)

    def record_transaction(self, status: str, duration_ms: float) -> None:
        now = datetime.utcnow().isoformat()
        with self._lock:
            self.counters["transactions_total"] += 1
            self.durations["transaction_ms_total"] += duration_ms

            status_lower = str(status).lower()
            if status_lower == "approved":
                self.counters["transactions_approved"] += 1
            elif status_lower == "pending":
                self.counters["transactions_pending"] += 1
            elif status_lower == "rejected":
                self.counters["transactions_rejected"] += 1

            self.windows["tx_outcomes"].append({"timestamp": now, "status": status_lower})

    def record_liveness(self, success: bool, duration_ms: float) -> None:
        now = datetime.utcnow().isoformat()
        with self._lock:
            self.counters["liveness_total"] += 1
            self.durations["liveness_ms_total"] += duration_ms
            if success:
                self.counters["liveness_passed"] += 1
            else:
                self.counters["liveness_failed"] += 1
            self.windows["liveness_outcomes"].append({"timestamp": now, "success": bool(success)})

    def record_settlement(self, success: bool, reason: str, duration_ms: float) -> None:
        now = datetime.utcnow().isoformat()
        with self._lock:
            self.counters["settlement_total"] += 1
            self.durations["settlement_ms_total"] += duration_ms
            if success:
                self.counters["settlement_success"] += 1
            else:
                self.counters["settlement_failed"] += 1
            self.windows["settlement_outcomes"].append(
                {"timestamp": now, "success": bool(success), "reason": reason}
            )

    def record_db_error(self, context: str, detail: Optional[str] = None) -> None:
        now = datetime.utcnow().isoformat()
        with self._lock:
            self.counters["db_errors"] += 1
            self.windows["db_errors"].append(
                {"timestamp": now, "context": context, "detail": detail or "N/A"}
            )

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            counters = dict(self.counters)
            durations = dict(self.durations)
            windows = {k: list(v) for k, v in self.windows.items()}

        tx_total = counters["transactions_total"] or 1
        liveness_total = counters["liveness_total"] or 1
        settlement_total = counters["settlement_total"] or 1

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "counters": counters,
            "rates": {
                "transaction_approval_rate": round(counters["transactions_approved"] / tx_total, 4),
                "transaction_rejection_rate": round(counters["transactions_rejected"] / tx_total, 4),
                "liveness_failure_rate": round(counters["liveness_failed"] / liveness_total, 4),
                "settlement_failure_rate": round(counters["settlement_failed"] / settlement_total, 4),
            },
            "averages_ms": {
                "transaction": round(durations["transaction_ms_total"] / tx_total, 2),
                "liveness": round(durations["liveness_ms_total"] / liveness_total, 2),
                "settlement": round(durations["settlement_ms_total"] / settlement_total, 2),
            },
            "recent": {
                "tx_outcomes": windows["tx_outcomes"][-20:],
                "liveness_outcomes": windows["liveness_outcomes"][-20:],
                "settlement_outcomes": windows["settlement_outcomes"][-20:],
                "db_errors": windows["db_errors"][-20:],
            },
        }

    def alerts(self) -> Dict[str, Any]:
        snap = self.snapshot()
        rates = snap["rates"]
        counters = snap["counters"]
        alerts = []

        if counters["transactions_total"] >= 10 and rates["transaction_rejection_rate"] >= 0.30:
            alerts.append(
                {
                    "severity": "warning",
                    "type": "rejection_spike",
                    "message": f"Rejection rate high: {rates['transaction_rejection_rate'] * 100:.1f}%",
                }
            )

        if counters["liveness_total"] >= 10 and rates["liveness_failure_rate"] >= 0.35:
            alerts.append(
                {
                    "severity": "warning",
                    "type": "liveness_failure_spike",
                    "message": f"Liveness failure rate high: {rates['liveness_failure_rate'] * 100:.1f}%",
                }
            )

        if counters["settlement_total"] >= 5 and rates["settlement_failure_rate"] >= 0.05:
            alerts.append(
                {
                    "severity": "critical",
                    "type": "settlement_failures",
                    "message": f"Settlement failure rate high: {rates['settlement_failure_rate'] * 100:.1f}%",
                }
            )

        if counters["db_errors"] >= 3:
            alerts.append(
                {
                    "severity": "critical",
                    "type": "db_errors",
                    "message": f"Database errors detected: {counters['db_errors']}",
                }
            )

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_alerts": alerts,
            "has_alerts": len(alerts) > 0,
        }


metrics_registry = MetricsRegistry()
