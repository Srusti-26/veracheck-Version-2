"""
Wikipedia Service — free open-source API for claim cross-referencing.

Uses Wikipedia REST API (no key required).
Extracts topic keywords from the claim before searching to avoid
irrelevant results. Validates result relevance before returning.
"""

import logging
import re
import httpx

logger = logging.getLogger("wikipedia")

WIKI_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
TIMEOUT = 4.0

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "this", "that", "these",
    "those", "it", "its", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "as", "into", "through", "about",
    "not", "no", "nor", "so", "yet", "both", "either", "neither",
    "according", "confirmed", "proven", "said", "claim", "claims",
    "true", "false", "fake", "hoax", "real", "fact",
}

# Maps claim keywords to focused Wikipedia search queries
TOPIC_HINTS = {
    "5g":             "5G technology health effects misinformation",
    "vaccine":        "COVID-19 vaccine safety effectiveness",
    "covid":          "COVID-19 coronavirus facts",
    "corona":         "COVID-19 coronavirus facts",
    "moon":           "Apollo Moon landing NASA",
    "chandrayaan":    "Chandrayaan-3 ISRO lunar mission",
    "climate":        "climate change scientific consensus",
    "bleach":         "bleach ingestion health dangers",
    "microchip":      "COVID vaccine microchip conspiracy theory",
    "garlic":         "garlic health benefits COVID myths",
    "turmeric":       "turmeric curcumin cancer research",
    "ivermectin":     "ivermectin COVID-19 treatment evidence",
    "upi":            "Unified Payments Interface India",
    "aadhaar":        "Aadhaar biometric identification India",
    "demonetization": "India demonetization 2016 effects",
    "flat earth":     "flat Earth theory debunked",
    "autism":         "vaccine autism myth debunked",
    "hydroxychloroquine": "hydroxychloroquine COVID-19 treatment",
    "ivermectin":     "ivermectin COVID-19 WHO recommendation",
    "onion":          "India onion export ban 2023",
    "g20":            "G20 India 2023 presidency",
}


class WikipediaService:

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def initialize(self):
        self._client = httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": "VeraCheck/1.0"})
        logger.info("Wikipedia service ready.")

    async def close(self):
        if self._client:
            await self._client.aclose()

    async def get_evidence(self, claim: str) -> str | None:
        """
        Search Wikipedia for the claim topic and return a relevant summary.
        Returns None if no relevant article found or on error.
        """
        try:
            query = self._build_query(claim)
            titles = await self._search(query, limit=3)
            if not titles:
                return None

            claim_keywords = self._keywords(claim)
            for title in titles:
                if self._is_relevant(title, claim_keywords):
                    summary = await self._summary(title)
                    if summary:
                        return f"[Wikipedia: {title}] {summary}"
            return None
        except Exception as e:
            logger.debug(f"Wikipedia lookup failed: {e}")
            return None

    def _build_query(self, claim: str) -> str:
        claim_lower = claim.lower()
        for keyword, hint_query in TOPIC_HINTS.items():
            if keyword in claim_lower:
                return hint_query
        # Fallback: strip stopwords, keep top 4 keywords
        words = re.findall(r'\b[a-zA-Z]{3,}\b', claim)
        keywords = [w for w in words if w.lower() not in STOPWORDS]
        return " ".join(keywords[:4]) if keywords else claim[:60]

    def _keywords(self, text: str) -> set:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        return {w for w in words if w not in STOPWORDS}

    def _is_relevant(self, title: str, claim_keywords: set) -> bool:
        title_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', title.lower()))
        return len(title_words & claim_keywords) >= 1

    async def _search(self, query: str, limit: int = 3) -> list:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "utf8": 1,
        }
        resp = await self._client.get(WIKI_SEARCH_URL, params=params)
        results = resp.json().get("query", {}).get("search", [])
        return [r["title"] for r in results]

    async def _summary(self, title: str) -> str | None:
        url = WIKI_SUMMARY_URL.format(title.replace(" ", "_"))
        resp = await self._client.get(url)
        extract = resp.json().get("extract", "")
        sentences = re.split(r'(?<=[.!?])\s+', extract.strip())
        return " ".join(sentences[:2]) if sentences else None
