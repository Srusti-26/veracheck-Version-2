"""
Fact Store — FAISS vector index + in-memory fact database.

Stores verified facts as embeddings in a FAISS flat index.
Provides O(1) approximate nearest-neighbour search.

In production, persist FAISS index to disk and sync with PostgreSQL.
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from core.config import settings
from models.schemas import Verdict

logger = logging.getLogger("fact_store")


class FactStore:
    """
    In-memory fact database with FAISS vector search.
    
    Facts are loaded from the seed dataset on startup and can be
    added via the Admin API at runtime.
    """

    def __init__(self):
        self._facts: Dict[str, dict] = {}          # id → fact record
        self._fact_list: List[dict] = []           # ordered list for FAISS lookup
        self._index = None                          # FAISS index
        self._embedding_service = None

    async def initialize(self):
        """Load seed facts from JSON dataset."""
        seed_path = Path("data/seed_facts.json")
        if seed_path.exists():
            with open(seed_path) as f:
                facts = json.load(f)
            for fact in facts:
                fact_id = fact.get("id", str(uuid.uuid4())[:8])
                self._facts[fact_id] = {**fact, "id": fact_id}
                self._fact_list.append({**fact, "id": fact_id})
            logger.info(f"Loaded {len(self._facts)} seed facts.")
        else:
            logger.warning("No seed facts found. Using empty fact store.")
            self._seed_demo_facts()

    def _seed_demo_facts(self):
        """Add demo facts if no dataset file found."""
        demo_facts = [
            {"id": "f001", "text": "India has 28 states and 8 union territories as of 2019.", "verdict": "TRUE", "source": "GoI", "category": "politics"},
            {"id": "f002", "text": "COVID-19 vaccines are safe and effective according to WHO.", "verdict": "TRUE", "source": "WHO", "category": "health"},
            {"id": "f003", "text": "5G technology causes coronavirus infection.", "verdict": "FALSE", "source": "WHO", "category": "health"},
            {"id": "f004", "text": "Drinking bleach cures COVID-19.", "verdict": "FALSE", "source": "CDC", "category": "health"},
            {"id": "f005", "text": "Climate change is primarily caused by human activities.", "verdict": "TRUE", "source": "IPCC", "category": "science"},
            {"id": "f006", "text": "The Moon landing in 1969 was a hoax.", "verdict": "FALSE", "source": "NASA", "category": "science"},
            {"id": "f007", "text": "India became independent on 15 August 1947.", "verdict": "TRUE", "source": "History", "category": "history"},
            {"id": "f008", "text": "Onion exports were banned by India in 2023 to control domestic prices.", "verdict": "TRUE", "source": "APEDA", "category": "economy"},
            {"id": "f009", "text": "Eating garlic prevents COVID-19 infection.", "verdict": "MISLEADING", "source": "WHO", "category": "health"},
            {"id": "f010", "text": "WhatsApp messages are fully encrypted end-to-end.", "verdict": "TRUE", "source": "WhatsApp", "category": "technology"},
        ]
        for fact in demo_facts:
            self._facts[fact["id"]] = fact
            self._fact_list.append(fact)

    async def build_index(self, embedding_service):
        """
        Embed all facts and build FAISS index.
        Called once on startup after embedding model is ready.
        """
        self._embedding_service = embedding_service

        if not self._fact_list:
            logger.warning("No facts to index.")
            return

        logger.info(f"Building FAISS index for {len(self._fact_list)} facts...")
        texts = [f["text"] for f in self._fact_list]
        embeddings = await embedding_service.embed_batch(texts)

        try:
            import faiss
            dim = embeddings.shape[1]
            self._index = faiss.IndexFlatIP(dim)  # Inner product (cosine on normalized vecs)
            self._index.add(embeddings)
            logger.info(f"FAISS index built: {self._index.ntotal} vectors, dim={dim}")
        except ImportError:
            logger.warning("FAISS not installed. Using numpy brute-force search (slower).")
            self._embeddings_matrix = embeddings  # fallback

    async def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[dict]:
        """
        Retrieve top-K facts most similar to the query embedding.
        Returns list of fact dicts with 'similarity' field added.
        """
        if not self._fact_list:
            return []

        query = query_embedding.reshape(1, -1).astype(np.float32)

        try:
            import faiss
            if self._index is not None:
                scores, indices = self._index.search(query, min(top_k, len(self._fact_list)))
                results = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx < 0:
                        continue
                    fact = dict(self._fact_list[idx])
                    fact["similarity"] = float(score)
                    results.append(fact)
                return results
        except ImportError:
            pass

        # Fallback: numpy brute-force
        if hasattr(self, '_embeddings_matrix'):
            sims = self._embeddings_matrix @ query.T
            sims = sims.flatten()
            top_indices = np.argsort(sims)[::-1][:top_k]
            results = []
            for idx in top_indices:
                fact = dict(self._fact_list[idx])
                fact["similarity"] = float(sims[idx])
                results.append(fact)
            return results

        return []

    def add_fact(self, fact: dict) -> str:
        """Add a new fact (runtime; requires index rebuild)."""
        fact_id = str(uuid.uuid4())[:8]
        fact["id"] = fact_id
        fact["created_at"] = time.time()
        self._facts[fact_id] = fact
        self._fact_list.append(fact)
        return fact_id

    def get_all_facts(self) -> List[dict]:
        return list(self._facts.values())

    def get_fact(self, fact_id: str) -> Optional[dict]:
        return self._facts.get(fact_id)

    def delete_fact(self, fact_id: str) -> bool:
        if fact_id in self._facts:
            del self._facts[fact_id]
            self._fact_list = [f for f in self._fact_list if f["id"] != fact_id]
            return True
        return False

    @property
    def count(self) -> int:
        return len(self._facts)
