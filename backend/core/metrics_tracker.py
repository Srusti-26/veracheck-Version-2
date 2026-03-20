"""
Rolling-window metrics tracker for the VeraCheck dashboard.

Tracks throughput, latency percentiles, pipeline stage distribution,
cache hit rate, and estimated cost savings vs a GPT-4 baseline.
"""

import time
import logging
import statistics
from collections import deque

from core.config import settings
from models.schemas import PipelineStage

logger = logging.getLogger("metrics")

# Cost model: GPT-4 baseline vs local inference
GPT4_COST_PER_REQUEST = 0.015       # ~$0.03/1K tokens, ~500 tokens avg
LOCAL_LLM_COST_PER_REQUEST = 0.0001  # electricity only
EMBEDDING_COST_PER_REQUEST = 0.00001


class MetricsTracker:
    """Rolling window metrics tracker."""

    def __init__(self):
        self._window = settings.METRICS_WINDOW_SECONDS
        self._request_times: deque = deque()
        self._latencies: deque = deque()
        self._stages: deque = deque()

        self._total_requests = 0
        self._stage_counts = {1: 0, 2: 0, 3: 0}
        self._cache_hits = 0
        self._total_for_cache = 0

    def record_request(self, latency_ms: float, stage: PipelineStage):
        now = time.time()
        self._request_times.append(now)
        self._latencies.append((now, latency_ms))
        self._total_requests += 1
        self._prune()

    def record_stage(self, stage: int):
        self._stages.append((time.time(), stage))
        self._stage_counts[stage] = self._stage_counts.get(stage, 0) + 1

    def record_cache_hit(self):
        self._cache_hits += 1
        self._total_for_cache += 1

    def _prune(self):
        """Drop entries outside the rolling window."""
        cutoff = time.time() - self._window
        while self._request_times and self._request_times[0] < cutoff:
            self._request_times.popleft()
        while self._latencies and self._latencies[0][0] < cutoff:
            self._latencies.popleft()
        while self._stages and self._stages[0][0] < cutoff:
            self._stages.popleft()

    def snapshot(self) -> dict:
        self._prune()
        now = time.time()

        window_requests = len(self._request_times)
        throughput_rps = window_requests / self._window if window_requests > 0 else 0.0

        recent_latencies = [l for _, l in self._latencies]
        if recent_latencies:
            recent_latencies.sort()
            avg_latency = statistics.mean(recent_latencies)
            p95_latency = recent_latencies[int(len(recent_latencies) * 0.95)]
            p99_latency = recent_latencies[int(len(recent_latencies) * 0.99)]
        else:
            avg_latency = p95_latency = p99_latency = 0.0

        recent_stages = [s for _, s in self._stages]
        total_stages = len(recent_stages) or 1
        stage1_pct = sum(1 for s in recent_stages if s == 1) / total_stages
        stage2_pct = sum(1 for s in recent_stages if s == 2) / total_stages
        stage3_pct = sum(1 for s in recent_stages if s == 3) / total_stages
        llm_skip_rate = stage1_pct + stage2_pct

        total_with_cache = self._total_for_cache + self._total_requests
        cache_hit_rate = self._cache_hits / total_with_cache if total_with_cache > 0 else 0.0

        total = self._total_requests
        llm_calls = self._stage_counts.get(3, 0)
        non_llm_calls = total - llm_calls
        naive_cost = total * GPT4_COST_PER_REQUEST
        actual_cost = (
            llm_calls * LOCAL_LLM_COST_PER_REQUEST
            + non_llm_calls * EMBEDDING_COST_PER_REQUEST
        )

        return {
            "timestamp": now,
            "throughput_rps": round(throughput_rps, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "p99_latency_ms": round(p99_latency, 2),
            "stage1_pct": round(stage1_pct * 100, 1),
            "stage2_pct": round(stage2_pct * 100, 1),
            "stage3_pct": round(stage3_pct * 100, 1),
            "llm_skip_rate": round(llm_skip_rate * 100, 1),
            "cache_hit_rate": round(cache_hit_rate * 100, 1),
            "total_processed": total,
            "stage_counts": self._stage_counts,
            "estimated_cost_saved_usd": round(max(0.0, naive_cost - actual_cost), 4),
            "naive_cost_usd": round(naive_cost, 4),
            "actual_cost_usd": round(actual_cost, 6),
        }
