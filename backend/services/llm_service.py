"""
LLM Service — Stage 3 inference using local open-source models.

Default: google/flan-t5-base (~250MB, CPU-friendly)
Upgrade:  mistralai/Mistral-7B-Instruct-v0.2 (requires ~8GB GPU)
          meta-llama/Llama-3.2-3B-Instruct   (requires ~6GB GPU)

Only invoked for ~15% of claims that stages 1 and 2 cannot classify.
"""

import asyncio
import logging
import random
import time
from typing import Optional

from core.config import settings

logger = logging.getLogger("llm")


class LLMService:
    """Local LLM inference. Supports flan-t5 (seq2seq) and causal LMs (Mistral, Llama)."""

    def __init__(self):
        self._pipeline = None
        self._loop = None
        self._model_type = "demo"

    async def initialize(self):
        self._loop = asyncio.get_event_loop()
        await self._loop.run_in_executor(None, self._load_model)

    def _load_model(self):
        try:
            from transformers import pipeline
            import torch

            model_name = settings.LLM_MODEL
            logger.info(f"Loading LLM: {model_name}...")

            if "t5" in model_name.lower():
                self._model_type = "seq2seq"
                self._pipeline = pipeline(
                    "text2text-generation",
                    model=model_name,
                    max_new_tokens=settings.LLM_MAX_NEW_TOKENS,
                    temperature=settings.LLM_TEMPERATURE,
                    device="cpu",
                )
                logger.info("flan-t5 pipeline ready (CPU).")

            elif "mistral" in model_name.lower() or "llama" in model_name.lower():
                self._model_type = "causal"
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self._pipeline = pipeline(
                    "text-generation",
                    model=model_name,
                    max_new_tokens=settings.LLM_MAX_NEW_TOKENS,
                    temperature=settings.LLM_TEMPERATURE,
                    do_sample=True,
                    device=device,
                )
                logger.info(f"Causal LM pipeline ready ({device}).")

            else:
                raise ValueError(f"Unknown model type: {model_name}")

        except ImportError:
            logger.warning("transformers/torch not installed. LLM running in demo mode.")
            self._model_type = "demo"
        except Exception as e:
            logger.warning(f"Failed to load LLM ({e}). Running in demo mode.")
            self._model_type = "demo"

    async def generate(self, prompt: str) -> str:
        if self._model_type == "demo":
            return self._demo_response(prompt)
        return await self._loop.run_in_executor(None, self._sync_generate, prompt)

    def _sync_generate(self, prompt: str) -> str:
        try:
            if self._model_type == "seq2seq":
                return self._pipeline(prompt)[0]["generated_text"]
            elif self._model_type == "causal":
                return self._pipeline(
                    prompt,
                    return_full_text=False,
                    pad_token_id=self._pipeline.tokenizer.eos_token_id,
                )[0]["generated_text"]
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "VERDICT: UNVERIFIED\nCONFIDENCE: 0.5\nREASON: Unable to determine verdict."

    def _demo_response(self, prompt: str) -> str:
        """Simulated response used when transformers is not installed."""
        time.sleep(0.05)

        claim = ""
        for line in prompt.split("\n"):
            if line.startswith("CLAIM:"):
                claim = line.replace("CLAIM:", "").strip().lower()
                break

        false_keywords = ["hoax", "fake", "bleach", "5g causes", "moon landing fake", "not real"]
        mislead_keywords = ["out of context", "partially", "some say", "alleged"]

        if any(k in claim for k in false_keywords):
            verdict, conf = "FALSE", round(0.82 + random.uniform(-0.05, 0.05), 2)
            reason = "Claim matches known misinformation patterns."
        elif any(k in claim for k in mislead_keywords):
            verdict, conf = "MISLEADING", round(0.71 + random.uniform(-0.05, 0.05), 2)
            reason = "Claim contains contextually misleading framing."
        else:
            verdict, conf = "UNVERIFIED", round(0.52 + random.uniform(-0.05, 0.05), 2)
            reason = "Insufficient evidence to verify or refute this claim."

        return f"VERDICT: {verdict}\nCONFIDENCE: {conf}\nREASON: {reason}"
