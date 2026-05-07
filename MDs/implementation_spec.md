# UBID Platform — Technical Specification for Pending Implementation

> **Purpose:** This file is a precise technical spec. Another developer or AI model can use this to write the exact code for each pending file without reading the full plan. All parameters, thresholds, algorithms, and schemas are specified here.

---

## FILE: `src/entity_resolution/blocker.py`

**Goal:** Reduce O(n²) comparisons to a manageable candidate set. Must achieve ≥99.5% recall on true match pairs.

### Function Signature
```python
def generate_candidate_pairs(normalised_records: List[dict]) -> List[Tuple[str, str]]
```

### Input Record Fields Required
Each record dict must have: `record_id`, `source_system`, `canonical_name`, `soundex`, `metaphone` (tuple), `pin_code`, `pan`, `gstin`, `lat`, `lng`, `geocode_quality`, `nic_code`

### 6 Blocking Keys — All Must Be Implemented

| Key | Index Structure | Condition to Index |
|---|---|---|
| Key 1: PAN Exact | `pan_index[pan].append(record_id)` | `rec["pan"]` is not None |
| Key 2: GSTIN Exact | `gstin_index[gstin].append(record_id)` | `rec["gstin"]` is not None |
| Key 3: Pin + Soundex | `pin_soundex_index[f"{pin}_{soundex}"].append(record_id)` | both present |
| Key 4: Pin + Metaphone | `pin_meta_index[f"{pin}_{metaphone[0]}"].append(record_id)` | both present, use `metaphone[0]` only |
| Key 5: H3 Geocell + First name token | `h3_cell = h3.geo_to_h3(lat, lng, resolution=7)`, key = `f"{h3_cell}_{name_tokens[0]}"` | geocode_quality in ("HIGH","MEDIUM") |
| Key 6: NIC 2-digit + Pin + First name token | key = `f"{nic_2digit}_{pin}_{name_tokens[0]}"` | all three present |

### Pair Generation Logic
```python
# For each index, for every key with >1 record:
for i in range(len(record_ids)):
    for j in range(i+1, len(record_ids)):
        pair = (min(a, b), max(a, b))  # canonical ordering
        pairs.add(pair)  # use a Set to deduplicate
return list(pairs)
```

### Import
```python
import h3
from collections import defaultdict
from typing import List, Tuple, Set
```

---

## FILE: `src/entity_resolution/feature_extractor.py`

**Goal:** Compute a 13-feature vector for every candidate pair.

### Function Signatures
```python
def extract_features(rec_a: dict, rec_b: dict) -> dict  # returns {F01..F13}
def _identifier_match_score(id_a, id_b) -> float
def _abbreviation_match_score(name_a: str, name_b: str) -> float
```

### All 13 Features — Exact Specification

| Feature | Computation | None Condition |
|---|---|---|
| **F01** | `fuzz.jaro_winkler_similarity(canonical_a, canonical_b) / 100.0` | Either name empty |
| **F02** | `fuzz.token_set_ratio(canonical_a, canonical_b) / 100.0` | Either name empty |
| **F03** | `_abbreviation_match_score(canonical_a, canonical_b)` | Returns 0.0 not None |
| **F04** | `_identifier_match_score(rec_a["pan"], rec_b["pan"])` | Returns 0.0 not None |
| **F05** | `_identifier_match_score(rec_a["gstin"], rec_b["gstin"])` | Returns 0.0 not None |
| **F06** | `1.0` if same pin, `0.7` if adjacent (use `PIN_ADJACENCY`), `0.0` otherwise | Either pin None |
| **F07** | `geodesic((lat_a, lng_a), (lat_b, lng_b)).meters` | Either quality not in ("HIGH","MEDIUM") |
| **F08** | `len(tokens_a & tokens_b) / len(tokens_a | tokens_b)` Jaccard | Either token set empty |
| **F09** | Compare last 10 digits of phone. `1.0`=exact, `0.5`=last 7 match, `0.0`=no match | Either phone empty |
| **F10** | NIC: `1.0`=exact, `0.7`=same 2-digit, `0.4`=same 1-digit, `0.0`=different | Either NIC empty |
| **F11** | `fuzz.jaro_winkler_similarity(owner_a.upper(), owner_b.upper()) / 100.0` | Either owner empty |
| **F12** | `1.0` if `rec_a["source_system"] == rec_b["source_system"]` else `0.0` | Never None |
| **F13** | `min(abs(year_a - year_b), 10)` (year difference, capped at 10) | Either year None |

