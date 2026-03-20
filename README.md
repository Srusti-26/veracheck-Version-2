# VeraCheck

Real-time multilingual misinformation detection for vernacular news and social media. Built entirely on open-source models — no paid APIs, no data leaving your infrastructure.

---

## Overview

VeraCheck fact-checks claims in Hindi, Kannada, Tamil, Hinglish, and English using a 3-stage pipeline that routes most requests through fast vector similarity and lightweight heuristics, invoking a local LLM only when necessary. This keeps median latency under 10ms and cost near zero at scale.

**Key numbers (on the 40-fact seed dataset):**

| Metric | Value |
|---|---|
| LLM bypass rate | ~85% |
| Median latency (Stage 1) | ~0.5ms |
| Median latency (Stage 2) | ~2ms |
| Median latency (Stage 3 / LLM) | 200–2000ms |
| Cost per 1M requests vs GPT-4 | ~$1.50 vs $15,000 |

---

## Features

- **Multilingual** — detects language automatically, translates to English via Helsinki-NLP models, then embeds and searches
- **3-stage pipeline** — vector similarity → heuristic rules → local LLM (only ~15% of claims reach the LLM)
- **Live feed** — simulates a stream of social media posts processed in real time via SSE
- **Explainability** — every verdict shows the top retrieved facts and similarity scores
- **Admin panel** — add/delete facts at runtime, export results as CSV
- **Redis cache** — deduplicates repeated claims; falls back to in-memory if Redis is unavailable
- **Offline capable** — works without internet after initial model download

---

## Architecture

```
Incoming claim (any language)
        │
        ▼
  Translate → English   ~5ms
        │
        ▼
  Embed (MiniLM-L12)    ~5ms
        │
        ▼
  FAISS search (top-5)  ~1ms
        │
        ├── cos_sim ≥ 0.88 → Stage 1: Auto-classify     ~0.5ms  (~65% of claims)
        ├── cos_sim ≥ 0.65 → Stage 2: Heuristic rules   ~2ms    (~20% of claims)
        └── cos_sim < 0.65 → Stage 3: Local LLM         ~200ms  (~15% of claims)
```

**Stack:**
- Backend: FastAPI + FAISS + SentenceTransformers + HuggingFace Transformers
- Frontend: Next.js 14 + Tailwind CSS + Recharts
- Cache: Redis (with in-memory fallback)
- Models: `paraphrase-multilingual-MiniLM-L12-v2` (embedding), `google/flan-t5-base` (LLM default), Helsinki-NLP opus-mt (translation)

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- 4GB RAM minimum (8GB+ recommended if using Mistral-7B)
- Redis (optional — system works without it)

---

## Setup

### Option A: Manual (recommended for development)

**1. Clone and enter the project**
```bash
git clone https://github.com/yourrepo/veracheck
cd veracheck
```

**2. Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

**3. Frontend**
```bash
cd ../frontend
npm install
cp .env.local.example .env.local
```

### Option B: Docker Compose

```bash
docker compose up --build
```

First run downloads ~500MB of models. Subsequent starts use the cached volume.

---

## Running

**Backend** (from `backend/` with venv active):
```bash
uvicorn main:app --reload --port 8000
```

**Frontend** (from `frontend/`):
```bash
npm run dev
```

Open **http://localhost:3000**

API docs available at **http://localhost:8000/docs**

---

## Models

Models download automatically from HuggingFace on first run.

| Model | Size | Purpose | Notes |
|---|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` | ~120MB | Embeddings | Auto-downloads |
| `google/flan-t5-base` | ~250MB | LLM (Stage 3) | Default, CPU-friendly |
| `mistralai/Mistral-7B-Instruct-v0.2` | ~14GB | LLM (Stage 3) | Requires 8GB GPU |
| `meta-llama/Llama-3.2-3B-Instruct` | ~6GB | LLM (Stage 3) | Requires 6GB GPU |
| `Helsinki-NLP/opus-mt-{src}-en` | ~300MB each | Translation | Loads per language on demand |

To switch the LLM, set `LLM_MODEL` in your `.env`:
```
LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.2
```

For Mistral or Llama, you need a HuggingFace account with model access:
```bash
huggingface-cli login
```

---

## Configuration

All settings are in `backend/.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `LLM_MODEL` | `google/flan-t5-base` | LLM for Stage 3 |
| `HIGH_SIM_THRESHOLD` | `0.88` | Similarity cutoff for Stage 1 auto-classify |
| `MID_SIM_THRESHOLD` | `0.65` | Similarity cutoff for Stage 2 heuristic |
| `FAISS_TOP_K` | `5` | Number of facts retrieved per query |
| `FEED_POSTS_PER_SECOND` | `10.0` | Live feed simulation rate |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection (optional) |

