"""
Heuristic Classifier — Stage 2 of the pipeline.

Uses rule-based analysis to classify claims without invoking the LLM.
Covers: negation detection, contradiction keywords, stance scoring, multi-fact voting.

~2ms per classification.
"""

import re
import logging
from typing import List, Tuple

from models.schemas import Verdict

logger = logging.getLogger("heuristic")

NEGATION_PATTERNS = [
    r"\bnot\b", r"\bno\b", r"\bnever\b", r"\bwithout\b", r"\bnone\b",
    r"\bneither\b", r"\bnor\b", r"\bfalsely\b", r"\bcontrary to\b",
    r"\bopposite of\b", r"\bno evidence\b", r"\bno proof\b",
    r"नहीं", r"ना\b", r"ಇಲ್ಲ", r"இல்லை",
]

CONTRADICTION_SIGNALS = {
    "false", "fake", "hoax", "misinformation", "disproven", "debunked",
    "wrong", "incorrect", "myth", "lie", "fabricated", "manipulated",
    "झूठ", "फर्जी", "गलत",
}

AGREEMENT_SIGNALS = {
    "confirmed", "verified", "true", "correct", "official", "proven",
    "fact", "real", "accurate", "genuine", "सच", "सत्य", "सही",
}

MISLEADING_SIGNALS = {
    "misleading", "out of context", "partial", "selective", "twisted",
    "exaggerated", "cherry-picked", "half-truth", "incomplete",
}


class HeuristicClassifier:
    """
    Stage 2 classifier using negation detection, keyword rules, and multi-fact voting.
    """

    async def classify(
        self,
        claim: str,
        top_facts: List[dict],
        similarity: float,
    ) -> Tuple[Verdict, float, str, str]:
        """
        Returns (verdict, confidence, reason, verdict_category).
        """
        claim_lower = claim.lower()
        claim_negated = self._has_negation(claim_lower)

        # ── Multi-fact weighted vote ──────────────────────────────────────────
        vote_scores: dict = {}
        for fact in top_facts[:3]:
            label = fact.get("verdict", "UNVERIFIED").upper()
            sim = float(fact.get("similarity", 0.0))
            if claim_negated and label == "TRUE":
                label = "FALSE"
            elif claim_negated and label == "FALSE":
                label = "TRUE"
            vote_scores[label] = vote_scores.get(label, 0.0) + sim

        best_label = max(vote_scores, key=vote_scores.get) if vote_scores else "UNVERIFIED"
        best_fact = top_facts[0] if top_facts else {}
        fact_text = best_fact.get("text", "")

        # ── Misleading signals override ───────────────────────────────────────
        if self._has_misleading_signals(claim_lower):
            return (
                Verdict.MISLEADING, 0.70,
                "Claim contains language patterns associated with misleading framing.",
                "MISLEADING_KEYWORD",
            )

        # ── Contradiction keywords in claim itself ────────────────────────────
        if self._has_contradiction_keywords(claim_lower) and best_label == "TRUE":
            return (
                Verdict.FALSE,
                round(0.68 + (similarity - 0.60) * 0.3, 4),
                f"Claim uses misinformation keywords against a verified fact: \"{fact_text[:80]}\"",
                "KEYWORD_MATCH",
            )

        # ── Return voted verdict with calibrated confidence ───────────────────
        label_map = {
            "TRUE": Verdict.TRUE, "FALSE": Verdict.FALSE,
            "MISLEADING": Verdict.MISLEADING, "UNVERIFIED": Verdict.UNVERIFIED,
        }
        verdict = label_map.get(best_label, Verdict.UNVERIFIED)
        base_conf = 0.65 + (similarity - 0.60) * 0.5
        if best_label in ("TRUE", "FALSE"):
            has_agreement = any(w in claim_lower for w in AGREEMENT_SIGNALS)
            base_conf += 0.05 if has_agreement else 0.0
        confidence = round(min(base_conf, 0.90), 4)

        negation_note = " (negation detected)" if claim_negated else ""
        verdict_category = "NEGATION" if claim_negated else "WEIGHTED_VOTE"
        reason = (
            f"Weighted vote across top-3 facts \u2192 {best_label}{negation_note}. "
            f"Top match: \"{fact_text[:80]}\""
        )
        return verdict, confidence, reason, verdict_category

    def _has_negation(self, claim: str) -> bool:
        return any(re.search(p, claim) for p in NEGATION_PATTERNS)

    def _has_misleading_signals(self, claim: str) -> bool:
        return any(w in claim for w in MISLEADING_SIGNALS)

    def _has_contradiction_keywords(self, claim: str) -> bool:
        return any(w in claim for w in CONTRADICTION_SIGNALS)