### `_identifier_match_score` Exact Logic
```
Both present, match    → +1.0
Both present, mismatch → -1.0   ← STRONG NEGATIVE (hard rule in scorer)
One absent             → +0.5   (cannot determine)
Both absent            → 0.0
```

### `_abbreviation_match_score` Logic
- If `len(name_a) <= 6` and `len(words_b) >= 2`: check if name_a == first-letters of words_b → `1.0`, partial → `0.5`
- Check vice versa
- Otherwise return `0.0`

### Imports Needed
```python
from rapidfuzz import fuzz
from geopy.distance import geodesic
from src.normalisation.address_parser import PIN_ADJACENCY
```

---

## FILE: `src/entity_resolution/scorer.py`

**Goal:** Load trained LightGBM model, score pairs, apply PAN hard rule, route to AUTO_LINK/REVIEW/KEEP_SEPARATE, compute SHAP values.

### Constants
```python
FEATURE_ORDER = ["F01","F02","F03","F04","F05","F06","F07","F08","F09","F10","F11","F12","F13"]
THRESHOLD_AUTO_LINK = float(os.getenv("THRESHOLD_AUTO_LINK", "0.95"))
THRESHOLD_REVIEW    = float(os.getenv("THRESHOLD_REVIEW",    "0.75"))
MODEL_DIR = "src/entity_resolution/models"
```

### LightGBM Training Parameters — Exact Values
```python
lgbm_params = {
    "objective":        "binary",
    "metric":           "binary_logloss",
    "num_leaves":       31,
    "learning_rate":    0.05,
    "feature_fraction": 0.9,
    "min_data_in_leaf": 20,
    "n_estimators":     300,
    "verbose":          -1,
    "random_state":     42
}
```

### Calibration
```python
# Platt Scaling via sklearn
from sklearn.calibration import CalibratedClassifierCV
calibrated_model = CalibratedClassifierCV(base_lgbm, method="sigmoid", cv=5)
calibrated_model.fit(X_train, y_train)
```

### Train/Val Split
```python
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
```

### Feature Array Conversion
```python
def features_to_array(feature_dict: dict) -> np.ndarray:
    # None values → np.nan
    return np.array([feature_dict.get(f, np.nan) if feature_dict.get(f) is not None else np.nan
                     for f in FEATURE_ORDER], dtype=np.float32)
```

### Scoring Logic (exact)
```python
def score_pair(feature_dict, calibrated_model, lgbm_model) -> dict:
    arr = features_to_array(feature_dict).reshape(1, -1)
    calibrated_score = float(calibrated_model.predict_proba(arr)[0][1])

    pan_hard_rule = False
    if feature_dict.get("F04") == -1.0:   # PAN mismatch → force non-match
        calibrated_score = 0.0
        pan_hard_rule = True

    if calibrated_score >= THRESHOLD_AUTO_LINK:
        decision = "AUTO_LINK"
    elif calibrated_score >= THRESHOLD_REVIEW:
        decision = "REVIEW"
    else:
        decision = "KEEP_SEPARATE"

    # SHAP — use underlying lgbm_model, NOT calibrated_model
    explainer = shap.TreeExplainer(lgbm_model)
    shap_values = explainer.shap_values(arr)
    # shap_values is list of 2 arrays for binary; take index 1 (positive class)
    shap_for_match = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]
    shap_dict = {feat: round(float(shap_for_match[i]), 4) for i, feat in enumerate(FEATURE_ORDER)}

    return {"calibrated_score": calibrated_score, "decision": decision,
            "shap_values": shap_dict, "pan_hard_rule_applied": pan_hard_rule}
```

### Model Save/Load Paths
```
src/entity_resolution/models/calibrated_model.pkl   ← Used for scoring
src/entity_resolution/models/lgbm_model.pkl         ← Used for SHAP only
```

### MLflow Logging (in train_model)
```python
import mlflow
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
with mlflow.start_run():
    mlflow.log_params(lgbm_params)
    mlflow.log_metric("val_auc", auc)
    mlflow.log_metric("val_f1", f1)
    mlflow.sklearn.log_model(calibrated_model, "calibrated_model")
```

