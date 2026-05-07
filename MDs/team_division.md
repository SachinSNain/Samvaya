# UBID Platform — Team Work Division (4 People)

> **Scope:** All phases **except** Phase 7 (React Frontend). Backend, ML pipeline, data, infra, and testing only.

---

## 🔴 Person 1 — Core Data & ML Engine (Most Critical)

**Why critical:** Everything else in the project depends on this working first. The database schema, the data pipeline, and the ML model must be ready before the API or any other component can function. A block here blocks everyone.

### Responsibilities

#### Phase 2 — Database Schema & Setup (Days 2–3)
- `src/database/models.py` — All 9 SQLAlchemy ORM table definitions (source tables, UBID registry, activity tables, review tasks)
- `src/database/connection.py` — SQLAlchemy engine + session factory + `get_db()` dependency
- `src/database/migrations/` — Alembic setup and initial migration (`alembic init`, `alembic revision --autogenerate`, `alembic upgrade head`)
- `.env` and `.env.example` files

#### Phase 4 — Entity Resolution ML Pipeline (Days 4–6)
- `src/entity_resolution/blocker.py` — All 6 blocking keys (PAN exact, GSTIN exact, Pin+Soundex, Pin+Metaphone, H3 geocell+token, NIC+Pin+token)
- `src/entity_resolution/feature_extractor.py` — All 13 features (F01–F13) with full implementation
- `src/entity_resolution/scorer.py` — LightGBM model training, Platt scaling calibration, SHAP value generation, thresholding logic (`AUTO_LINK` / `REVIEW` / `KEEP_SEPARATE`)
- `scripts/train_model.py` — Standalone model training script
- `src/entity_resolution/models/` — Save trained `lgbm_model.pkl` and `calibrated_model.pkl`

#### Tests (your own code)
- `tests/test_blocker.py` — Blocking recall ≥ 99.5%
- `tests/test_features.py` — All F01–F13 unit tests
- `tests/test_scorer.py` — Score routing logic

### Key Dependencies you produce
> The trained model `.pkl` files, the DB schema, and the `feature_extractor.py` are needed by everyone else.

---

## 🔴 Person 2 — Data Generation & Normalisation (Most Critical)

**Why critical:** The synthetic data is the raw fuel for the entire system. If data generation is broken or unrealistic, the ML model won't train, and the demo queries won't look impressive. Normalisation is what the blocker and feature extractor both depend on.

### Responsibilities

#### Phase 1 — Synthetic Data Generation (Days 1–2)
- `src/data_generation/entity_generator.py` — 5,000 ground truth entities with all fields (name, PAN, GSTIN, address, NIC code, lat/lng, status)
- `src/data_generation/department_record_generator.py` — 3–4 variants per entity across 4 departments (shop_establishment, factories, labour, kspcb)
- `src/data_generation/variation_injector.py` — Name typos, abbreviations, transliteration, PAN corruption logic, address format variants
- `src/data_generation/activity_event_generator.py` — 12-month event stream (electricity, inspections, renewals, closures) per entity with the correct pattern per status
- `src/data_generation/dictionaries/` — All 4 dictionary files (`karnataka_business_names.py`, `karnataka_street_names.py`, `nic_codes.py`, `pin_codes.py`)
- `scripts/generate_synthetic_data.py` — The one-shot script that runs all generators and outputs to `data/raw/`
- `data/ground_truth/labelled_pairs.csv` and `entity_clusters.csv` — Ground truth for ML training and evaluation

#### Phase 3 — Normalisation Engine (Days 3–4)
- `src/normalisation/name_normaliser.py` — Legal suffix stripping, abbreviation expansion, city normalisation, phonetic keys (Soundex + Double Metaphone), Kannada transliteration
- `src/normalisation/address_parser.py` — Karnataka-specific address type detection (BBMP, industrial, survey, landmark, minimal), ward/taluk extraction, pin code lookup
- `src/normalisation/identifier_validator.py` — PAN format validation, GSTIN validation + state code + embedded PAN extraction
- `src/normalisation/pii_scrambler.py` — Deterministic HMAC-based scrambling for names, PAN, GSTIN, phone, dates
- `src/normalisation/geocoder.py` — Nominatim API call + pin centroid fallback
- `src/normalisation/standardiser.py` — Orchestrator that runs all the above on a single record and returns a unified normalised dict

#### Tests (your own code)
- `tests/test_normalisation.py` — All name normaliser + PAN/GSTIN validation tests

### Key Dependencies you produce
> The generated CSVs in `data/raw/` and the `standardiser.py` output format are the input for Person 1's blocker and Person 3's activity engine.

---

## 🟡 Person 3 — Activity Intelligence Engine & UBID Assignment (Important, Parallel)

**Why important (not critical):** This work is substantial and complex, but it can be developed somewhat in parallel once the DB schema from Person 1 is ready. It does not block Person 1 or 2.

### Responsibilities

#### Phase 4 (partial) — UBID Assigner (Day 5–6)
- `src/entity_resolution/ubid_assigner.py` — Union-Find data structure, `mint_ubid()` UBID generation (`KA-UBID-XXXXXX`), cluster-to-UBID mapping, PAN/GSTIN anchor selection, DB persistence of `ubid_entities` and `ubid_source_links`

