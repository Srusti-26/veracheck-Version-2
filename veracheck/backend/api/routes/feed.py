"""Feed API routes including SSE (Server-Sent Events) for live stream."""

import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.get("/history")
async def get_feed_history(request: Request, limit: int = 50):
    """Get recent feed history."""
    feed = request.app.state.feed_simulator
    history = feed.history[-limit:]
    return {"posts": [p.model_dump() for p in history], "total": len(history)}


@router.post("/start")
async def start_feed(request: Request):
    """Start the feed simulator."""
    feed = request.app.state.feed_simulator
    await feed.start()
    return {"status": "started"}


@router.post("/stop")
async def stop_feed(request: Request):
    """Stop the feed simulator."""
    feed = request.app.state.feed_simulator
    await feed.stop()
    return {"status": "stopped"}


@router.get("/stream")
async def stream_feed(request: Request):
    """
    Server-Sent Events endpoint for live feed.
    Frontend subscribes to this to get real-time updates.
    """
    feed = request.app.state.feed_simulator
    queue = feed.subscribe()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    post = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(post)}\n\n"
                except asyncio.TimeoutError:
                    yield "data: {\"heartbeat\": true}\n\n"
        finally:
            feed.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
