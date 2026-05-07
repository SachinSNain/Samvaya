# UBID Platform — Implementation Plan
### Samvaya Hackathon | Core Infrastructure & Platform Build

> [!NOTE]
> LLM and AI integration details have been moved to [`llm_ai_implementation.md`](llm_ai_implementation.md). This file covers data pipeline, database, frontend, and environment setup only.

---

## Current Codebase Audit

### ✅ Already Exists
| Module | Files | Status |
|---|---|---|
| `src/normalisation/` | address_parser, geocoder, identifier_validator, name_normaliser, pii_scrambler, standardiser | ✅ Complete |
| `src/entity_resolution/` | blocker, feature_extractor (F01–F13), scorer, ubid_assigner | ✅ Complete |
| `src/activity_engine/` | signal_config, signal_scorer, event_router, activity_classifier | ✅ Complete |
| `src/database/` | models.py, connection.py | ✅ Complete |
| `src/api/routers/` | ubid.py, activity.py, review.py, admin.py | ✅ Complete |
| `src/data_generation/` | entity_generator, department_record_generator, variation_injector, activity_event_generator | ✅ Complete |
| `scripts/` | generate_synthetic_data, run_pipeline, train_model, reset_demo | ✅ Complete |
| `frontend/src/` views | LookupView, ActivityView, ReviewQueueView, AnalyticsView | ✅ Partial |

### ❌ Missing (Must Build)
| Missing | Priority |
|---|---|
| `data/raw/*.csv` | 🔴 Critical — data dirs are empty, nothing can be tested |
| Trained model `.pkl` files | 🔴 Critical — pipeline cannot score pairs |
| `reviewer_summary` + `reviewer_notes` columns in ReviewTask | 🔴 High — needed for LLM integration |
| 4 empty frontend pages (LookupPage, ActivityPage, ReviewPage, DashboardPage) | 🔴 High — demo face |
| `scripts/pregenerate_summaries.py` | 🟡 High — see `llm_ai_implementation.md` |
| `src/llm_router.py` | 🔴 Critical — see `llm_ai_implementation.md` |
| F14 semantic embedding feature | 🟢 Optional — see `llm_ai_implementation.md` |
| `POST /api/nl-query` endpoint | 🟢 Stretch — see `llm_ai_implementation.md` |

---

## Phase 0 — Data Pipeline (Run First — Unblocks Everything)

> [!CAUTION]
> No code can be tested until this is done. The `data/raw/` directory is currently empty. Execute in this exact order:

```bash
# Step 1 — Generate synthetic data (~5 min)
# Creates: data/raw/shop_establishment.csv, factories.csv, labour.csv, kspcb.csv, activity_events.csv
python scripts/generate_synthetic_data.py

# Step 2 — Create database schema
alembic upgrade head

# Step 3 — Train the LightGBM entity resolution model (~3 min)
# Creates: src/entity_resolution/models/calibrated_model.pkl + lgbm_model.pkl
python scripts/train_model.py

# Step 4 — Run the full pipeline (~15 min)
# Normalise → Block → Score → Assign UBIDs → Route Activity Events
python scripts/run_pipeline.py
```

**Expected output after Phase 0:**
- `data/raw/*.csv` — 5 CSV files with ~15,000–20,000 department records + ~120,000 events
- `src/entity_resolution/models/calibrated_model.pkl` exists and is loadable
- `ubid_entities` table has ~4,000–5,000 rows
- `review_tasks` table has PENDING tasks (REVIEW-bucket pairs)
- `activity_scores` table populated for all UBIDs
- `ubid_activity_events` table has routed events

---

## Phase 1 — Database Schema Update

**File:** `src/database/models.py`

Add two columns to the `ReviewTask` class. These columns are required for the LLM integration (see `llm_ai_implementation.md`):

```python
class ReviewTask(Base):
    # ... existing columns ...

    # NEW — LLM AI columns
    reviewer_summary = Column(Text)
    # ^ Pre-generated via Gemini 2.5 Flash (scrambled inputs — API lane safe)
    # ^ Populated by scripts/pregenerate_summaries.py the night before demo

    reviewer_notes = Column(Text)
    # ^ Generated on-demand via Llama 3.1 8B (raw canonical fields — LOCAL lane only)
    # ^ Populated by scorer.py when decision == "REVIEW"
```