---

## FILE: `src/entity_resolution/ubid_assigner.py`

**Goal:** Run Union-Find over AUTO_LINK pairs, mint UBIDs, find PAN/GSTIN anchors.

### UBID Format
```
KA-UBID-XXXXXX  where XXXXXX is base-36 (digits + uppercase letters)
```

### Base-36 Conversion
```python
BASE36_CHARS = string.digits + string.ascii_uppercase  # "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def to_base36(num: int, length: int = 6) -> str:
    result = []
    while num > 0:
        result.append(BASE36_CHARS[num % 36])
        num //= 36
    while len(result) < length:
        result.append('0')
    return ''.join(reversed(result))

def mint_ubid() -> str:
    uid = uuid.uuid4().int % (36 ** 6)
    return f"KA-UBID-{to_base36(uid)}"
```

### UnionFind Class — With Path Compression + Union by Rank
```python
class UnionFind:
    def __init__(self): self.parent = {}; self.rank = {}
    def find(self, x):
        if x not in self.parent: self.parent[x] = x; self.rank[x] = 0
        if self.parent[x] != x: self.parent[x] = self.find(self.parent[x])  # path compression
        return self.parent[x]
    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py: return
        if self.rank[px] < self.rank[py]: px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]: self.rank[px] += 1
    def get_clusters(self) -> dict:
        clusters = defaultdict(list)
        for node in self.parent: clusters[self.find(node)].append(node)
        return dict(clusters)
```

### Main Function Signature
```python
def assign_ubids(auto_link_pairs: List[Tuple[str,str]], all_records: List[dict]) -> Tuple[dict, dict]:
    # Returns: (record_to_ubid, ubid_to_anchor)
    # record_to_ubid: {record_id: ubid}
    # ubid_to_anchor: {ubid: {pan_anchor, gstin_anchors, anchor_status, member_count}}
```

### Anchor Selection Logic
- For each cluster, iterate all member records
- `pan_anchor` = first non-null `pan` found in cluster
- `gstin_anchors` = all unique non-null GSTINs in cluster (list)
- `anchor_status` = `"ANCHORED"` if pan_anchor else `"UNANCHORED"`

---

## FILE: `src/activity_engine/signal_config.py`

### Signal Weights (exact)
```python
SIGNAL_WEIGHTS = {
    "electricity_consumption_high":  +0.90,
    "water_consumption_high":        +0.70,
    "licence_renewal":               +0.80,
    "inspection_visit":              +0.70,
    "compliance_filing":             +0.75,
    "administrative_update":         +0.40,
    "electricity_consumption_low":   -0.50,
    "renewal_overdue_180d":          -0.40,
    "closure_declaration":           -1.00,   # PERMANENT
    "licence_cancellation":          -0.90,   # PERMANENT
}
```

### Signal Half-Lives in Days (exact)
```python
SIGNAL_HALF_LIVES = {
    "electricity_consumption_high":  45,
    "water_consumption_high":        45,
    "licence_renewal":               365,
    "inspection_visit":              180,
    "compliance_filing":             270,
    "administrative_update":         90,
    "electricity_consumption_low":   30,
    "renewal_overdue_180d":          180,
    "closure_declaration":           None,   # None = permanent, never decays
    "licence_cancellation":          None,
}
PERMANENT_SIGNALS = {"closure_declaration", "licence_cancellation"}
```

### Classification Thresholds (exact)
```python
THRESHOLD_ACTIVE      = +0.4    # score > 0.4  → ACTIVE
THRESHOLD_DORMANT_LOW = -0.2    # score < -0.2 → CLOSED_SUSPECTED
                                # between       → DORMANT
```

### Decay Formula (exact)
```python
import math
def compute_decay(half_life_days: int, days_since: int) -> float:
    if half_life_days is None:
        return 1.0   # permanent signal, no decay
    lambda_val = math.log(2) / half_life_days
    return math.exp(-lambda_val * days_since)
```

### Seasonal NIC Code Config
```python
SEASONAL_NIC_CODES = {
    "24": {"active_months": [10,11,12,1,2,3]},   # Fireworks / basic chemicals
    "10": {"active_months": [10,11,12,9]},         # Food (festive season peak)
    "14": {"active_months": [6,7,8,9,10,11]},      # Apparel (export season)
}
```

---

