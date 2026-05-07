# UBID Platform — Prototype Build Guide
## Hackathon Working Prototype: Approach, Sequence & Technical Decisions

---

## Core Mental Model

> **Data Layer → ML/Logic Layer → Backend API Layer → Frontend Layer**

- Never build frontend before backend is stable
- Never build ML before data is clean and structured
- Each phase is the foundation for the next — do not skip or reorder

---

## Phase 1 — Synthetic Data Generation (Days 1–2)

- Generate **5,000 synthetic business entities** using Python (`faker` + custom Karnataka logic)
- Create records per entity across **4 departments**: Shop Establishment, Factories, Labour, KSPCB
- Inject intentional variations per record:
  - Name: abbreviations, legal suffix changes, Kannada/English transliteration differences
  - Address: same location written 3 different ways (BBMP ward / survey no / landmark)
  - PAN/GSTIN: present in only ~40% of records; occasionally mistyped
  - Intra-dept duplicates: ~8% of businesses appear twice in the same department
- Generate **12 months of activity events** per business: renewals, inspections, consumption readings, compliance filings
- Vary activity realistically: some businesses Active, some Dormant, a few Closed
- Store as CSV files or directly into PostgreSQL tables (one table per department)
- This dataset is your ground truth — you know exactly which records belong to the same entity

---

## Phase 2 — Database Setup (Days 2–3)

- Use **PostgreSQL** — ACID-compliant, JSONB support for evidence payloads, NIC-trusted
- Use **SQLAlchemy** as ORM; **Alembic** for schema migrations (version-controlled)

**Source DB** (simulates department systems):
- `dept_shop_establishment`, `dept_factories`, `dept_labour`, `dept_kspcb`
- `activity_events` table (simulated event stream; add `processed` boolean flag for polling)

