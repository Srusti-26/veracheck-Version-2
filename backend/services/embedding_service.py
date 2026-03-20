"""
Multilingual sentence embeddings via SentenceTransformers.
Model: paraphrase-multilingual-MiniLM-L12-v2 (50+ languages, 384-dim, ~120MB)
"""

import asyncio
import logging
import numpy as np
from typing import List

from core.config import settings

logger = logging.getLogger("embedding")


class EmbeddingService:
    """Async-compatible wrapper around SentenceTransformers."""

    def __init__(self):
        self._model = None
        self._loop = None

    async def initialize(self):
        self._loop = asyncio.get_event_loop()
        await self._loop.run_in_executor(None, self._load_model)
        logger.info(f"Embedding model loaded: {settings.EMBEDDING_MODEL}")

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        except ImportError:
            logger.warning("sentence-transformers not installed. Using random embeddings (demo mode).")
            self._model = None

    async def embed(self, text: str) -> np.ndarray:
        return (await self.embed_batch([text]))[0]

    async def embed_batch(self, texts: List[str]) -> np.ndarray:
        if self._model is None:
            return np.random.randn(len(texts), settings.EMBEDDING_DIM).astype(np.float32)

        result = await self._loop.run_in_executor(
            None,
            lambda: self._model.encode(
                texts,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
        )
        return result.astype(np.float32)

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two L2-normalized vectors."""
        return float(np.dot(a, b))