## FILE: `src/activity_engine/signal_scorer.py`

### Constants
```python
LOOKBACK_DAYS = 365
```

### Function Signature
```python
def compute_activity_score(ubid: str, events: list, reference_date: datetime = None) -> dict:
    # Returns: {raw_score, activity_status, evidence, event_count, lookback_days, computed_at}
```

### Algorithm (exact order)
1. If `reference_date` is None → use `datetime.now(timezone.utc)`
2. **Check permanent signals FIRST** — if any `event["event_type"]` in `PERMANENT_SIGNALS` → immediately return `CLOSED_CONFIRMED` with score `-1.0`
3. Filter events to lookback window: `event_timestamp > reference_date - LOOKBACK_DAYS days`
4. For each remaining event: `contribution = SIGNAL_WEIGHTS[event_type] * compute_decay(half_life, days_since)`
5. Sum all contributions: `total_score`
6. Normalise: `normalised = 2 / (1 + exp(-total_score)) - 1` → range [-1, +1]
7. Classify using thresholds
8. Sort evidence by `abs(contribution)` descending
9. Return full result dict

### Evidence Item Structure
```python
{
    "event_type":       str,
    "event_timestamp":  str,
    "source_system":    str,
    "weight":           float,
    "decay":            float,   # rounded to 4dp
    "contribution":     float,   # rounded to 4dp
    "days_since":       int
}
```

---

## FILE: `src/activity_engine/event_router.py`

### Purpose
Poll unprocessed events from `activity_events_raw` (`processed=False`), look up their UBID via `ubid_source_links`, write to `ubid_activity_events` or `unmatched_events`.

### Function Signature
```python
def route_all_events(record_to_ubid: dict, db: Session) -> dict:
    # record_to_ubid: {"source_system:source_record_id": "KA-UBID-XXXXXX"}
    # Returns: {"routed": int, "unmatched": int}
```

### Routing Logic
```python
for event in unprocessed_events:
    lookup_key = f"{event.source_system}:{event.source_record_id}"
    ubid = record_to_ubid.get(lookup_key)
    if ubid:
        # Write to ubid_activity_events with signal_weight and half_life_days from SIGNAL_CONFIG
        ...
        event.processed = True
    else:
        # Write to unmatched_events with reason_unmatched = "NO_SOURCE_LINK"
        ...
        event.processed = True  # Still mark processed, never silently drop
```

---

## FILE: `src/activity_engine/activity_classifier.py`

### Purpose
Bulk-run activity scoring for all UBIDs. Update `activity_scores` table. Mark `is_current=True` for new, `is_current=False` for old.

### Function Signature
```python
def classify_all_ubids(ubid_list: List[str], db: Session) -> dict:
    # Returns: {ubid: activity_status} for all processed
```

### Logic Per UBID
1. Fetch all events from `ubid_activity_events` for this ubid
2. Call `compute_activity_score(ubid, events)`
3. Set old `ActivityScore` rows for this ubid to `is_current=False`
4. Write new `ActivityScore` row with `is_current=True`
5. Update `ubid_entities.activity_status` to match

---

## FILE: `src/api/main.py`

```python
app = FastAPI(title="UBID Platform API", version="1.0.0")
# CORS: allow_origins from env CORS_ORIGINS (default: "http://localhost:3000")
# Routers: prefix /api/ubid, /api/activity, /api/review, /api/admin
# Health: GET /health → {"status": "ok", "service": "ubid-platform"}
```

---

## FILE: `src/api/routers/ubid.py`

### Endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/api/ubid/lookup` | Query params: `pan`, `gstin`, `name`, `pincode`. Returns UBID detail. |
| GET | `/api/ubid/{ubid}` | Full detail with source records + evidence + activity status |

### Response Structure for Detail
```python
{
    "ubid": str,
    "pan_anchor": str | None,
    "gstin_anchors": list,
    "anchor_status": str,
    "activity_status": str,
    "activity_score": float | None,
    "source_records": [
        {"source_system", "source_record_id", "confidence", "link_type", "linked_at",
         "evidence": {"feature_vector", "shap_values", "calibrated_score"}}
    ],
    "source_record_count": int,
    "created_at": str
}
```

---

## FILE: `src/api/routers/activity.py`

