"""
VeraCheck — Data Schemas (Pydantic v2)
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import time


class Verdict(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    MISLEADING = "MISLEADING"
    UNVERIFIED = "UNVERIFIED"


class PipelineStage(str, Enum):
    STAGE1_AUTO = "STAGE1_AUTO"
    STAGE2_HEURISTIC = "STAGE2_HEURISTIC"
    STAGE3_LLM = "STAGE3_LLM"
    CACHED = "CACHED"


# ── Request Models ─────────────────────────────────────────────────────────────

class ClaimRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=2000, description="The claim to fact-check")
    source: Optional[str] = Field(None, description="Source of the claim (e.g., Twitter, WhatsApp)")
    metadata: Optional[Dict[str, Any]] = None


class BatchClaimRequest(BaseModel):
    claims: List[ClaimRequest] = Field(..., max_length=100)


class FactCreateRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)
    verdict: Verdict
    source: str
    category: Optional[str] = None
    tags: Optional[List[str]] = []


# ── Response Models ────────────────────────────────────────────────────────────

class RetrievedFact(BaseModel):
    id: str
    text: str
    verdict: str
    source: str
    similarity: float
    category: Optional[str] = None


class TranslationDetail(BaseModel):
    original_text: str
    translated_text: str
    source_language: str
    source_language_name: str
    was_translated: bool


class CheckResult(BaseModel):
    claim: str
    english_claim: str
    detected_language: str
    verdict: Verdict
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_tier: str = "MEDIUM"  # HIGH / MEDIUM / LOW
    verdict_category: str = ""       # NEAR_DUPLICATE / NEGATION / KEYWORD / LLM_INFERRED / CACHED
    explanation: str
    retrieved_facts: List[Dict[str, Any]] = []
    best_similarity: float = Field(..., ge=0.0, le=1.0)
    pipeline_stage: PipelineStage
    latency_ms: float
    timestamp: float = Field(default_factory=time.time)
    translation: Optional[TranslationDetail] = None
    wikipedia_summary: Optional[str] = None


class BatchCheckResponse(BaseModel):
    job_id: str
    queued_count: int
    estimated_completion_ms: float


class FactRecord(BaseModel):
    id: str
    text: str
    verdict: Verdict
    source: str
    category: Optional[str] = None
    tags: List[str] = []
    created_at: float = Field(default_factory=time.time)


class MetricSnapshot(BaseModel):
    timestamp: float
    throughput_rps: float           # requests per second
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    stage1_pct: float               # % handled by Stage 1
    stage2_pct: float               # % handled by Stage 2
    stage3_pct: float               # % handled by Stage 3 (LLM)
    llm_skip_rate: float            # = stage1_pct + stage2_pct
    cache_hit_rate: float
    total_processed: int
    estimated_cost_saved_usd: float  # vs naive GPT-4 baseline


class FeedPost(BaseModel):
    id: str
    text: str
    source: str
    language: str
    timestamp: float
    result: Optional[CheckResult] = None
