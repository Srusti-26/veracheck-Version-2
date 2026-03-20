"""Metrics API routes."""
from fastapi import APIRouter, Request
router = APIRouter()

@router.get("/snapshot")
async def metrics_snapshot(request: Request):
    """Get current metrics snapshot."""
    metrics = request.app.state.metrics
    cache = request.app.state.cache
    snap = metrics.snapshot()
    snap["cache"] = cache.stats
    return snap

@router.get("/history")
async def metrics_history(request: Request):
    """Get last N metric snapshots (stored in cache)."""
    cache = request.app.state.cache
    history = await cache.get("metrics:history") or []
    return {"history": history}
