"""
Feed Simulator — generates realistic multilingual social media / news posts.

Simulates streaming at FEED_POSTS_PER_SECOND rate.
Uses a curated pool of claims in Hindi, Kannada, Tamil, Hinglish, and English.
"""

import asyncio
import logging
import random
import time
import uuid
from collections import deque
from typing import List, Optional

from core.config import settings
from core.pipeline import FactCheckPipeline
from models.schemas import ClaimRequest, FeedPost

logger = logging.getLogger("feed")

# ── Simulated social media / WhatsApp posts ────────────────────────────────────
SAMPLE_POSTS = [
    # English — Health
    {"text": "COVID-19 vaccines contain microchips to track people", "source": "WhatsApp", "lang": "en"},
    {"text": "5G towers spread coronavirus disease through radiation", "source": "Twitter", "lang": "en"},
    {"text": "Drinking hot water kills coronavirus instantly", "source": "Facebook", "lang": "en"},
    {"text": "WHO confirmed that COVID vaccines are safe and effective", "source": "News", "lang": "en"},
    {"text": "Climate change is a hoax invented by scientists for funding", "source": "Twitter", "lang": "en"},

    # Hindi — Politics & Health
    {"text": "भारत ने 2023 में चंद्रयान-3 को सफलतापूर्वक चंद्रमा पर उतारा", "source": "WhatsApp", "lang": "hi"},
    {"text": "5G टावर से कोरोना वायरस फैलता है यह सच है", "source": "Facebook", "lang": "hi"},
    {"text": "भारत 28 राज्यों और 8 केंद्र शासित प्रदेशों से मिलकर बना है", "source": "News", "lang": "hi"},
    {"text": "प्याज खाने से कोरोना ठीक हो जाता है", "source": "WhatsApp", "lang": "hi"},
    {"text": "भारत में पेट्रोल की कीमतें सरकार ने कम कर दी हैं", "source": "Twitter", "lang": "hi"},

    # Kannada
    {"text": "ಭಾರತ 2047 ರ ವೇಳೆಗೆ ವಿಕಸಿತ ರಾಷ್ಟ್ರವಾಗುವ ಗುರಿ ಹೊಂದಿದೆ", "source": "News", "lang": "kn"},
    {"text": "5G ಟವರ್‌ಗಳು ಕೊರೊನಾ ವೈರಸ್ ಹರಡುತ್ತವೆ ಎಂಬುದು ಸತ್ಯ", "source": "WhatsApp", "lang": "kn"},
    {"text": "ಕರ್ನಾಟಕ ರಾಜ್ಯ ಸ್ಥಾಪನೆ ದಿನ ನವೆಂಬರ್ 1 ರಂದು ಆಚರಿಸಲಾಗುತ್ತದೆ", "source": "Facebook", "lang": "kn"},

    # Tamil
    {"text": "5G தொழில்நுட்பம் கொரோனா வைரஸை பரப்புகிறது", "source": "WhatsApp", "lang": "ta"},
    {"text": "இந்தியா 15 ஆகஸ்ட் 1947 அன்று சுதந்திரம் பெற்றது", "source": "News", "lang": "ta"},
    {"text": "WHO கொரோனா தடுப்பூசி பாதுகாப்பானது என்று உறுதிப்படுத்தியுள்ளது", "source": "News", "lang": "ta"},

    # Hinglish (code-switched)
    {"text": "Ye sach hai ki bleach peene se COVID theek hota hai", "source": "WhatsApp", "lang": "hi"},
    {"text": "India ka moon mission Chandrayaan-3 successful raha 2023 mein", "source": "Twitter", "lang": "hi"},
    {"text": "Vaccine lene se log infertile ho jaate hain ye proven hai", "source": "Facebook", "lang": "hi"},

    # English — Economy & Science
    {"text": "India banned onion exports in 2023 to stabilize domestic prices", "source": "Reuters", "lang": "en"},
    {"text": "The moon landing in 1969 was completely staged by NASA", "source": "YouTube", "lang": "en"},
    {"text": "WhatsApp messages are fully end-to-end encrypted", "source": "Tech Blog", "lang": "en"},
    {"text": "Eating turmeric can cure cancer according to latest research", "source": "Facebook", "lang": "en"},
    {"text": "India has won the most Olympic gold medals in 2024", "source": "Twitter", "lang": "en"},
    {"text": "Garlic consumption has been proven to prevent COVID infection", "source": "WhatsApp", "lang": "en"},
    {"text": "IPCC confirmed humans are primarily responsible for climate change", "source": "BBC", "lang": "en"},
]

SOURCES = ["WhatsApp", "Twitter/X", "Facebook", "Telegram", "News Channel", "YouTube"]


class FeedSimulator:
    """
    Generates a continuous stream of multilingual posts and processes
    them through the fact-check pipeline.
    """

    def __init__(self, pipeline: FactCheckPipeline):
        self._pipeline = pipeline
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._history: deque = deque(maxlen=settings.FEED_MAX_HISTORY)
        self._subscribers: List[asyncio.Queue] = []

    async def start(self, posts_per_second: float = None):
        if self._running:
            return
        self._running = True
        rate = posts_per_second or settings.FEED_POSTS_PER_SECOND
        self._task = asyncio.create_task(self._run(rate))
        logger.info(f"Feed simulator started at {rate} posts/sec")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Feed simulator stopped.")

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to live feed updates (for SSE endpoint)."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._subscribers = [s for s in self._subscribers if s is not q]

    @property
    def history(self) -> List[FeedPost]:
        return list(self._history)

    async def _run(self, rate: float):
        interval = 1.0 / rate
        while self._running:
            try:
                post_data = random.choice(SAMPLE_POSTS)
                post = FeedPost(
                    id=str(uuid.uuid4())[:8],
                    text=post_data["text"],
                    source=post_data.get("source", random.choice(SOURCES)),
                    language=post_data.get("lang", "en"),
                    timestamp=time.time(),
                )

                # Run through pipeline
                try:
                    result = await self._pipeline.check_claim(
                        ClaimRequest(text=post.text, source=post.source)
                    )
                    post.result = result
                except Exception as e:
                    logger.warning(f"Pipeline error for feed post: {e}")

                self._history.append(post)

                # Notify subscribers
                for q in list(self._subscribers):
                    try:
                        q.put_nowait(post.model_dump())
                    except asyncio.QueueFull:
                        pass  # Drop if subscriber can't keep up

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Feed simulator error: {e}", exc_info=True)
                await asyncio.sleep(1.0)
