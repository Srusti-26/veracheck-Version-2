"""
Translation Service — multilingual translation to English.

Primary: Helsinki-NLP opus-mt models (where available)
Fallback: deep-translator (free, no API key) using Google Translate
Language detection via langdetect with Unicode script fallback.
"""

import asyncio
import logging
from typing import Dict, Optional

from core.config import settings

logger = logging.getLogger("translation")

LANG_NAMES = {
    "en": "English", "hi": "Hindi", "kn": "Kannada", "ta": "Tamil",
    "te": "Telugu", "mr": "Marathi", "bn": "Bengali", "pa": "Punjabi",
    "ur": "Urdu", "gu": "Gujarati",
}

# Helsinki-NLP models that actually exist on HuggingFace (verified)
# Tamil uses 'mul-en' (multilingual) since opus-mt-ta-en doesn't exist
HELSINKI_SUPPORTED = {"hi", "te", "mr", "bn", "pa"}

# Override model names for languages where the direct model doesn't exist
HELSINKI_MODEL_OVERRIDES = {
    "ta": "Helsinki-NLP/opus-mt-mul-en",  # Tamil via multilingual model
}

# Languages we trust from langdetect — reject anything not in this set
TRUSTED_LANGUAGES = {
    "en", "hi", "kn", "ta", "te", "mr", "bn", "pa", "ur", "gu"
}


class TranslationService:
    """Language detection + translation to English."""

    def __init__(self):
        self._translators: Dict[str, any] = {}
        self._loop = None
        self._translation_cache: Dict[str, str] = {}
        self._deep_translator_available = False

    async def initialize(self):
        self._loop = asyncio.get_event_loop()
        # Check if deep-translator is available
        await self._loop.run_in_executor(None, self._check_deep_translator)
        await self._load_translator("hi")  # pre-load Hindi
        logger.info("Translation service ready.")

    def _check_deep_translator(self):
        try:
            from deep_translator import GoogleTranslator
            GoogleTranslator(source="hi", target="en").translate("test")
            self._deep_translator_available = True
            logger.info("deep-translator (Google) available as fallback.")
        except Exception as e:
            logger.warning(f"deep-translator not available: {e}")

    async def detect_language(self, text: str) -> str:
        result = await self._loop.run_in_executor(None, self._sync_detect, text)
        lang = result or "en"
        logger.debug(f"Detected language: {LANG_NAMES.get(lang, lang)}")
        return lang

    def _sync_detect(self, text: str) -> str:
        try:
            from langdetect import detect
            detected = detect(text).split("-")[0]
            # Reject misdetections — fall back to script heuristic
            if detected not in TRUSTED_LANGUAGES:
                return self._script_detect(text)
            return detected
        except Exception:
            return self._script_detect(text)

    @staticmethod
    def _script_detect(text: str) -> str:
        scores = {
            "hi": sum(1 for c in text if "\u0900" <= c <= "\u097F"),
            "kn": sum(1 for c in text if "\u0C80" <= c <= "\u0CFF"),
            "ta": sum(1 for c in text if "\u0B80" <= c <= "\u0BFF"),
            "te": sum(1 for c in text if "\u0C00" <= c <= "\u0C7F"),
            "bn": sum(1 for c in text if "\u0980" <= c <= "\u09FF"),
        }
        best = max(scores, key=scores.get)
        return best if scores[best] > 3 else "en"

    async def translate_to_english(self, text: str, source_lang: str) -> str:
        if source_lang == "en":
            return text
        cache_key = f"{source_lang}:{text[:100]}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]
        translated = await self._loop.run_in_executor(
            None, self._sync_translate, text, source_lang
        )
        self._translation_cache[cache_key] = translated
        return translated

    def _sync_translate(self, text: str, source_lang: str) -> str:
        # Try Helsinki-NLP first (only for supported languages)
        helsinki_supported = HELSINKI_SUPPORTED | set(HELSINKI_MODEL_OVERRIDES.keys())
        if source_lang in helsinki_supported:
            result = self._try_helsinki(text, source_lang)
            if result and result != text:
                return result

        # Fallback: deep-translator (free Google Translate wrapper)
        if self._deep_translator_available:
            result = self._try_deep_translator(text, source_lang)
            if result and result != text:
                return result

        logger.warning(f"All translation methods failed for {source_lang}. Returning original.")
        return text

    def _try_helsinki(self, text: str, source_lang: str) -> Optional[str]:
        try:
            translator = self._translators.get(source_lang)
            if translator is None:
                # Use override model name if available
                model_name = HELSINKI_MODEL_OVERRIDES.get(
                    source_lang,
                    f"{settings.TRANSLATION_MODEL_PREFIX}-{source_lang}-en"
                )
                self._sync_load_translator(source_lang, model_name)
                translator = self._translators.get(source_lang)
            if translator is None:
                return None
            return translator(text, max_length=512)[0]["translation_text"]
        except Exception as e:
            logger.warning(f"Helsinki translation failed ({source_lang}): {e}")
            return None

    def _try_deep_translator(self, text: str, source_lang: str) -> Optional[str]:
        try:
            from deep_translator import GoogleTranslator
            return GoogleTranslator(source=source_lang, target="en").translate(text)
        except Exception as e:
            logger.warning(f"deep-translator failed ({source_lang}): {e}")
            return None

    async def _load_translator(self, source_lang: str):
        supported = HELSINKI_SUPPORTED | set(HELSINKI_MODEL_OVERRIDES.keys())
        if source_lang not in supported:
            return
        if source_lang in self._translators:
            return
        model_name = HELSINKI_MODEL_OVERRIDES.get(
            source_lang,
            f"{settings.TRANSLATION_MODEL_PREFIX}-{source_lang}-en"
        )
        await self._loop.run_in_executor(
            None, self._sync_load_translator, source_lang, model_name
        )

    def _sync_load_translator(self, source_lang: str, model_name: str):
        try:
            from transformers import pipeline
            logger.info(f"Loading translation model: {model_name}...")
            self._translators[source_lang] = pipeline(
                "translation", model=model_name, device="cpu"
            )
            logger.info(f"Translation model ready: {model_name}")
        except Exception as e:
            logger.warning(f"Could not load {model_name}: {e}")
            self._translators[source_lang] = None
