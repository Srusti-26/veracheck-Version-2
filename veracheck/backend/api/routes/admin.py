"""Admin API routes."""
import csv
import io
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
router = APIRouter()

@router.get("/export/csv")
async def export_results_csv(request: Request):
    """Export recent feed results as CSV."""
    feed = request.app.state.feed_simulator
    history = feed.history

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "id", "timestamp", "source", "language", "text",
        "verdict", "confidence", "pipeline_stage", "latency_ms"
    ])
    writer.writeheader()
    for post in history:
        row = {
            "id": post.id,
            "timestamp": post.timestamp,
            "source": post.source,
            "language": post.language,
            "text": post.text[:200],
            "verdict": post.result.verdict if post.result else "N/A",
            "confidence": post.result.confidence if post.result else "",
            "pipeline_stage": post.result.pipeline_stage if post.result else "",
            "latency_ms": post.result.latency_ms if post.result else "",
        }
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=veracheck_export.csv"}
    )

@router.get("/config")
async def get_config():
    """Return current pipeline configuration."""
    from core.config import settings
    return {
        "high_sim_threshold": settings.HIGH_SIM_THRESHOLD,
        "mid_sim_threshold": settings.MID_SIM_THRESHOLD,
        "embedding_model": settings.EMBEDDING_MODEL,
        "llm_model": settings.LLM_MODEL,
        "faiss_top_k": settings.FAISS_TOP_K,
        "batch_size": settings.BATCH_SIZE,
        "cache_ttl_seconds": settings.CACHE_TTL_SECONDS,
    }