**UBID Registry DB** (platform's own storage):
- `ubid_entities` — master UBID record per unique business
- `ubid_source_links` — maps each source record to a UBID (many-to-one)
- `ubid_link_evidence` — JSONB: feature vector, SHAP values, confidence score per linkage
- `review_tasks` — human review queue with full audit trail
- `activity_scores` — per-UBID classifications with evidence snapshots (JSONB)
- `unmatched_events` — events that could not be joined to any UBID

**For demo:** No need for Kafka. Poll `activity_events` table every few seconds using the `processed` flag — simulates a stream adequately.

---

## Phase 3 — Normalisation Engine (Days 3–4)

Pure Python module — no web framework yet. Build as separate files, each independently testable.

- **`name_normaliser.py`**
  - Strip legal suffixes (dict of 47 variants: Pvt Ltd, LLP, Proprietorship, etc.)
  - Expand abbreviations (180+ term dict: INDS→INDUSTRIES, MFG→MANUFACTURING)
  - Transliterate Kannada → Latin using `indic-transliteration` Python library
  - Generate phonetic keys using `soundex` and `doublemetaphone` libraries
  - Return: canonical name + soundex key + metaphone key

- **`address_parser.py`**
  - Regex patterns for Karnataka-specific address formats (BBMP ward, KIADB industrial area, rural survey numbers)
  - Extract components: building number, street, locality, pin code, industrial area name
  - Geocode via **self-hosted OSM Nominatim** (run in Docker)
  - Return: structured address dict + lat/lng + quality flag (HIGH / MEDIUM / LOW)

- **`identifier_validator.py`**
  - Validate PAN: 5 alpha + 4 numeric + 1 alpha
  - Validate GSTIN: 15 chars, state code must be 29 for Karnataka
  - Normalise to uppercase; strip spaces and dashes

- **`pii_scrambler.py`**
  - HMAC-SHA256 on business names → lookup in synthetic name dictionary (deterministic)
  - Structure-preserving encryption on PAN/GSTIN (keeps format valid)
  - Fixed date offset shift per dataset (preserves temporal ordering)
  - **Every record passes through this before any ML stage**

- **`standardiser.py`**
  - Orchestrator: calls all four modules in sequence
  - Input: raw dept record → Output: unified normalised record in internal schema

- Write **unit tests** for each module before moving on — most bugs hide here

---

## Phase 4 — Entity Resolution ML Pipeline (Days 4–6)

### 4a — Blocker (`blocker.py`)
- Generates candidate pairs using **6 independent blocking keys:**
  - PAN exact match
  - GSTIN prefix match
  - Pin code + Soundex of canonical name
  - Pin code + Double-Metaphone of canonical name
  - H3 geo-cell (resolution 7, ~1.2 km²) + most distinctive name token — use `h3` Python library
  - NIC industry code + pin + first name token
- Group records by each key; cross-product within each block = candidate pairs
- Deduplicate pairs across all blocking keys
- **Target: ≥99.5% blocking recall** — validate against labelled synthetic pairs

### 4b — Feature Extractor (`feature_extractor.py`)
Compute all 13 features per candidate pair:

| Feature | Method | Library |
|---|---|---|
| F01 — Name Jaro-Winkler | JW distance on canonical names | `rapidfuzz` |
| F02 — Name Token Set Ratio | token_set_ratio on canonical names | `rapidfuzz` |
| F03 — Abbreviation Match | Custom: checks if one name abbreviates the other | Custom |
| F04 — PAN Exact Match | −1 (both present, mismatch) / 0.5 (one missing) / 1.0 (match) | Custom |
| F05 — GSTIN Match | Same logic as PAN | Custom |
| F06 — Pin Code Match | Exact=1 / Adjacent=0.7 / Else=0 (use pin adjacency dict) | Custom |
| F07 — Geo Distance | Haversine metres; only when geocoding quality ≥ MEDIUM | `geopy` |
| F08 — Address Token Overlap | Jaccard similarity on parsed address tokens | Custom |
| F09 — Phone Match | Normalised exact/partial match | Custom |
| F10 — Industry Code Compat | NIC exact=1 / 2-digit=0.7 / 1-digit=0.4 / mismatch=0 | Custom |
| F11 — Owner Name | Jaro-Winkler on principal owner names (if present) | `rapidfuzz` |
| F12 — Same-Source Flag | 1 if both records from same department | Custom |
| F13 — Reg Date Proximity | Absolute year difference capped at 10 | Custom |

### 4c — Scoring Engine (`scorer.py`)

**Training:**
- Generate ~10,000 labelled pairs from synthetic ground truth (50% true matches, 50% non-matches)
- Train **LightGBM** classifier on feature vectors (`lightgbm` Python library)
- Apply **Platt Scaling** for calibration: `sklearn.calibration.CalibratedClassifierCV`
- Track experiment with **MLflow** (`mlflow ui` locally)

**Inference:**
- Feature vector → LightGBM → calibrated probability → confidence score
- Apply thresholds:
  - ≥ 0.95 → **Auto-Link** (committed automatically)
  - 0.75 – 0.94 → **Review Queue** (human reviewer)
  - < 0.75 → **Keep Separate** (unlinked)
- **PAN mismatch hard rule:** If both records have PAN and they differ → force Keep Separate regardless of model score

**Explainability (SHAP):**
- Use `shap.TreeExplainer(lgbm_model)` on every prediction
- Returns per-feature contribution values (e.g., name similarity +0.32, PAN match +0.41)
- Serialise SHAP values as JSONB → store in `ubid_link_evidence` table
- These values are shown to reviewers in the UI

### 4d — UBID Assigner (`ubid_assigner.py`)
- Use **Union-Find (Disjoint Set Union)** over all Auto-Link pairs → form entity clusters
  - Use `networkx` library or implement DSU directly (~20 lines)
- Each connected component = one unique business → assign one UBID
- UBID format: `KA-UBID-{6-char-base36}` (generate via `uuid` + base36 encoding)
- Anchor to PAN/GSTIN if present in any record in the cluster
- Write UBID + all source links + full evidence to PostgreSQL (append-only)

---

## Phase 5 — Activity Engine (Days 6–7)

Standalone Python module. Reads from `activity_events` table; writes to `activity_scores`.

- **`event_router.py`**
  - Poll unprocessed events from `activity_events` (check `processed = false`)
  - Look up source record ID in `ubid_source_links`
  - If found → attach UBID, write to `ubid_activity_log`
  - If not found → write to `unmatched_events` with triage reason code

- **`signal_scorer.py`**
  - Define signal weight + half-life constants in a config dict per event type
  - For each UBID, fetch all events in **12-month lookback window**
  - Apply decay formula: `score += weight × exp(−λ × days_since_event)` where `λ = ln(2) / half_life`
  - Normalise via sigmoid transform → Activity Score (AS) in [−1, +1]
  - Key weights: Electricity ≥50% baseline = +0.90, Licence renewal = +0.80, Closure = −1.00 (permanent)

- **`activity_classifier.py`**
  - AS > 0.4 → **Active**
  - −0.2 ≤ AS ≤ 0.4 → **Dormant**
  - AS < −0.2 → **Closed (Suspected)**
  - Hard closure event present → **Closed (Confirmed)** — overrides all positive signals
  - Build evidence snapshot: list of contributing events with individual weighted scores
  - Write classification + JSONB evidence to `activity_scores`

---

## Phase 6 — Backend API (Days 7–9)

Use **FastAPI** — async, auto-generates OpenAPI docs, minimal footprint.
Use **Pydantic** for request/response validation. Run with **Uvicorn**.

**Key API Routers:**

- **`/api/ubid/`**
  - `GET /lookup?pan=` or `?name=&pincode=` → returns UBID + linked source records
  - `GET /{ubid}` → full record: source links + activity status + evidence timeline

- **`/api/activity/`**
  - `GET /{ubid}/status` → current status + evidence
  - `GET /{ubid}/timeline` → all events chronologically
  - `GET /query?status=active&pincode=560058&sector=...&no_inspection_days=540` → **THE DEMO QUERY**

- **`/api/review/`**
  - `GET /queue` → paginated review tasks by priority
  - `GET /task/{task_id}` → full review card (both records + feature scores + SHAP values)
  - `POST /task/{task_id}/decision` → submit decision (CONFIRM_MATCH / NON_MATCH / PARTIAL / etc.)
  - `GET /stats` → auto-link rate, override rate, queue depth

- **`/api/admin/`**
  - `GET /audit-log` → full append-only decision trail (RTI-compatible)
  - `POST /thresholds` → update auto-link/review thresholds
  - `GET /model-stats` → model version, override rate, last retrain date

- Add **CORS middleware** so React frontend can call the API
- Run the full ML pipeline as a **one-shot pre-computation script** before demo — populate UBID registry in advance to avoid real-time latency during the live demo

---

## Phase 7 — Frontend (Days 9–12)

Use **React** + **Ant Design** component library (enterprise/government look out of the box).
Only start after backend endpoints are working and testable.

Build these 4 views in priority order:

- **View 1 — UBID Lookup (highest demo value)**
  - Search bar: accepts PAN, GSTIN, business name + pin code
  - Result card: UBID, anchor identifiers, all linked source records with confidence scores
  - Drill-down: feature scores as bar chart, SHAP waterfall chart

- **View 2 — Activity Dashboard (the "impossible query" centrepiece)**
  - Filter panel: status, pin code, NIC sector, days since last inspection
  - Results table: UBID, business name, status badge (🟢 Active / 🟡 Dormant / 🔴 Closed), last event
  - Row click → evidence timeline (all events, decayed weights, chronological)

- **View 3 — Reviewer Queue**
  - Task list with confidence score + reviewer assignment + status
  - Click task → side-by-side comparison card:
    - Left: Record A (raw + canonical fields)
    - Right: Record B (raw + canonical fields)
    - Middle: Feature score bars (F01–F13) colour-coded green/amber/red
    - Bottom: SHAP waterfall chart (use `recharts` or `victory`)
    - Decision buttons: CONFIRM MATCH / NON-MATCH / PARTIAL / REQUEST INFO / DEFER

- **View 4 — Analytics Dashboard (for C&I audience)**
  - Active business count by sector (bar chart via `recharts`)
  - Status distribution pie chart
  - Review queue health: queue depth, auto-link rate, override rate over time
  - Map view of business density by pin code (`react-leaflet`)

**SHAP waterfall options:**
- Option A: generate in Python using `shap` library, return as base64 image via API
- Option B: store SHAP values as JSONB, reconstruct waterfall chart in React using `recharts`

---

## Phase 8 — Connecting Everything (Days 12–13)

- Frontend calls FastAPI via `axios` — all requests to `http://localhost:8000`
- FastAPI uses SQLAlchemy sessions to read/write PostgreSQL
- ML pipeline scripts are either:
  - Called as FastAPI background tasks for real-time operations, or
  - Run as **scheduled Python scripts** that write pre-computed results to DB (preferred for demo stability)
- Run full pipeline as a **one-shot pre-computation** before demo to populate UBID registry

**Docker Compose (mandatory for demo reliability):**
```yaml
services:
  postgres: ...        # UBID registry + source DB
  nominatim: ...       # self-hosted geocoding
  mlflow: ...          # model tracking dashboard
  backend: ...         # FastAPI + Uvicorn
  frontend: ...        # React dev server or nginx
```
- One `docker compose up` brings the entire system live
- Ensures reproducible demo environment — no "works on my machine" failures

---

## How the ML Confidence Score Works End-to-End

- The model input is **not** raw business names — it is the **13-number feature vector**
- LightGBM learns which combination of features best predicts a true match
- Training uses synthetic labelled pairs (you know ground truth from generation)
- Platt Scaling corrects the raw probability to a properly calibrated confidence score (0.85 = 85% of such matches are truly correct in validation data)
- SHAP decomposes the score post-hoc into per-feature contributions visible to reviewers
- For Round 2: reviewer decisions (CONFIRM_MATCH / NON_MATCH) are added to training data → model retrained iteratively (active learning loop)

---

## Technology Stack Summary

| Component | Technology | Why |
|---|---|---|
| Language | Python 3.11 | All ML/data libs; FastAPI; fast prototyping |
| Database | PostgreSQL + SQLAlchemy + Alembic | ACID, JSONB, NIC-trusted, audit tables |
| String Matching | RapidFuzz | C-backed; fast Jaro-Winkler + token_set_ratio at scale |
| Geo Blocking | H3 Python library | Hex cell blocking; ~1.2 km² resolution |
| Geocoding | OSM Nominatim (Docker) | No external API; no PII leaves network |
| ML Model | LightGBM + scikit-learn calibration | Interpretable; CPU-efficient; handles missing features |
| Explainability | SHAP (TreeExplainer) | Exact for tree models; per-feature contribution |
| ML Tracking | MLflow (local) | Model versioning; experiment tracking; promotion workflow |
| Union-Find | networkx or custom DSU | Transitive closure for entity clustering |
| Backend API | FastAPI + Uvicorn | Async; auto OpenAPI docs; minimal footprint |
| Frontend | React + Ant Design | Enterprise UI; government-appropriate; component-rich |
| Charts | recharts | React-native charting; SHAP waterfall reconstruction |
| Maps | react-leaflet | Business density heatmap by pin code |
| HTTP Client | axios | Frontend → API calls |
| Containerisation | Docker + Docker Compose | One-command reproducible demo environment |

---

## Build Sequence Summary

```
Day 1–2:   Synthetic data generation (5,000 entities × 4 depts + 12mo events)
Day 2–3:   PostgreSQL schema setup (source DB + UBID registry DB)
Day 3–4:   Normalisation engine (name, address, PAN/GSTIN, scrambler)
Day 4–6:   Entity resolution pipeline (blocker → features → LightGBM → SHAP → UBID)
Day 6–7:   Activity engine (event router → signal scorer → classifier)
Day 7–9:   FastAPI backend (all 4 router groups; pre-computation script)
Day 9–12:  React frontend (4 views in priority order)
Day 12–13: Integration, Docker Compose, demo rehearsal, edge case testing
```

---

*UBID Platform — Hackathon Prototype Build Guide*