import logging
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.routes import claims, facts, feed, metrics, admin
from core.config import settings
from core.pipeline import FactCheckPipeline
from services.redis_cache import RedisCache
from services.fact_store import FactStore
from services.feed_simulator import FeedSimulator
from core.metrics_tracker import MetricsTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("veracheck")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VeraCheck starting up...")

    app.state.cache = RedisCache(settings.REDIS_URL)
    await app.state.cache.connect()

    app.state.fact_store = FactStore()
    await app.state.fact_store.initialize()

    app.state.metrics = MetricsTracker()

    app.state.pipeline = FactCheckPipeline(
        fact_store=app.state.fact_store,
        cache=app.state.cache,
        metrics=app.state.metrics,
    )
    await app.state.pipeline.initialize()

    app.state.feed_simulator = FeedSimulator(pipeline=app.state.pipeline)
    await app.state.feed_simulator.start()  # auto-start feed on launch

    logger.info("All services ready.")
    yield

    logger.info("Shutting down...")
    await app.state.feed_simulator.stop()
    await app.state.pipeline._wikipedia.close()
    await app.state.cache.disconnect()


app = FastAPI(
    title="VeraCheck API",
    description="Real-Time Vernacular News Fact-Checker",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(claims.router, prefix="/api/v1/claims", tags=["Claims"])
app.include_router(facts.router, prefix="/api/v1/facts", tags=["Facts"])
app.include_router(feed.router, prefix="/api/v1/feed", tags=["Feed"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time(), "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=12345,
        reload=settings.DEBUG,
        workers=1,
    )
