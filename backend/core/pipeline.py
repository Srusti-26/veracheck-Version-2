"""
3-stage fact-check pipeline.

Stage 1 (cos_sim >= 0.88): auto-classify from vector similarity alone. ~0.5ms, no LLM.
Stage 2 (cos_sim >= 0.65): heuristic keyword + stance rules. ~2ms, no LLM.
Stage 3 (cos_sim <  0.65): local LLM inference. ~200-2000ms.

Typically 70-90% of requests are resolved by stages 1 and 2.
"""

import asyncio
import hashlib
import logging
import time
from typing import Optional

import numpy as np

from core.config import settings
from core.metrics_tracker import MetricsTracker
from models.schemas import (
    CheckResult,
    Verdict,
    PipelineStage,
    ClaimRequest,
    TranslationDetail,
)
from services.embedding_service import EmbeddingService
from services.fact_store import FactStore
from services.heuristic_classifier import HeuristicClassifier
from services.llm_service import LLMService
from services.redis_cache import RedisCache
from services.translation_service import TranslationService
from services.wikipedia_service import WikipediaService

logger = logging.getLogger("pipeline")


class FactCheckPipeline:
    """Orchestrates the 3-stage pipeline with caching, batching, and fallbacks."""

    def __init__(
        self,
        fact_store: FactStore,
        cache: RedisCache,
        metrics: MetricsTracker,
    ):
        self.fact_store = fact_store
        self.cache = cache
        self.metrics = metrics

        self._embedding_service: Optional[EmbeddingService] = None
        self._llm_service: Optional[LLMService] = None
        self._translation_service: Optional[TranslationService] = None
        self._heuristic: HeuristicClassifier = HeuristicClassifier()
        self._wikipedia: WikipediaService = WikipediaService()

        self._queue: asyncio.Queue = asyncio.Queue(maxsize=settings.QUEUE_MAX_SIZE)
        self._batch_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Load all models and start the background batch processor."""
        logger.info("Loading embedding model...")
        self._embedding_service = EmbeddingService()
        await self._embedding_service.initialize()

        logger.info("Loading translation service...")
        self._translation_service = TranslationService()
        await self._translation_service.initialize()

        logger.info("Loading LLM service...")
        self._llm_service = LLMService()
        await self._llm_service.initialize()

        await self._wikipedia.initialize()
        await self.fact_store.build_index(self._embedding_service)

        self._batch_task = asyncio.create_task(self._batch_processor_loop())
        logger.info("Pipeline ready.")

    async def check_claim(self, request: ClaimRequest) -> CheckResult:
        """Run a single claim through the pipeline. Results are cached by claim hash."""
        start_time = time.perf_counter()

        cache_key = self._cache_key(request.text)
        cached = await self.cache.get(cache_key)
        if cached:
            self.metrics.record_cache_hit()
            return CheckResult(**cached)

        detected_lang = await self._translation_service.detect_language(request.text)
        english_text = request.text
        was_translated = False
        if detected_lang != "en":
            english_text = await self._translation_service.translate_to_english(
                request.text, source_lang=detected_lang
            )
            was_translated = True

        # Build translation detail
        lang_names = {
            "hi": "Hindi", "kn": "Kannada", "ta": "Tamil", "te": "Telugu",
            "mr": "Marathi", "bn": "Bengali", "pa": "Punjabi", "en": "English",
            "ur": "Urdu", "gu": "Gujarati",
        }
        translation_detail = TranslationDetail(
            original_text=request.text,
            translated_text=english_text,
            source_language=detected_lang,
            source_language_name=lang_names.get(detected_lang, detected_lang.upper()),
            was_translated=was_translated,
        )

        claim_embedding = await self._embedding_service.embed(english_text)
        top_facts = await self.fact_store.search(
            query_embedding=claim_embedding,
            top_k=settings.FAISS_TOP_K,
        )

        best_similarity = top_facts[0]["similarity"] if top_facts else 0.0

        if best_similarity >= settings.HIGH_SIM_THRESHOLD:
            stage = PipelineStage.STAGE1_AUTO
            verdict, confidence, explanation = self._stage1_classify(top_facts, best_similarity)
            verdict_category = "NEAR_DUPLICATE"
            self.metrics.record_stage(1)

        elif best_similarity >= settings.MID_SIM_THRESHOLD:
            stage = PipelineStage.STAGE2_HEURISTIC
            verdict, confidence, explanation, verdict_category = await self._stage2_classify(
                english_text, top_facts, best_similarity
            )
            self.metrics.record_stage(2)

        else:
            stage = PipelineStage.STAGE3_LLM
            verdict, confidence, explanation = await self._stage3_classify(
                english_text, top_facts
            )
            verdict_category = "LLM_INFERRED"
            self.metrics.record_stage(3)

        # Confidence tier
        if confidence >= 0.85:
            confidence_tier = "HIGH"
        elif confidence >= 0.65:
            confidence_tier = "MEDIUM"
        else:
            confidence_tier = "LOW"

        # Wikipedia evidence (non-blocking, best-effort)
        wiki_summary = await self._wikipedia.get_evidence(english_text)

        latency_ms = (time.perf_counter() - start_time) * 1000

        result = CheckResult(
            claim=request.text,
            english_claim=english_text,
            detected_language=detected_lang,
            verdict=verdict,
            confidence=round(confidence, 4),
            confidence_tier=confidence_tier,
            verdict_category=verdict_category,
            explanation=explanation,
            retrieved_facts=top_facts[:3],
            best_similarity=round(best_similarity, 4),
            pipeline_stage=stage,
            latency_ms=round(latency_ms, 2),
            timestamp=time.time(),
            translation=translation_detail,
            wikipedia_summary=wiki_summary,
        )

        await self.cache.set(cache_key, result.model_dump(), ttl=settings.CACHE_TTL_SECONDS)
        self.metrics.record_request(latency_ms=latency_ms, stage=stage)

        return result

    async def enqueue(self, request: ClaimRequest) -> str:
        """Non-blocking enqueue for batch mode. Returns a job ID for polling."""
        job_id = hashlib.md5(f"{request.text}{time.time()}".encode()).hexdigest()[:12]
        await self._queue.put((job_id, request))
        return job_id

    def _stage1_classify(self, top_facts, similarity: float):
        """Auto-classify using weighted voting across top-3 facts."""
        label_map = {"TRUE": Verdict.TRUE, "FALSE": Verdict.FALSE, "MISLEADING": Verdict.MISLEADING}
        vote_scores: dict = {}
        for fact in top_facts[:3]:
            label = fact.get("verdict", "UNVERIFIED").upper()
            weight = float(fact.get("similarity", 0.0))
            vote_scores[label] = vote_scores.get(label, 0.0) + weight
        best_label = max(vote_scores, key=vote_scores.get)
        verdict = label_map.get(best_label, Verdict.UNVERIFIED)
        confidence = float(np.clip(similarity, 0, 1))
        best_fact = top_facts[0]
        explanation = (
            f"[Stage 1 — Auto] Weighted vote across top-3 facts → {best_label} "
            f"(similarity: {similarity:.2%}). Top match: \"{best_fact['text'][:120]}\""
        )
        return verdict, confidence, explanation

    async def _stage2_classify(self, claim: str, top_facts, similarity: float):
        """Heuristic classifier using negation detection and keyword rules."""
        verdict, confidence, reason, verdict_category = await self._heuristic.classify(
            claim=claim,
            top_facts=top_facts,
            similarity=similarity,
        )
        explanation = (
            f"[Stage 2 — Heuristic] {reason} "
            f"(similarity: {similarity:.2%}, confidence: {confidence:.2%})"
        )
        return verdict, confidence, explanation, verdict_category

    async def _stage3_classify(self, claim: str, top_facts):
        """Full LLM verification. Only invoked when stages 1 and 2 cannot classify."""
        context_facts = "\n".join(
            [f"{i+1}. \"{f['text']}\" [Verdict: {f.get('verdict', 'unknown').upper()}, Source: {f.get('source', 'unknown')}]"
             for i, f in enumerate(top_facts[:3])]
        )
        prompt = (
            f"You are a strict fact-checker. Evaluate the claim against the known facts below.\n\n"
            f"CLAIM: {claim}\n\n"
            f"KNOWN FACTS:\n{context_facts}\n\n"
            f"Instructions:\n"
            f"- If the claim matches or supports a TRUE fact: VERDICT = TRUE\n"
            f"- If the claim contradicts or negates a TRUE fact, or matches a FALSE fact: VERDICT = FALSE\n"
            f"- If the claim is partially true or taken out of context: VERDICT = MISLEADING\n"
            f"- If no fact is relevant: VERDICT = UNVERIFIED\n\n"
            f"Respond ONLY in this exact format:\n"
            f"VERDICT: TRUE | FALSE | MISLEADING | UNVERIFIED\n"
            f"CONFIDENCE: 0.0 to 1.0\n"
            f"REASON: one concise sentence\n"
        )
        llm_output = await self._llm_service.generate(prompt)
        verdict, confidence, reason = self._parse_llm_output(llm_output)
        return verdict, confidence, f"[Stage 3 — LLM] {reason}"

    def _parse_llm_output(self, text: str):
        """Parse structured LLM output into (verdict, confidence, reason)."""
        import re
        lines = text.strip().split("\n")
        verdict = Verdict.UNVERIFIED
        confidence = 0.5
        reason = text[:200]

        for line in lines:
            upper = line.upper().strip()
            if upper.startswith("VERDICT:"):
                v = re.sub(r'[^A-Z]', '', line.split(":", 1)[-1].strip().upper())
                verdict = {
                    "TRUE": Verdict.TRUE,
                    "FALSE": Verdict.FALSE,
                    "MISLEADING": Verdict.MISLEADING,
                }.get(v, Verdict.UNVERIFIED)
            elif upper.startswith("CONFIDENCE:"):
                try:
                    nums = re.findall(r'[0-9]*\.?[0-9]+', line)
                    if nums:
                        val = float(nums[0])
                        confidence = val if val <= 1.0 else val / 100.0
                except ValueError:
                    pass
            elif upper.startswith("REASON:"):
                reason = line.split(":", 1)[-1].strip()

        # flan-t5 sometimes returns just the verdict word directly
        if verdict == Verdict.UNVERIFIED:
            flat = text.strip().upper()
            for v_str, v_enum in [("FALSE", Verdict.FALSE), ("TRUE", Verdict.TRUE), ("MISLEADING", Verdict.MISLEADING)]:
                if v_str in flat:
                    verdict = v_enum
                    confidence = 0.65
                    break

        return verdict, confidence, reason

    async def _batch_processor_loop(self):
        """Drains the async queue in micro-batches at BATCH_FLUSH_INTERVAL_MS cadence."""
        interval = settings.BATCH_FLUSH_INTERVAL_MS / 1000
        while True:
            try:
                await asyncio.sleep(interval)
                batch = []
                for _ in range(settings.BATCH_SIZE):
                    try:
                        batch.append(self._queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break

                if batch:
                    tasks = [self.check_claim(req) for _, req in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for (job_id, _), result in zip(batch, results):
                        if isinstance(result, Exception):
                            logger.error(f"Batch job {job_id} failed: {result}")
                        else:
                            await self.cache.set(
                                f"job:{job_id}", result.model_dump(), ttl=300
                            )

            except asyncio.CancelledError:
                logger.info("Batch processor stopped.")
                break
            except Exception as e:
                logger.error(f"Batch processor error: {e}", exc_info=True)

    @property
    def embedding_service(self):
        return self._embedding_service

    @staticmethod
    def _cache_key(text: str) -> str:
        return f"claim:{hashlib.sha256(text.encode()).hexdigest()[:16]}"