**After editing models.py, run:**
```bash
alembic revision --autogenerate -m "add_reviewer_ai_columns"
alembic upgrade head
```

**Verify migration:**
```bash
# Check the new columns exist
python -c "from src.database.models import ReviewTask; print([c.name for c in ReviewTask.__table__.columns])"
```

---

## Phase 2 — Frontend Page Completion

All 4 page files are currently **0 bytes**. The corresponding View components already exist and just need to be imported.

### `frontend/src/pages/LookupPage.tsx`
```tsx
import React from 'react';
import LookupView from './LookupView';

export default function LookupPage() {
  return <LookupView />;
}
```
> After LLM integration: add `ai_explanation` callout box below the UBID detail card (see `llm_ai_implementation.md` Step 6).

---

### `frontend/src/pages/ActivityPage.tsx`
```tsx
import React from 'react';
import ActivityView from './ActivityView';

export default function ActivityPage() {
  return <ActivityView />;
}
```
> After LLM integration: add `activity_narrative` "Business Health Narrative" panel on UBID detail (see `llm_ai_implementation.md` Step 7).

---

### `frontend/src/pages/ReviewPage.tsx`
```tsx
import React from 'react';
import ReviewQueueView from './ReviewQueueView';

export default function ReviewPage() {
  return <ReviewQueueView />;
}
```
> After LLM integration: add `ai_teaser` (first sentence of `reviewer_summary`) on each queue card (see `llm_ai_implementation.md` Step 6).

---

### `frontend/src/pages/DashboardPage.tsx`
```tsx
import React from 'react';
import AnalyticsView from './AnalyticsView';

export default function DashboardPage() {
  return <AnalyticsView />;
}
```
> After LLM integration: add `ai_insights` anomaly callout from `/review/stats` (see `llm_ai_implementation.md` Step 6).

---

## Phase 3 — Environment & Docker Updates

### `.env.example` — Add LLM keys
```env
# ── Existing ──────────────────────────────────────
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ubid_platform
POSTGRES_USER=ubid_user
POSTGRES_PASSWORD=your_password_here
SCRAMBLER_SECRET_KEY=dev_secret_key_replace_in_prod
NOMINATIM_URL=http://localhost:8080
MLFLOW_TRACKING_URI=http://localhost:5000
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
DEMO_MODE=true

# ── NEW — LLM Integration ──────────────────────────
GEMINI_API_KEY=your_google_ai_studio_key_here
GROQ_API_KEY=your_groq_api_key_here
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
FORCE_LOCAL_ONLY=false
# ^ Set to "true" for the demo air-gap kill switch moment
```

### `requirements.txt` — Add LLM packages
```
# ── NEW — LLM Integration ──────────────────────
google-generativeai>=0.8.0
groq>=0.9.0
httpx>=0.25.2
sentence-transformers>=2.7.0
```

### `docker-compose.yml` — Backend service env section
Add to the `backend` service `environment:` block:
```yaml
- GEMINI_API_KEY=${GEMINI_API_KEY}
- GROQ_API_KEY=${GROQ_API_KEY}
- OLLAMA_BASE_URL=http://host.docker.internal:11434
- OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.1:8b}
- FORCE_LOCAL_ONLY=${FORCE_LOCAL_ONLY:-false}
```

---