---

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/claims/check` | POST | Fact-check a single claim |
| `/api/v1/claims/batch` | POST | Enqueue a batch of claims |
| `/api/v1/claims/job/{id}` | GET | Poll batch job result |
| `/api/v1/feed/stream` | GET | SSE live feed |
| `/api/v1/feed/history` | GET | Recent feed posts |
| `/api/v1/metrics/snapshot` | GET | Live metrics |
| `/api/v1/facts/` | GET/POST | List or add facts |
| `/api/v1/admin/export/csv` | GET | Export results as CSV |
| `/api/v1/admin/config` | GET | Current pipeline config |
| `/docs` | GET | Swagger UI |

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/claims/check \
  -H "Content-Type: application/json" \
  -d '{"text": "5G towers spread coronavirus"}'
```

```json
{
  "claim": "5G towers spread coronavirus",
  "english_claim": "5G towers spread coronavirus",
  "detected_language": "en",
  "verdict": "FALSE",
  "confidence": 0.9412,
  "explanation": "[Stage 1 — Auto] Near-identical to known FALSE statement...",
  "pipeline_stage": "STAGE1_AUTO",
  "latency_ms": 4.2
}
```

---

## Adding Facts

Via API:
```bash
curl -X POST http://localhost:8000/api/v1/facts/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Your fact here", "verdict": "TRUE", "source": "Source Name"}'
```

Or edit `data/seed_facts.json` and restart the backend.

---

## Project Structure

```
veracheck/
├── backend/
│   ├── main.py                     # FastAPI app + startup/shutdown
│   ├── core/
│   │   ├── config.py               # All settings (env-driven)
│   │   ├── pipeline.py             # 3-stage pipeline logic
│   │   └── metrics_tracker.py      # Rolling metrics
│   ├── api/routes/
│   │   ├── claims.py
│   │   ├── feed.py
│   │   ├── facts.py
│   │   ├── metrics.py
│   │   └── admin.py
│   ├── services/
│   │   ├── embedding_service.py    # SentenceTransformers wrapper
│   │   ├── fact_store.py           # FAISS index + fact DB
│   │   ├── heuristic_classifier.py # Stage 2 rule engine
│   │   ├── llm_service.py          # Stage 3 LLM inference
│   │   ├── translation_service.py  # Helsinki-NLP translation
│   │   ├── feed_simulator.py       # Live feed generator
│   │   └── redis_cache.py          # Redis + in-memory fallback
│   ├── models/schemas.py           # Pydantic v2 models
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── pages/index.tsx             # Main dashboard
│   ├── components/
│   │   ├── CheckerInput.tsx        # Manual fact-check input
│   │   ├── LiveFeedPanel.tsx       # SSE live feed display
│   │   ├── ResultsPanel.tsx        # Verdict display
│   │   ├── MetricsDashboard.tsx    # Recharts metrics
│   │   ├── ExplainabilityPanel.tsx # Retrieved evidence
│   │   ├── PipelineViz.tsx         # Stage visualization
│   │   └── AdminPanel.tsx          # Fact management
│   ├── styles/globals.css
│   └── package.json
├── data/
│   └── seed_facts.json             # 40 verified facts
├── docker/
│   └── docker-compose.yml
└── scripts/
    └── dev.sh                      # One-command dev start (Linux/macOS)
```

---

## Common Issues

**Backend fails to start — model download error**
- Check your internet connection on first run. Models are cached after the first download.
- If behind a proxy, set `HF_HUB_OFFLINE=1` and pre-download models manually.

**`faiss` import error**
- Run `pip install faiss-cpu`. The system falls back to numpy brute-force search if FAISS is unavailable, but it's slower.

**Translation not working for a language**
- The Helsinki-NLP model for that language pair may not exist. The service falls back to passing the original text through untranslated.

**Redis connection refused**
- Redis is optional. The system automatically falls back to an in-memory cache. No action needed.

**Frontend shows "Failed to connect to API"**
- Ensure the backend is running on port 8000 and `NEXT_PUBLIC_API_URL` in `frontend/.env.local` matches.

---

## Future Improvements

- Fine-tune the embedding model on regional dialects (Hinglish, code-switched text)
- Replace the asyncio queue with Apache Kafka for horizontal scaling
- Add FAISS IVF index for 1M+ fact databases
- Persistent storage for fact database and audit logs
- User feedback loop to improve verdict accuracy over time
