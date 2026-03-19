"""Observability routes for metrics and alerts."""

from fastapi import APIRouter

from backend.observability.metrics import metrics_registry

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    """Return in-memory operational metrics snapshot."""
    return metrics_registry.snapshot()


@router.get("/alerts")
async def get_alerts():
    """Return active operational alerts based on current metrics."""
    return metrics_registry.alerts()