## Full Sprint Order

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 0  [NOW — ~40 min total]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✦ python scripts/generate_synthetic_data.py
  ✦ alembic upgrade head
  ✦ python scripts/train_model.py
  ✦ python scripts/run_pipeline.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOUR 1  [Platform Core — this file]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✦ Add reviewer_summary + reviewer_notes to ReviewTask model
  ✦ Run Alembic migration
  ✦ Wire up 4 empty frontend pages
  ✦ Update .env.example + requirements.txt + docker-compose.yml

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOUR 1–2  [LLM Core — see llm_ai_implementation.md]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✦ Create src/llm_router.py (Steps 1)
  ✦ Hook scorer.py → reviewer_explanation (Step 3)
  ✦ Hook review.py → ai_explanation in response (Step 6)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOUR 3  [LLM Hooks — see llm_ai_implementation.md]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✦ Hook address_parser.py (Step 2)
  ✦ Create scripts/pregenerate_summaries.py (Step 8)
  ✦ Hook activity_classifier.py (Step 5)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOUR 4–5  [Optional — see llm_ai_implementation.md]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✦ F14 embedding feature + retrain model (Step 9)
  ✦ signal_scorer.py EVENT_CLASSIFIER hook (Step 4)
  ✦ POST /api/nl-query endpoint (Step 10)
```

---

## Pre-Demo Checklist (Night Before)

### Data & Model
- [ ] `data/raw/shop_establishment.csv` exists (>10,000 rows)
- [ ] `data/raw/factories.csv`, `labour.csv`, `kspcb.csv`, `activity_events.csv` exist
- [ ] `src/entity_resolution/models/calibrated_model.pkl` exists
- [ ] `ubid_entities` table has >4,000 records
- [ ] `review_tasks` table has >50 PENDING tasks

### Ollama (Local LLM)
- [ ] `ollama pull llama3.1:8b` — 4.7GB model downloaded
- [ ] `ollama ps` — shows `llama3.1:8b` loaded and warm (not just downloaded)
- [ ] `ollama run llama3.1:8b "ping"` — responds within 2 seconds

### LLM Pre-generation
- [ ] `GEMINI_API_KEY` set in `.env`
- [ ] `python scripts/pregenerate_summaries.py` — completed successfully
- [ ] `review_tasks.reviewer_summary` column populated for all PENDING tasks

### Demo Reset
- [ ] `python scripts/reset_demo.py` — run **after** pre-generation (wipes UBID registry, keeps summaries)

### Frontend & API
- [ ] `npm start` runs cleanly at `http://localhost:3000`
- [ ] All 4 pages load without blank screen
- [ ] `curl http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] Demo query works: `GET /api/activity/query?status=ACTIVE&pincode=560058&no_inspection_days=540`
- [ ] Review queue loads: `GET /api/review/queue` returns tasks with `ai_teaser`
- [ ] Review task detail: `GET /api/review/task/{id}` includes `ai_explanation`

### Air-Gap Test
- [ ] Set `FORCE_LOCAL_ONLY=true` in `.env`
- [ ] Disconnect Wi-Fi
- [ ] Open reviewer card → AI explanation still loads (via Ollama)
- [ ] Reconnect Wi-Fi, set `FORCE_LOCAL_ONLY=false`

---

## Demo Day — "Privacy Kill Switch" Sequence

> [!IMPORTANT]
> Practice this sequence before the presentation. This is the highest-scoring demo moment.

**Step 1:** *"We'll now demonstrate that our most sensitive AI operations are completely air-gapped from the internet."*

**Step 2:** Toggle airplane mode — **visible to judges**.

**Step 3:** Open Review Queue in the frontend. Pick an ambiguous pair. Click it.

**Step 4:** Reviewer card loads with AI-generated side-by-side explanation — generated **locally by Llama 3.1 8B on the RTX 4050** in under 2 seconds.

**Step 5:** Submit a CONFIRM_MATCH decision. The queue depth counter decrements.

**Step 6:** *"The entire reviewer workflow — including AI explanations — just ran with zero internet. This is the architecture Karnataka's government network requires."*

**Step 7:** Reconnect Wi-Fi. Navigate to Analytics Dashboard.

**Step 8:** *"For non-PII aggregate analytics, we leverage Gemini 2.5 Flash — but only for data that has no individual identifiers."*

---

*This plan covers: data pipeline, DB schema, frontend wiring, environment setup, and demo preparation.*
*For all LLM and AI integration code, see: `llm_ai_implementation.md`*
*Hardware target: Intel i7-13th Gen + NVIDIA RTX 4050 6GB VRAM*
