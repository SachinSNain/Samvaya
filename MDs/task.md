# UBID Platform — Task Tracker

## ✅ Implemented (Completed)

### STEP 1 — Foundation
- [x] `src/database/connection.py` — SQLAlchemy engine and session factory
- [x] `src/database/models.py` — All 12 PostgreSQL table schemas
- [x] `src/database/__init__.py`

### STEP 2 — Data Generation
- [x] `src/data_generation/` — Entity, department, and event generators
- [x] `scripts/generate_synthetic_data.py` — Pipeline script
- [x] Successfully generated 1,230 department records & 8,340 activity events.

### STEP 3 — Normalisation Engine
- [x] `src/normalisation/name_normaliser.py` — Suffixes, abbreviations, phonetics
- [x] `src/normalisation/address_parser.py` — BBMP, Industrial, Survey, Landmark parsing
- [x] `src/normalisation/identifier_validator.py` — PAN / GSTIN regex validation
- [x] `src/normalisation/pii_scrambler.py` — HMAC-SHA256 deterministic scrambling
- [x] `src/normalisation/geocoder.py` — Nominatim integration
- [x] `src/normalisation/standardiser.py` — Orchestrator
- [x] `tests/test_normalisation.py` — 31/31 unit tests passing

### STEP 4 — Entity Resolution ML Pipeline
- [x] Create `src/entity_resolution/blocker.py` (O(n) blocking keys)
- [x] Create `src/entity_resolution/feature_extractor.py` (F01-F13 calculation)
- [x] Create `src/entity_resolution/scorer.py` (LightGBM with Platt Scaling and SHAP)
- [x] Create `src/entity_resolution/ubid_assigner.py` (Union-Find clustering)
- [x] Run `scripts/train_model.py` to train and save ML artifacts

### STEP 5 — Activity Intelligence Engine
- [x] Create `src/activity_engine/signal_config.py`
- [x] Create `src/activity_engine/signal_scorer.py`
- [x] Create `src/activity_engine/event_router.py`
- [x] Create `src/activity_engine/activity_classifier.py`

### STEP 6 — FastAPI Backend
- [x] Set up `src/api/main.py`
- [x] Create UBID detail endpoints (`src/api/routers/ubid.py`)
- [x] Create Activity Query endpoints (`src/api/routers/activity.py`)
- [x] Create Reviewer Queue endpoints (`src/api/routers/review.py`)
- [x] Create Admin endpoints (`src/api/routers/admin.py`) — Audit logs & thresholds

### STEP 7 — Scripts & Integration
- [x] `scripts/run_pipeline.py` — End-to-end demo script
- [x] `scripts/reset_demo.py` — DB truncation for demo rehearsal
- [x] Docker compose validation

---

## ⏳ To Be Implemented (Pending)

### STEP 8 — Infrastructure & Docker
- [x] `docker-compose.yml` — Services: postgres, nominatim, mlflow, backend, frontend
- [x] `Dockerfile` for FastAPI backend (uvicorn, port 8000)
- [x] `Dockerfile` for React frontend (nginx or dev server)
- [x] `.env.example` with all required environment variables documented
- [ ] Verify `docker compose up` brings the full system live in one command
- [ ] Run `scripts/run_pipeline.py` inside Docker to pre-populate UBID registry before demo
- [x] Database migrations via Alembic (`alembic upgrade head`)

### STEP 9 — React Frontend (4 Views in Priority Order)

#### View 1 — UBID Directory & Lookup (Highest Demo Value)
- [x] Backend `GET /api/ubid/list` endpoint
- [x] Data Table: lists all companies and their UBIDs
- [x] Search & Filters: search by company name, PAN, or GSTIN
- [x] Result modal/drawer: UBID, anchor identifiers, linked source records with confidence scores
- [x] Drill-down: F01–F13 feature scores as bar chart
- [x] SHAP waterfall chart (reconstruct from JSONB values using `recharts`)

#### View 2 — Activity Dashboard (The "Impossible Query" Centrepiece)
- [x] Filter panel: status dropdown, pin code input, NIC sector, days-since-inspection slider
- [x] Results table: UBID, business name, status badge (🟢 Active / 🟡 Dormant / 🔴 Closed), last event
- [x] Row click → evidence timeline (all events, decayed weights, chronological)
- [x] Wire to `GET /api/activity/query` demo endpoint

#### View 3 — Reviewer Queue
- [x] Task list with confidence score, status badge, and queue depth counter
- [x] Side-by-side comparison card: Record A vs Record B (raw + canonical fields)
- [x] F01–F13 feature score bars colour-coded (green / amber / red)
- [x] Decision buttons: CONFIRM MATCH / NON-MATCH / PARTIAL / REQUEST INFO / DEFER
- [x] Wire to `GET /api/review/queue`, `GET /api/review/task/{id}`, `POST /api/review/task/{id}/decision`

#### View 4 — Analytics Dashboard
- [x] Active business count by NIC sector (bar chart via `recharts`)
- [x] Status distribution pie chart (Active / Dormant / Closed)
- [x] Review queue health panel: queue depth, auto-link rate, override rate
- [x] Map view of business density by pin code (`react-leaflet`)
- [x] Wire to `GET /api/admin/model-stats` and `GET /api/review/stats`

### STEP 10 — Integration & Demo Rehearsal
- [ ] Connect React frontend to FastAPI via `axios` (`http://localhost:8000`)
- [ ] End-to-end smoke test: generate data → run pipeline → verify lookup & activity query in UI
- [ ] Test reviewer workflow: pick a REVIEW-bucket pair, submit a decision, verify DB update
- [ ] Validate the demo query: `?status=ACTIVE&pincode=560058&no_inspection_days=540`
- [ ] Edge case tests: missing PAN, intra-department duplicates, unmatched events
- [ ] Run `scripts/reset_demo.py` + `scripts/run_pipeline.py` together as a clean rehearsal loop

### STEP 11 — Testing & Quality
- [x] Write `tests/test_blocker.py` — Validate ≥99.5% blocking recall on synthetic pairs.
- [x] Write `tests/test_feature_extractor.py` — Spot-check F01-F13 calculations.
- [x] Write `tests/test_scorer.py` — Verify PAN hard rule forces score to 0.0 on mismatch.
- [x] Write `tests/test_activity_scorer.py` — Verify permanent signals (e.g. CLOSURE) override positive events.
- [x] Run `pytest tests/ -v` and document coverage.
