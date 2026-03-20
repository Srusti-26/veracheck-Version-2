"""
Configuration — environment-based settings for VeraCheck.
All thresholds, model names, and infra URLs are configurable here.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "VeraCheck"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL_SECONDS: int = 3600  # 1 hour

    # ── Embedding Model ───────────────────────────────────────────────────────
    # paraphrase-multilingual-MiniLM-L12-v2 supports 50+ languages incl. Hindi/Kannada/Tamil
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_DIM: int = 384

    # ── LLM (local, open-source) ──────────────────────────────────────────────
    # Use flan-t5-base for low-compute environments; swap for Mistral-7B on GPU
    LLM_MODEL: str = "google/flan-t5-base"
    LLM_MAX_NEW_TOKENS: int = 256
    LLM_TEMPERATURE: float = 0.1

    # ── Translation ───────────────────────────────────────────────────────────
    # Helsinki-NLP models: opus-mt-{src}-en (e.g. opus-mt-hi-en for Hindi)
    TRANSLATION_MODEL_PREFIX: str = "Helsinki-NLP/opus-mt"
    SUPPORTED_LANGUAGES: List[str] = ["hi", "kn", "ta", "te", "mr", "bn", "pa"]

    # ── FAISS ─────────────────────────────────────────────────────────────────
    FAISS_INDEX_PATH: str = "data/faiss_index.bin"
    FAISS_TOP_K: int = 5

    # ── Pipeline Optimization Thresholds ─────────────────────────────────────
    # Stage 1: If similarity >= HIGH_SIM_THRESHOLD → skip LLM (auto-classify)
    HIGH_SIM_THRESHOLD: float = 0.85
    # Stage 2: If similarity >= MID_SIM_THRESHOLD → use heuristic classifier
    MID_SIM_THRESHOLD: float = 0.60
    # Stage 3: Below MID_SIM_THRESHOLD → invoke LLM

    # ── Queue / Batch ─────────────────────────────────────────────────────────
    QUEUE_MAX_SIZE: int = 10_000
    BATCH_SIZE: int = 16
    BATCH_FLUSH_INTERVAL_MS: int = 100  # Flush queue every 100 ms

    # ── Feed Simulator ────────────────────────────────────────────────────────
    FEED_POSTS_PER_SECOND: float = 10.0
    FEED_MAX_HISTORY: int = 200

    # ── Metrics ───────────────────────────────────────────────────────────────
    METRICS_WINDOW_SECONDS: int = 60  # Rolling window for throughput calc

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