#### Phase 5 — Activity Intelligence Engine (Days 6–7)
- `src/activity_engine/signal_config.py` — All signal weights, half-lives, permanent signal definitions, `compute_decay()` formula, seasonal NIC code config
- `src/activity_engine/signal_scorer.py` — `compute_activity_score()`: decay-weighted sum, sigmoid normalisation, ACTIVE/DORMANT/CLOSED_SUSPECTED classification, evidence list with per-signal breakdown
- `src/activity_engine/event_router.py` — Route raw activity events to their UBID via source link lookup; write to `ubid_activity_events`; route unmatched events to `unmatched_events` table
- `src/activity_engine/activity_classifier.py` — Bulk run activity scoring for all UBIDs; update `activity_scores` table; mark `is_current = True`

#### Scripts
- The activity-scoring portions of `scripts/run_pipeline.py` (Steps 8 and 9) — `route_all_events()` and `compute_all_activity_scores()`

#### Tests (your own code)
- `tests/test_activity_engine.py` — Signal scoring unit tests (decay formula, permanent signal override, ACTIVE/DORMANT threshold boundary cases)

### Key Dependencies you need
> You need Person 1's `database/models.py` (especially `UBIDActivityEvent`, `ActivityScore`, `UnmatchedEvent`) and Person 2's generated `activity_events.csv` to test realistically.

### Key Dependencies you produce
> `activity_scores` table populated in DB; `event_router.py` needed by Person 4's API endpoints.

---

## 🟡 Person 4 — FastAPI Backend, Docker & Scripts (Important, Parallel)

**Why important (not critical):** The API is a relatively independent layer that sits on top of the DB and ML pipeline. It can be scaffolded and tested with mocked data while others build the core logic. Docker and scripts can be written independently.

### Responsibilities

#### Phase 6 — FastAPI Backend (Days 7–9)
- `src/api/main.py` — FastAPI app creation, CORS middleware, router registration, `/health` endpoint
- `src/api/dependencies.py` — `get_db()` DB session injection, auth stubs
- `src/api/schemas/` — All 4 Pydantic schema files (`ubid_schemas.py`, `activity_schemas.py`, `review_schemas.py`, `admin_schemas.py`) — request/response models for all endpoints
- `src/api/routers/ubid.py` — `GET /api/ubid/lookup` (by PAN/GSTIN/name+pin), `GET /api/ubid/{ubid}` (full detail with source links and evidence)
- `src/api/routers/activity.py` — **THE DEMO QUERY** `GET /api/activity/query` (filter by status, pincode, no_inspection_days), `GET /api/activity/{ubid}/timeline`
- `src/api/routers/review.py` — `GET /api/review/queue`, `GET /api/review/task/{task_id}`, `POST /api/review/task/{task_id}/decision`, `GET /api/review/stats`
- `src/api/routers/admin.py` — `GET /api/admin/audit-log`, `GET /api/admin/model-stats`, `POST /api/admin/thresholds`

#### Phase 8 — Docker Compose & Integration (Days 12–13)
- `docker-compose.yml` — All 5 services (postgres, nominatim, mlflow, backend, frontend) with healthchecks and volumes
- `Dockerfile.backend` — Python 3.11, pip install, alembic upgrade, uvicorn
- `Dockerfile.frontend` — Node 18, npm install, npm start
- Root project files: `README.md`, `.gitignore`, project folder structure setup

#### Phase 9 — Demo Preparation Scripts (Day 13)
- `scripts/run_pipeline.py` — Full 9-step orchestration script (Steps 1–7: load source records, normalise, block, feature extract, score, assign UBIDs, persist registry, create review tasks)
- `scripts/reset_demo.py` — TRUNCATE all UBID registry tables for a clean demo start
- `scripts/validate_metrics.py` — Check all 7 success metrics and print pass/fail

#### Tests (your own code)
- `tests/test_api.py` — FastAPI route testing with `httpx` and `pytest-asyncio`

### Key Dependencies you need
> You need Person 1's `models.py` and `connection.py` (to write routers that actually query the DB), and Person 3's `event_router.py` to call in `run_pipeline.py`.

---

## 📋 Summary Table

| | Person 1 | Person 2 | Person 3 | Person 4 |
|---|---|---|---|---|
| **Focus** | DB + ML Model | Data Gen + Normalisation | Activity Engine + UBID | API + Docker + Scripts |
| **Criticality** | 🔴 Critical | 🔴 Critical | 🟡 Important | 🟡 Important |
| **Phase** | Phase 2 + Phase 4 | Phase 1 + Phase 3 | Phase 4 (partial) + Phase 5 | Phase 6 + Phase 8 + Phase 9 |
| **Blocks who?** | Everyone | Person 1 + Person 3 | Person 4 (activity API) | No one |
| **Primary language** | Python | Python | Python | Python |
| **Key output** | `models.py`, trained `.pkl` | CSVs + `standardiser.py` | `activity_scores` table | Running API + Docker stack |

---

## 🚦 Recommended Build Order

```
Day 1–2:  Person 2 → Generate entities + dept records + activity events
Day 2–3:  Person 1 → DB schema + Alembic migrations (can start immediately)
Day 3–4:  Person 2 → Normalisation engine
Day 4–5:  Person 1 → Blocker + Feature extractor + Model training
Day 5–6:  Person 3 → UBID assigner + Activity engine (DB schema ready by now)
Day 7–8:  Person 4 → API endpoints (DB + ML ready)
Day 12:   Person 4 → Docker compose + Integration
Day 13:   All → Run pipeline, fix metrics, demo rehearsal
```

> **Critical path:** Person 2 → Person 1 → Person 3 → Person 4
