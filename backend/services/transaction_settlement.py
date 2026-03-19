"""
Transaction settlement service.

Centralizes debit/credit logic and enforces idempotency so a transaction
cannot be settled more than once.
"""

from datetime import datetime
from typing import Any, Dict, Union
import importlib

from backend.models.transaction import TransactionStatus
from backend.observability.metrics import metrics_registry
from backend.utils.logger import logger


def _to_object_id(value: Union[str, Any]) -> Union[str, Any]:
    """Convert string value to ObjectId when possible."""
    try:
        bson_module = importlib.import_module("bson")
        object_id_cls = getattr(bson_module, "ObjectId")
    except Exception:
        return value

    if isinstance(value, object_id_cls):
        return value

    if isinstance(value, str) and object_id_cls.is_valid(value):
        return object_id_cls(value)

    return value


async def settle_transaction_by_id(
    db,
    transaction_id: Union[str, Any],
    source: str,
) -> Dict[str, Any]:
    """
    Settle an approved transaction by id (idempotent).

    Returns a status dict with settled=True when funds were moved in this call.
    """
    settlement_start = metrics_registry.start_timer()
    tx_obj_id = _to_object_id(transaction_id)

    claimed_tx = await db.transactions.find_one_and_update(
        {
            "_id": tx_obj_id,
            "status": TransactionStatus.APPROVED,
            "$or": [
                {"settlement.applied": {"$exists": False}},
                {"settlement.applied": False},
            ],
            "settlement.state": {"$ne": "processing"},
        },
        {
            "$set": {
                "settlement.state": "processing",
                "settlement.claimed_at": datetime.utcnow(),
                "settlement.claimed_by": source,
            }
        },
    )

    if not claimed_tx:
        current = await db.transactions.find_one({"_id": tx_obj_id})
        if not current:
            metrics_registry.record_settlement(False, "not_found", metrics_registry.elapsed_ms(settlement_start))
            return {"settled": False, "reason": "not_found"}

        settlement = current.get("settlement", {})
        if settlement.get("applied"):
            metrics_registry.record_settlement(False, "already_settled", metrics_registry.elapsed_ms(settlement_start))
            return {"settled": False, "reason": "already_settled"}

        if current.get("status") != TransactionStatus.APPROVED:
            metrics_registry.record_settlement(False, "not_approved", metrics_registry.elapsed_ms(settlement_start))
            return {"settled": False, "reason": "not_approved"}

        if settlement.get("state") == "processing":
            metrics_registry.record_settlement(False, "processing", metrics_registry.elapsed_ms(settlement_start))
            return {"settled": False, "reason": "processing"}

        metrics_registry.record_settlement(False, "not_claimed", metrics_registry.elapsed_ms(settlement_start))
        return {"settled": False, "reason": "not_claimed"}

    try:
        user_id = _to_object_id(claimed_tx["user_id"])
        user = await db.users.find_one({"_id": user_id})
        if not user:
            raise ValueError(f"Sender user not found: {claimed_tx['user_id']}")

        card_idx = claimed_tx.get("card_index")
        cards = user.get("cards", [])
        if card_idx is None or card_idx < 0 or card_idx >= len(cards):
            raise ValueError(f"Invalid card_index for settlement: {card_idx}")

        amount = float(claimed_tx["amount"])
        today = datetime.utcnow().date().isoformat()
        current_balance = float(cards[card_idx].get("balance", 0.0))

        sender_update = await db.users.update_one(
            {"_id": user_id},
            {
                "$inc": {
                    f"cards.{card_idx}.balance": -amount,
                    f"cards.{card_idx}.daily_spent": amount,
                },
                "$set": {
                    f"cards.{card_idx}.last_reset": today,
                    "last_transaction_time": datetime.utcnow(),
                    "last_transaction_location": claimed_tx.get("user_location"),
                },
            },
        )

        if sender_update.matched_count == 0:
            raise ValueError("Sender update did not match any document")

        recipient_email = claimed_tx.get("recipient_email")
        if recipient_email:
            recipient = await db.users.find_one({"email": recipient_email})
            if recipient and recipient.get("cards"):
                await db.users.update_one(
                    {"_id": recipient["_id"]},
                    {"$inc": {"cards.0.balance": amount}},
                )
                logger.info(
                    f"Transfer settled | TX: {claimed_tx['_id']} | To: {recipient_email} | €{amount:.2f}"
                )

        await db.transactions.update_one(
            {"_id": tx_obj_id},
            {
                "$set": {
                    "settlement.applied": True,
                    "settlement.state": "completed",
                    "settlement.settled_at": datetime.utcnow(),
                    "settlement.source": source,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        logger.success(
            f"Settlement completed | TX: {claimed_tx['_id']} | Card Index: {card_idx} | "
            f"Amount: €{amount:.2f} | New Balance: €{(current_balance - amount):.2f}"
        )

        metrics_registry.record_settlement(True, "settled", metrics_registry.elapsed_ms(settlement_start))

        return {
            "settled": True,
            "reason": "settled",
            "amount": amount,
            "card_index": card_idx,
        }

    except Exception as exc:
        await db.transactions.update_one(
            {"_id": tx_obj_id},
            {
                "$set": {
                    "settlement.state": "failed",
                    "settlement.last_error": str(exc),
                    "settlement.failed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        logger.error(f"Settlement failed | TX: {tx_obj_id} | Error: {exc}")
        metrics_registry.record_settlement(False, "failed", metrics_registry.elapsed_ms(settlement_start))
        metrics_registry.record_db_error("settlement", str(exc))
        raise
