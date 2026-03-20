"""Claims API routes."""

import time
from fastapi import APIRouter, Request, HTTPException
from models.schemas import ClaimRequest, BatchClaimRequest, CheckResult

router = APIRouter()


@router.post("/check", response_model=CheckResult)
async def check_claim(request: Request, body: ClaimRequest):
    """Fact-check a single claim through the 3-stage pipeline."""
    pipeline = request.app.state.pipeline
    try:
        result = await pipeline.check_claim(body)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_check(request: Request, body: BatchClaimRequest):
    """Enqueue a batch of claims for async processing."""
    pipeline = request.app.state.pipeline
    job_ids = []
    for claim in body.claims:
        job_id = await pipeline.enqueue(claim)
        job_ids.append(job_id)

    return {
        "job_ids": job_ids,
        "queued_count": len(job_ids),
        "estimated_completion_ms": len(job_ids) * 50,
    }


@router.get("/job/{job_id}")
async def get_job_result(request: Request, job_id: str):
    """Poll for batch job result."""
    cache = request.app.state.cache
    result = await cache.get(f"job:{job_id}")
    if result is None:
        return {"status": "pending", "job_id": job_id}
    return {"status": "complete", "job_id": job_id, "result": result}
