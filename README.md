# Samvaya — Unified Business Identifier (UBID) Platform

> **AI Bharat Hackathon 2025 | Theme 1 — Karnataka Commerce & Industry**
>
> An end-to-end entity resolution and active business intelligence platform that assigns every Karnataka business a single Unified Business Identifier (UBID) by linking fragmented records across government department systems — without modifying any source system.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [What Samvaya Does](#2-what-samvaya-does)
3. [Architecture Overview](#3-architecture-overview)
4. [Tech Stack](#4-tech-stack)
5. [ML Pipeline](#5-ml-pipeline)
6. [Feature Engineering](#6-feature-engineering)
7. [Activity Intelligence Engine](#7-activity-intelligence-engine)
8. [Project Structure](#8-project-structure)
9. [Quick Start (Local)](#9-quick-start-local)
10. [Deployment (ngrok + Vercel)](#10-deployment-ngrok--vercel)
11. [Environment Variables](#11-environment-variables)
12. [API Reference](#12-api-reference)
13. [Frontend Pages](#13-frontend-pages)
14. [Running the Data Pipeline](#14-running-the-data-pipeline)
15. [Model Performance](#15-model-performance)
16. [Non-Negotiables Addressed](#16-non-negotiables-addressed)
17. [Future Scope](#17-future-scope)

---

## 1. Problem Statement

Karnataka's regulatory landscape spans 40+ state department systems — Shop Establishment, Factories, Labour, KSPCB, BESCOM, BWSSB, Fire, Food Safety, and more. Each was built in isolation with its own schema and identifiers. The same physical business appears as different records in different databases, making it impossible to answer basic questions like:

> *"How many businesses are actually operating in PIN 560058 and which haven't had an inspection in 18 months?"*

**Part A** — Automatically link records from 4 department systems that refer to the same real-world business and assign each a UBID.

**Part B** — Given a stream of activity events (inspections, renewals, compliance filings), classify each UBID as **Active**, **Dormant**, or **Closed** with an explainable evidence trail.

**Hard constraints:**
- Source department systems cannot be modified
- Raw PII cannot be sent to hosted LLMs
- Every automated decision must be explainable and reversible
- Ambiguous matches go to human review — never silently merged

---

## 2. What Samvaya Does

| Capability | Description |
|---|---|
| **UBID Assignment** | Links records across Shop Establishment, Factories, Labour, and KSPCB into a single canonical entity |
| **Confidence-Based Routing** | Score ≥ 0.95 → auto-link; 0.75–0.95 → human review queue; < 0.75 → stays separate |
| **Explainable Decisions** | SHAP values per pair show exactly which features drove the match score |
| **Activity Classification** | Classifies each UBID as Active / Dormant / Closed from heterogeneous event signals |
| **Reviewer Workflow** | Reviewers see evidence, SHAP explanations, and can CONFIRM or REJECT linkages |
| **NL Query** | Natural language interface for querying the UBID registry |
| **Analytics Dashboard** | Score distributions, department coverage, activity breakdowns, SHAP visualisations |
| **Audit Trail** | Every decision, ingestion, and API call is logged immutably |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          React Frontend                             │
│           (Vercel — global CDN, zero server cost)                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS (via ngrok static domain)
┌──────────────────────────────▼──────────────────────────────────────┐
│                        FastAPI Backend                               │
│              /api/ubid  /api/activity  /api/review                  │
│              /api/admin  /api/nlquery                               │
└────┬──────────────┬──────────────┬───────────────┬──────────────────┘
     │              │              │               │
┌────▼────┐  ┌──────▼──────┐ ┌────▼────┐  ┌───────▼───────┐
│Postgres │  │    Redis    │ │RabbitMQ │  │    Celery     │
│(primary │  │(cache +     │ │(message │  │   Workers     │
│  store) │  │task results)│ │ broker) │  │(async pipeline│
└─────────┘  └─────────────┘ └─────────┘  └───────────────┘
     │
┌────▼────────────────────────────────────────────────────────────────┐
│                     ML Pipeline (local)                              │
│  Synthetic Data → Normalisation → Blocking → Feature Extraction      │
│  → LightGBM Scoring → UBID Assignment → Activity Classification     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key design principle:** All computation (ML, Ollama, Nominatim) runs locally. The frontend is statically hosted on Vercel. Traffic to the local backend tunnels through a permanent ngrok static domain — no cloud compute cost.

---

## 4. Tech Stack

### Backend
| Component | Technology |
|---|---|
| API Framework | FastAPI 0.104 |
| Database | PostgreSQL 15 + SQLAlchemy 2.0 + Alembic |
| Caching | Redis 7 |
| Task Queue | Celery 5.3 + RabbitMQ 3.13 |
| Geocoding | Nominatim (self-hosted, India OSM data) |
| ML Tracking | MLflow |

### Machine Learning
| Component | Technology |
|---|---|
| Classifier | LightGBM 4.1 (calibrated with sigmoid) |
| Explainability | SHAP TreeExplainer |
| Semantic Embedding (F14) | `paraphrase-multilingual-mpnet-base-v2` (sentence-transformers) |
| String Similarity | RapidFuzz (Jaro-Winkler, token set ratio) |
| Phonetic Matching | Jellyfish, Metaphone |
| Transliteration | indic-transliteration |

### Frontend
| Component | Technology |
|---|---|
| Framework | React 19 + TypeScript |
| UI Library | Ant Design 6 |
| Charts | Recharts |
| Maps | React Leaflet |
| Animations | Framer Motion |
| Icons | Lucide React |
| HTTP | Axios |
| Routing | React Router 7 |

### Infrastructure
| Component | Technology |
|---|---|
| Containerisation | Docker Compose |
| Frontend Hosting | Vercel (free tier) |
| Tunnel | ngrok (permanent static domain) |
| LLM (local) | Ollama — `llama3.1:8b` |
| LLM (cloud) | Google Gemini / Groq (PII-free queries only) |

---

## 5. ML Pipeline

The entity resolution pipeline runs in four stages:

```
Stage 1 — Normalisation
  Raw dept records → canonical_name, canonical_address, validated PAN/GSTIN,
  geocoded lat/lng (Nominatim), transliterated script

Stage 2 — Blocking
  Reduces O(n²) candidate pairs to tractable set via:
  • Pin code proximity blocks
  • PAN/GSTIN exact-match blocks
  • Name n-gram index blocks

Stage 3 — Feature Extraction (14 features per pair)
  See Feature Engineering section below

Stage 4 — Scoring & Routing
  LightGBM (calibrated) → confidence score → route to:
  • AUTO_LINK  (score ≥ 0.95)
  • REVIEW     (0.75 ≤ score < 0.95)
  • SEPARATE   (score < 0.75)
```

**Training data:** 6,574 labelled pairs (5,259 train / 1,315 val) generated from 5,000 synthetic ground-truth entities with deterministic variations injected across 4 simulated department systems.

---

## 6. Feature Engineering

| Feature | Description |
|---|---|
| **F01** | Name Jaro-Winkler similarity on canonical names |
| **F02** | Token Set Ratio (handles reordered tokens) |
| **F03** | Abbreviation match score |
| **F04** | PAN exact match (1.0 / 0.0 / null) |
| **F05** | GSTIN exact match (1.0 / 0.0 / null) |
| **F06** | Pin code match — 1.0 exact, 0.7 adjacent, 0.0 different |
| **F07** | Haversine geo-distance normalised to [0, 1] (≥ 2 km → 1.0) |
| **F08** | Phone number similarity |
| **F09** | Owner name Jaro-Winkler |
| **F10** | NIC sector code match (2-digit) |
| **F11** | Registration year proximity |
| **F12** | Address token overlap |
| **F13** | Phonetic name similarity (Metaphone / Soundex) |
| **F14** | Multilingual semantic cosine similarity (`paraphrase-multilingual-mpnet-base-v2`) — runs entirely on local GPU, no API call |

`None` features are handled as `np.nan` — LightGBM processes them natively.

---

## 7. Activity Intelligence Engine

Each UBID accumulates activity events from department systems (inspections, licence renewals, compliance filings, utility readings). The engine:

1. **Routes** incoming events to the correct UBID (or queues unmatched events for review)
2. **Scores** each event type by a configurable weight and exponential time-decay (half-life per signal type)
3. **Classifies** each UBID as:
   - `ACTIVE` — recent, consistent signals
   - `DORMANT` — stale signals (no meaningful activity in configurable window)
   - `CLOSED` — explicit closure event or prolonged absence across all signal types
4. **Explains** every verdict: the reviewer sees which events contributed, over what time window, and what their decayed weights were

Signal weights and half-lives are fully configurable in `src/activity_engine/signal_config.py` without code changes.

---

## 8. Project Structure

```
Samvaya-main/
├── docker-compose.yml           # Full stack (postgres, redis, rabbitmq, backend, frontend)
├── Dockerfile.backend
├── .env.example                 # Template — copy to .env and fill in secrets
├── alembic.ini
├── alembic/                     # DB migrations
│   └── versions/
├── requirements.txt
│
├── scripts/
│   ├── generate_synthetic_data.py   # Step 1 — generate 5,000 synthetic businesses
│   ├── run_pipeline.py              # Step 2 — full ER + activity pipeline
│   ├── train_model.py               # Train / retrain LightGBM model
│   ├── init_db.py                   # Apply schema migrations
│   └── reset_demo.py                # Wipe and re-run from scratch
│
├── src/
│   ├── api/
│   │   ├── main.py                  # FastAPI app + CORS + middleware
│   │   ├── routers/
│   │   │   ├── ubid.py              # UBID lookup, search, detail
│   │   │   ├── activity.py          # Activity scores and event timelines
│   │   │   ├── review.py            # Review queue endpoints
│   │   │   ├── admin.py             # Admin console + pipeline triggers
│   │   │   └── nlquery.py           # Natural language query interface
│   │   └── schemas/                 # Pydantic request/response models
│   │
│   ├── entity_resolution/
│   │   ├── blocker.py               # Candidate pair generation
│   │   ├── feature_extractor.py     # 14-feature vector computation
│   │   ├── scorer.py                # LightGBM scoring + SHAP
│   │   ├── ubid_assigner.py         # Connected-components UBID assignment
│   │   └── models/
│   │       ├── lgbm_model.pkl
│   │       ├── calibrated_model.pkl
│   │       └── metrics.json
│   │
│   ├── normalisation/
│   │   ├── name_normaliser.py
│   │   ├── address_parser.py        # PIN code adjacency, street parsing
│   │   ├── identifier_validator.py  # PAN/GSTIN validation
│   │   ├── pii_scrambler.py         # Deterministic PII scrambling before LLM calls
│   │   ├── geocoder.py              # Nominatim integration
│   │   └── standardiser.py          # Orchestrator
│   │
│   ├── activity_engine/
│   │   ├── event_router.py          # Event → UBID matching
│   │   ├── signal_scorer.py         # Weighted time-decay scoring
│   │   ├── activity_classifier.py   # ACTIVE / DORMANT / CLOSED verdict
│   │   └── signal_config.py         # Weights and half-lives (configurable)
│   │
│   ├── data_generation/
│   │   ├── entity_generator.py      # 5,000 canonical ground-truth businesses
│   │   ├── department_record_generator.py
│   │   ├── variation_injector.py    # Typos, abbrevs, format variations
│   │   ├── activity_event_generator.py
│   │   └── dictionaries/            # Karnataka names, streets, NIC codes, PIN codes
│   │
│   ├── database/
│   │   ├── models.py                # All SQLAlchemy ORM models
│   │   └── connection.py
│   │
│   ├── cache.py                     # Redis get/set/delete helpers
│   ├── celery_app.py                # Celery app definition
│   └── llm_router.py                # Routes between Ollama / Gemini / Groq
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # Router + sidebar layout + auth guard
│   │   ├── api.ts                   # Axios instance with ngrok header
│   │   └── pages/
│   │       ├── HomePage.tsx         # Landing page with animations
│   │       ├── LoginPage.tsx
│   │       ├── LookupView.tsx       # UBID directory search
│   │       ├── UbidDetailView.tsx   # Full UBID detail + SHAP + map
│   │       ├── ActivityView.tsx     # Activity intelligence dashboard
│   │       ├── ReviewQueueView.tsx  # Human reviewer interface
│   │       ├── AnalyticsView.tsx    # Charts and metrics
│   │       └── AdminView.tsx        # Pipeline controls + system status
│   └── public/
│
└── tests/                           # Pytest test suite
    ├── test_blocker.py
    ├── test_feature_extractor.py
    ├── test_scorer.py
    ├── test_normalisation.py
    └── test_activity_engine.py
```

---

## 9. Quick Start (Local)

### Prerequisites
- Docker Desktop (Windows/Mac/Linux)
- Python 3.11+
- Node.js 18+ (for frontend dev)
- ngrok account (free) with a static domain

### Step 1 — Environment Setup

```bash
cp .env.example .env
# Edit .env — fill in GEMINI_API_KEY, GROQ_API_KEY, and your ngrok domain in CORS_ORIGINS
```

`.env` minimum required:
```env
POSTGRES_USER=ubid
POSTGRES_PASSWORD=ubid_secret
POSTGRES_DB=ubid_platform
SCRAMBLER_SECRET_KEY=change_me_in_prod
CORS_ORIGINS=http://localhost:3000
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
```

### Step 2 — Start Infrastructure

```bash
docker compose up -d postgres redis rabbitmq
```

### Step 3 — Initialise the Database

```bash
docker compose run --rm backend python -m alembic upgrade head
```

### Step 4 — Generate Synthetic Data & Run Pipeline

```bash
# Generate 5,000 synthetic Karnataka businesses across 4 dept systems
docker compose run --rm backend python scripts/generate_synthetic_data.py

# Run full entity resolution + activity classification pipeline
docker compose run --rm backend python scripts/run_pipeline.py
```

This produces ~4,700 UBIDs from ~187,000 candidate pairs.

### Step 5 — Start Backend

```bash
docker compose up -d backend celery_worker
```

Backend is now live at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

### Step 6 — Start Frontend

```bash
cd frontend
npm install
npm start
```

Frontend at `http://localhost:3000`.

### Login

Default password: `samvaya2024` (set in `AdminView` / `LoginPage`).

---

## 10. Deployment (ngrok + Vercel)

The production deployment runs the backend locally and tunnels it through a permanent ngrok static domain, with the frontend hosted on Vercel.

### Backend Tunnel (ngrok)

Install ngrok and configure `~/.config/ngrok/ngrok.yml` (or `%APPDATA%/ngrok/ngrok.yml` on Windows):

```yaml
version: "2"
authtoken: YOUR_NGROK_AUTH_TOKEN
tunnels:
  samvaya:
    proto: http
    addr: 8000
    domain: YOUR-STATIC-DOMAIN.ngrok-free.app
```

Start the tunnel:
```bash
ngrok start samvaya
```

The static domain never changes between restarts — no Vercel redeployment needed.

**Auto-start on Windows:** Place a shortcut to `ngrok start samvaya` in `shell:startup`.

### Frontend (Vercel)

1. Push the `frontend/` directory to GitHub
2. Import the repo into Vercel, set root directory to `frontend/`
3. Set environment variables in Vercel:
   - `REACT_APP_API_URL` = `https://YOUR-STATIC-DOMAIN.ngrok-free.app`
   - `CI` = `false`
4. Redeploy

### CORS Configuration

In your `.env` on the machine running Docker:
```env
CORS_ORIGINS=http://localhost:3000,https://your-vercel-app.vercel.app,https://YOUR-STATIC-DOMAIN.ngrok-free.app
```

Then force-recreate the backend container to reload env vars:
```bash
docker compose up -d --force-recreate backend
```

---

## 11. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` | `ubid` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `ubid_secret` | PostgreSQL password |
| `POSTGRES_DB` | `ubid_platform` | Database name |
| `SCRAMBLER_SECRET_KEY` | — | Secret for PII scrambling (change in prod) |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GROQ_API_KEY` | — | Groq API key |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Local Ollama endpoint |
| `OLLAMA_MODEL` | `llama3.1:8b` | Ollama model name |
| `FORCE_LOCAL_ONLY` | `false` | If `true`, only uses Ollama — no cloud LLM calls |
| `THRESHOLD_AUTO_LINK` | `0.95` | Score above which pairs are auto-linked |
| `THRESHOLD_REVIEW` | `0.75` | Score above which pairs go to review queue |
| `SKIP_LLM_PARSING` | `false` | Skip LLM address parsing (speeds up pipeline) |
| `SKIP_SEMANTIC_EMBED` | `false` | Skip F14 embedding (speeds up bulk runs) |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `NOMINATIM_URL` | `http://nominatim:8080` | Self-hosted Nominatim URL |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | MLflow server URL |

---

## 12. API Reference

All endpoints are prefixed with `/api`. Interactive docs: `http://localhost:8000/docs`.

### UBID Endpoints (`/api/ubid`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/ubid/search` | Search UBIDs by name, PIN code, or identifier |
| `GET` | `/api/ubid/{ubid}` | Full UBID detail (linked records, SHAP, activity) |
| `GET` | `/api/ubid/{ubid}/sources` | Source records linked to a UBID |
| `GET` | `/api/ubid/{ubid}/evidence` | Linkage evidence and SHAP values |

### Activity Endpoints (`/api/activity`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/activity/scores` | Paginated list of UBIDs with activity scores |
| `GET` | `/api/activity/{ubid}/timeline` | Event timeline for a specific UBID |
| `GET` | `/api/activity/summary` | Aggregated ACTIVE / DORMANT / CLOSED counts |

### Review Endpoints (`/api/review`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/review/queue` | Pending review tasks |
| `POST` | `/api/review/{task_id}/decide` | Submit CONFIRM or REJECT decision |
| `GET` | `/api/review/stats` | Review queue statistics |

### Admin Endpoints (`/api/admin`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/admin/pipeline/run` | Trigger full pipeline (async via Celery) |
| `GET` | `/api/admin/pipeline/status` | Pipeline job status |
| `GET` | `/api/admin/metrics` | System health and model metrics |

### Health Check

```
GET /health → {"status": "ok", "service": "ubid-platform"}
```

---

## 13. Frontend Pages

| Page | Route | Description |
|---|---|---|
| **Home** | `/` | Landing page — platform overview, feature cards, how-it-works flow |
| **Login** | `/login` | Password-based authentication |
| **UBID Directory** | `/dashboard/lookup` | Search and browse all UBIDs |
| **UBID Detail** | `/ubid/:ubid` | Full entity view — sources, SHAP chart, map, event timeline |
| **Activity Intelligence** | `/dashboard/activity` | Activity scores, status distribution, dormant business alerts |
| **Reviewer Queue** | `/dashboard/review` | Human-in-the-loop review interface with evidence panel |
| **Analytics** | `/dashboard/analytics` | Score distributions, department coverage, trend charts |
| **Admin Console** | `/dashboard/admin` | Pipeline controls, system status, model metrics |

All dashboard routes are protected behind `RequireAuth` — unauthenticated users are redirected to `/login`.

---

## 14. Running the Data Pipeline

### Full Reset

```bash
docker compose run --rm backend python scripts/reset_demo.py
```

This drops all UBID data and reruns the pipeline from raw synthetic records.

### Pipeline Only (no data regeneration)

```bash
docker compose run --rm backend python scripts/run_pipeline.py
```

### Retrain the Model

```bash
docker compose run --rm backend python scripts/train_model.py
```

The retrained model is saved to `src/entity_resolution/models/` and picked up automatically on the next backend restart.

### Flush Redis Cache

If you see stale empty responses after running the pipeline:
```bash
docker compose exec redis redis-cli FLUSHALL
```

---

## 15. Model Performance

Trained on **6,574 labelled pairs** from 5,000 synthetic Karnataka businesses across 4 simulated department systems.

| Metric | Value |
|---|---|
| Validation AUC | **1.000** |
| Validation F1 | **0.9985** |
| Auto-link threshold | 0.95 |
| Review threshold | 0.75 |
| Training set size | 5,259 pairs |
| Validation set size | 1,315 pairs |
| Model version | 1.0.0 |

The model uses **SHAP TreeExplainer** (built once at startup) to generate feature-level explanations for every scored pair — the dominant latency driver when scoring 500k+ candidate pairs was previously rebuilding the explainer per pair.

---

## 16. Non-Negotiables Addressed

| Constraint | How Samvaya Handles It |
|---|---|
| Source systems cannot be modified | All ingestion is read-only simulation; connector interface is pluggable |
| No raw PII to hosted LLMs | `pii_scrambler.py` applies deterministic scrambling before any LLM call; `FORCE_LOCAL_ONLY=true` blocks all cloud LLM calls entirely |
| Every decision must be explainable | SHAP values per feature per pair; activity verdicts show contributing events and time windows |
| Every decision must be reversible | Reviewer can CONFIRM or REJECT any auto-link; decisions update the UBID assignment and are logged in the audit trail |
| Ambiguous matches must go to human review | Confidence 0.75–0.95 routes to `ReviewQueueView`; unmatched events surface in the review queue |

---

## 17. Future Scope

See [FUTURE_SCOPE.md](FUTURE_SCOPE.md) for the full roadmap. Key planned improvements:

- **Online model retraining** — Celery task fine-tunes LightGBM continuously on reviewer decisions
- **Active learning** — surface review pairs that maximise information gain per label
- **Graph-based clustering** — GraphSAGE / Node2Vec for transitive relationship capture
- **Temporal activity forecasting** — predict ACTIVE → DORMANT transitions 90 days ahead
- **Incremental blocking** — score only new-record candidate pairs without full pipeline rerun
- **RBAC** — Viewer / Reviewer / Supervisor / Admin / Data Steward roles
- **Public API v1** — rate-limited API for banks, insurance, industry associations
- **Kannada / Hindi NL queries** — multilingual interface for field officers
- **Mobile-responsive UI** — field inspector access on tablet
- **National registry integrations** — MCA21, GSTN, EPFO enrichment

---

## Team

Built for the **AI Bharat Hackathon 2025** — Karnataka Commerce & Industry, Theme 1.

---

*Platform handles Karnataka business data. All data in the prototype is synthetic and deterministically generated — no real business PII is present in this repository.*