### THE DEMO QUERY — Exact endpoint
```
GET /api/activity/query
Query params: status, pincode, sector_nic, no_inspection_days
Example: /api/activity/query?status=ACTIVE&pincode=560058&no_inspection_days=540
```

### Filter Logic
1. Filter `activity_scores` where `is_current=True` and `activity_status=status`
2. Filter by pincode via `ubid_source_links`
3. Filter by no recent inspection: check `ubid_activity_events` for `event_type IN ("inspection_visit","safety_inspection","environmental_inspection")` after `cutoff_date`
4. Cap results at `200` for demo

### Also implement
```
GET /api/activity/{ubid}/timeline → all events for UBID ordered by timestamp desc
```

---

## FILE: `src/api/routers/review.py`

### Endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/api/review/queue` | Paginated. Params: `page=1`, `page_size=20`, `status=PENDING` |
| GET | `/api/review/task/{task_id}` | Full review card with both records + feature scores + SHAP |
| POST | `/api/review/task/{task_id}/decision` | Body: `{decision, reason}` |
| GET | `/api/review/stats` | `{queue_depth, auto_link_rate_pct, override_rate, avg_score}` |

### Decision Values (exact)
```
CONFIRM_MATCH / CONFIRM_NON_MATCH / CONFIRM_PARTIAL / REQUEST_INFO / DEFER
```

---

## FILE: `src/api/routers/admin.py`

### Endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/api/admin/audit-log` | Full append-only decision trail. Paginated. |
| GET | `/api/admin/model-stats` | `{model_version, val_auc, val_f1, override_rate, last_retrain}` |
| POST | `/api/admin/thresholds` | Body: `{auto_link_threshold, review_threshold}` — updates env/DB config |

---

## FILE: `scripts/train_model.py`

### Steps
1. Load `data/ground_truth/labelled_pairs.csv`
2. For each pair row, load both normalised records from `data/processed/` (or re-normalise from raw)
3. Call `extract_features(rec_a, rec_b)` → build X matrix
4. Call `scorer.train_model(df)` — splits 80/20, trains, calibrates, saves pkl
5. Log to MLflow
6. Print: `Validation AUC`, `F1 at 0.95 threshold`

---

## FILE: `scripts/reset_demo.py`

```python
# TRUNCATE these tables in this ORDER (respects FK constraints):
# unmatched_events, activity_scores, ubid_activity_events,
# review_tasks, ubid_link_evidence, ubid_source_links, ubid_entities
# Use: conn.execute("TRUNCATE ... RESTART IDENTITY CASCADE")
# Leave source tables INTACT: dept_shop_establishment, dept_factories, dept_labour, dept_kspcb, activity_events_raw
```

---

## FILE: `scripts/run_pipeline.py`

### 9 Steps in Order
```
Step 1: Load source records from all 4 dept tables
Step 2: Normalise all records via standardise_record()
Step 3: generate_candidate_pairs(normalised)
Step 4: extract_features() for all pairs
Step 5: score_pair() for all pairs — classify into auto_link / review / keep_separate
Step 6: assign_ubids(auto_link_pairs, all_records)
Step 7: persist UBID registry to DB (ubid_entities, ubid_source_links, ubid_link_evidence)
Step 8: Create review_tasks for pairs in "review" bucket
Step 9: route_all_events() + compute_activity_score() for all UBIDs
```

---

## Success Metrics to Validate After Pipeline Run

| Metric | Target | How to Check |
|---|---|---|
| Entity Resolution F1 | ≥ 0.92 | Run scorer eval on 500-pair held-out set |
| Blocking Pair Recall | ≥ 99.5% | `test_blocker.py` against `labelled_pairs.csv` |
| Auto-link Rate | 60–75% | `GET /api/review/stats` → `auto_link_rate_pct` |
| Activity Classification Accuracy | ≥ 88% | Compare vs ground_truth_status in entity_clusters.csv |
| UBID Lookup p99 Response Time | < 200ms | Run locust/k6 with 100 concurrent |
| Unmatched Event Rate | < 5% | `SELECT COUNT(*) FROM unmatched_events` / total |
| Review Queue Depth | 2,400–3,600 items | `GET /api/review/stats` → `queue_depth` |

---

## STEP 8: Infrastructure & Docker

---

## FILE: `docker-compose.yml`

### Services (exact names, ports, and dependencies)

