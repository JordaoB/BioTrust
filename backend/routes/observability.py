"""Observability routes for metrics and alerts."""

from fastapi import APIRouter
from fastapi import Depends

from backend.observability.metrics import metrics_registry
from backend.database import get_database
from backend.utils.logger import logger

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    """Return in-memory operational metrics snapshot."""
    return metrics_registry.snapshot()


@router.get("/alerts")
async def get_alerts():
    """Return active operational alerts based on current metrics."""
    return metrics_registry.alerts()


@router.get("/fraud-feed")
async def get_fraud_feed(limit: int = 30, db=Depends(get_database)):
    """Return recent transactions enriched for real-time fraud operations."""
    try:
        safe_limit = max(5, min(limit, 100))
        cursor = db.transactions.find({}).sort("created_at", -1).limit(safe_limit)
        transactions = await cursor.to_list(length=safe_limit)

        feed = []
        for tx in transactions:
            feed.append(
                {
                    "transaction_id": str(tx.get("_id")),
                    "user_id": tx.get("user_id"),
                    "recipient_email": tx.get("recipient_email"),
                    "amount": tx.get("amount", 0),
                    "status": tx.get("status", "unknown"),
                    "risk_score": tx.get("risk_score", 0),
                    "risk_level": str(tx.get("risk_level", "unknown")),
                    "risk_reason": tx.get("risk_reason"),
                    "risk_factors": tx.get("risk_factors", {}),
                    "anomaly_detected": tx.get("anomaly_detected", False),
                    "anomaly_score": tx.get("anomaly_score", 0),
                    "anomaly_reason": tx.get("anomaly_reason"),
                    "liveness_required": tx.get("liveness_required", False),
                    "liveness_performed": tx.get("liveness_performed", False),
                    "liveness_success": bool((tx.get("liveness_result") or {}).get("success", False)),
                    "settlement_state": (tx.get("settlement") or {}).get("state", "pending"),
                    "created_at": tx.get("created_at"),
                    "updated_at": tx.get("updated_at"),
                }
            )

        return {
            "generated_at": metrics_registry.snapshot()["timestamp"],
            "count": len(feed),
            "feed": feed,
        }
    except Exception as exc:
        metrics_registry.record_db_error("observability.fraud_feed", str(exc))
        logger.error(f"Failed to build fraud feed: {exc}")
        return {
            "generated_at": metrics_registry.snapshot()["timestamp"],
            "count": 0,
            "feed": [],
            "error": str(exc),
        }