```yaml
version: "3.9"

services:

  postgres:
    image: postgres:15-alpine
    container_name: ubid_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-ubid}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-ubid_secret}
      POSTGRES_DB: ${POSTGRES_DB:-ubid_platform}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-ubid}"]
      interval: 10s
      timeout: 5s
      retries: 5

  nominatim:
    image: mediagis/nominatim:4.2
    container_name: ubid_nominatim
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      PBF_URL: https://download.geofabrik.de/asia/india-latest.osm.pbf
      REPLICATION_URL: https://planet.openstreetmap.org/replication/hour/
      IMPORT_WIKIPEDIA: "false"
      IMPORT_TIGER_ADDRESSES: "false"
    volumes:
      - nominatim_data:/var/lib/nominatim
    # NOTE: First startup takes 30–60 min to download and index OSM data.
    # For demo, pre-build the image with data and push to a private registry.

  mlflow:
    image: python:3.11-slim
    container_name: ubid_mlflow
    restart: unless-stopped
    working_dir: /mlflow
    command: mlflow server --host 0.0.0.0 --port 5000 --default-artifact-root /mlflow/artifacts
    ports:
      - "5000:5000"
    volumes:
      - mlflow_data:/mlflow

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: ubid_backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-ubid}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-ubid_secret}
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: ${POSTGRES_DB:-ubid_platform}
      SCRAMBLER_SECRET_KEY: ${SCRAMBLER_SECRET_KEY:-change_me_in_prod}
      NOMINATIM_URL: http://nominatim:8080
      MLFLOW_TRACKING_URI: http://mlflow:5000
      THRESHOLD_AUTO_LINK: "0.95"
      THRESHOLD_REVIEW: "0.75"
      CORS_ORIGINS: "http://localhost:3000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./src:/app/src
      - ./data:/app/data
      - ./scripts:/app/scripts

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
    container_name: ubid_frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost:8000
    depends_on:
      - backend

volumes:
  postgres_data:
  nominatim_data:
  mlflow_data:
```

---

## FILE: `Dockerfile.backend`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system deps (for psycopg2, h3)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run Alembic migrations, then start the API server
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.api.main:app --host 0.0.0.0 --port 8000"]
```

---

## FILE: `frontend/Dockerfile.frontend`

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000
CMD ["npm", "start"]
```

---

## FILE: `.env.example`

```ini
# PostgreSQL
POSTGRES_USER=ubid
POSTGRES_PASSWORD=ubid_secret
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ubid_platform

# PII Scrambler (HMAC key — change this in production)
SCRAMBLER_SECRET_KEY=replace_with_a_long_random_secret

# Nominatim (self-hosted OSM geocoder)
NOMINATIM_URL=http://localhost:8080

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# Entity Resolution Thresholds
THRESHOLD_AUTO_LINK=0.95
THRESHOLD_REVIEW=0.75

# CORS (comma-separated list of allowed origins)
CORS_ORIGINS=http://localhost:3000
```

---

## FILE: `alembic.ini` + `alembic/env.py`

### `alembic.ini` — One line to set
```ini
sqlalchemy.url = postgresql://%(POSTGRES_USER)s:%(POSTGRES_PASSWORD)s@%(POSTGRES_HOST)s/%(POSTGRES_DB)s
```

### `alembic/env.py` — Key settings
```python
from src.database.models import Base
target_metadata = Base.metadata  # Required for autogenerate

# Load DB URL from env (override alembic.ini)
import os
config.set_main_option(
    "sqlalchemy.url",
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST', 'localhost')}/{os.getenv('POSTGRES_DB')}"
)
```

### Migration Commands
```bash
# Generate migration from ORM models
alembic revision --autogenerate -m "initial_schema"

# Apply all pending migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## Startup Sequence (Exact Order for Demo)

```
1. cp .env.example .env          # Fill in secrets
2. docker compose up -d postgres mlflow nominatim
3. docker compose up -d backend  # Runs alembic upgrade head on startup
4. python scripts/generate_synthetic_data.py   # Populate raw source tables
5. python scripts/train_model.py               # Train & save ML model artifacts
6. python scripts/run_pipeline.py              # Run ER + activity pipeline
7. docker compose up -d frontend
8. Open http://localhost:3000
```

> **Demo Reset**: `python scripts/reset_demo.py` then re-run steps 6 onwards.
