# UBID Platform — LLM & AI Implementation
### Samvaya Hackathon | Gemini 2.5 Flash + Llama 3.1 8B Hybrid

---

## Routing Policy (Core Principle)

```
PII_SENSITIVE tasks   → LOCAL  (Ollama Llama 3.1 8B on RTX 4050, always, no exceptions)
SAFE tasks            → API    (Gemini 2.5 Flash → Groq llama-3.1-8b-instant fallback)
FORCE_LOCAL_ONLY=true → LOCAL  (all tasks, air-gap demo mode)
```

Demo Day cascade: **Local Ollama → Gemini 2.5 Flash → Groq → Cached response**

---

## Step 1 — Create `src/llm_router.py` ⭐ Priority 1

This file does not exist yet. Create it from scratch.

### TaskType Enum
```python
from enum import Enum

class TaskType(Enum):
    # ── LOCAL LANE — hard-routed, no exceptions ──────────────────────────
    ADDRESS_NER             = "address_ner"           # Raw address → structured JSON
    REVIEWER_EXPLANATION    = "reviewer_explanation"  # Raw canonical fields → 2-sentence review
    PAN_MISMATCH_NARRATION  = "pan_mismatch"          # PAN hard-reject explanation
    INTRA_DEPT_DUPLICATE    = "intra_dept_duplicate"  # Same-dept duplicate explanation
    NAME_CANONICALISE       = "name_canonicalise"     # Ambiguous name token resolution

    # ── API LANE — Gemini 2.5 Flash → Groq fallback ──────────────────────
    REVIEWER_SUMMARY        = "reviewer_summary"       # Scrambled inputs → card summary
    REVIEWER_SCORE_SUMMARY  = "reviewer_score_summary" # Feature scores only → no PII, API-safe
    ACTIVITY_EXPLANATION    = "activity_explanation"   # UBID activity status narration
    ANALYTICS_NARRATION     = "analytics_narration"    # Aggregate dashboard narration
    SYNTHETIC_AUGMENTATION  = "synthetic_augmentation"
    EVENT_CLASSIFIER        = "event_classifier"       # Map unknown event to known type
    NL_QUERY_PARSE          = "nl_query_parse"         # NL string → structured JSON filter params

_PII_SENSITIVE_TASKS = {
    TaskType.ADDRESS_NER,
    TaskType.REVIEWER_EXPLANATION,
    TaskType.PAN_MISMATCH_NARRATION,
    TaskType.INTRA_DEPT_DUPLICATE,
    TaskType.NAME_CANONICALISE,
    # REVIEWER_SCORE_SUMMARY intentionally excluded — feature scores only, no raw PII
}
```

### Configuration
```python
import os
import logging
log = logging.getLogger(__name__)

OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
FORCE_LOCAL_ONLY = os.getenv("FORCE_LOCAL_ONLY", "false").lower() == "true"
```

### Module-level Gemini init (load once, not per call)
```python
# Initialise at import time — avoids re-configuring on every route() call
_gemini_model = None
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
except Exception as e:
    log.warning(f"Gemini init failed: {e}. API lane will fall through to Groq.")
```

### `_call_ollama()` — Local Llama 3.1 8B
```python
import httpx
def _call_ollama(prompt: str, system: str = "", max_tokens: int = 512) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": max_tokens,
            "num_gpu": 32,          # All 32 Llama layers onto RTX 4050 VRAM (use 32, not 99)
        }
    }
    resp = httpx.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=30.0)
    resp.raise_for_status()
    return resp.json()["response"].strip()
```

### `_call_gemini()` — Gemini 2.5 Flash
```python
def _call_gemini(prompt: str, system: str = "", max_tokens: int = 512) -> str:
    # Uses module-level _gemini_model — no re-init per call
    if _gemini_model is None:
        raise RuntimeError("Gemini model not initialised (missing API key or import error)")
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    response = _gemini_model.generate_content(
        full_prompt,
        generation_config={"temperature": 0.2, "max_output_tokens": max_tokens},
    )
    return response.text.strip()
```

### `_call_groq()` — Groq Fallback
```python
def _call_groq(prompt: str, system: str = "", max_tokens: int = 512) -> str:
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": "llama-3.1-8b-instant", "messages": messages,
               "max_tokens": max_tokens, "temperature": 0.2}
    resp = httpx.post("https://api.groq.com/openai/v1/chat/completions",
                      headers=headers, json=payload, timeout=20.0)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()
```

### `route()` — Main Dispatcher
```python
def route(task_type: TaskType, prompt: str, system: str = "", max_tokens: int = 512) -> str:
    is_pii = task_type in _PII_SENSITIVE_TASKS
    use_local = is_pii or FORCE_LOCAL_ONLY

    if use_local:
        # Hard fail — never send PII to API lane, even if Ollama is down
        try:
            return _call_ollama(prompt, system, max_tokens)
        except Exception as e:
            raise RuntimeError(
                f"LOCAL LLM required for PII task '{task_type.value}' "
                f"but Ollama unreachable. Run 'ollama serve'. Error: {e}"
            )

    # API lane: true 3-step cascade — Gemini → Groq → Ollama
    # Each step logs its failure before falling through, so you know exactly what failed.
    for caller, name in [
        (_call_gemini, "Gemini"),
        (_call_groq,   "Groq"),
        (_call_ollama, "Ollama"),
    ]:
        try:
            return caller(prompt, system, max_tokens)
        except Exception as e:
            log.warning(f"[route] {name} failed for task '{task_type.value}': {e}")

    raise RuntimeError(
        f"All LLM backends unavailable for task '{task_type.value}'. "
        "Check Ollama, Gemini key, and Groq key."
    )
```

### Convenience Wrappers
```python
import json

def extract_address_components(raw_address: str) -> dict:
    """NER on raw address. Always LOCAL — raw addresses are PII."""
    system = "You are a data extractor for Karnataka government records. Output ONLY valid JSON."
    prompt = (
        f'Extract components from this Karnataka address:\n"{raw_address}"\n\n'
        'Output: {"building": "", "street": "", "locality": "", '
        '"area_type": "BBMP|Industrial|Survey|Landmark|Unknown", "pincode": ""}'
    )
    result = route(TaskType.ADDRESS_NER, prompt, system, max_tokens=200)
    try:
        clean = result.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"building": None, "street": None, "locality": None,
                "area_type": "Unknown", "pincode": None, "parse_error": True}


def generate_reviewer_summary(scrambled_a: dict, scrambled_b: dict,
                               feature_scores: dict, confidence: float) -> str:
    """Reviewer card summary. Uses SCRAMBLED inputs — safe for API lane."""
    system = "You are a data analyst reviewing business entity matching for a government platform."
    prompt = (
        f"Two scrambled business records have {confidence:.0%} match confidence.\n\n"
        f"Record A: {json.dumps(scrambled_a, indent=2)}\n"
        f"Record B: {json.dumps(scrambled_b, indent=2)}\n"
        f"Feature scores: {json.dumps(feature_scores)}\n\n"
        "Write exactly 2 sentences: (1) strongest evidence they ARE the same business, "
        "(2) strongest evidence they are NOT."
    )
    return route(TaskType.REVIEWER_SUMMARY, prompt, system, max_tokens=200)


def explain_activity_status(ubid: str, status: str, evidence: list) -> str:
    """Plain-English activity status explanation. API lane — no PII."""
    system = "Explain a business activity classification to a government officer. Be clear and factual."
    prompt = (
        f"Business UBID {ubid} is classified as {status}.\n"
        f"Evidence signals:\n"
        + "\n".join(
            f"  - {e['event_type']}: score={e['contribution']:.3f}, {e['days_since']}d ago"
            for e in evidence[:8]
        )
        + "\n\nExplain this in 2 sentences suitable for a government audit report."
    )
    return route(TaskType.ACTIVITY_EXPLANATION, prompt, system, max_tokens=150)
```

---

## Step 2 — LLM Hook: `src/normalisation/address_parser.py`

**File:** `src/normalisation/address_parser.py`
**Where:** In `parse_address()`, replace the final `else:` block (when no pattern matches).
**Lane:** 🔴 LOCAL — raw addresses contain PII.

```python
else:
    # LLM fallback for unrecognised address formats
    try:
        from src.llm_router import extract_address_components
        llm_result = extract_address_components(addr)
        parsed.address_type = llm_result.get("area_type", "unknown").lower()
        parsed.locality = llm_result.get("locality") or parsed.locality
        if not parsed.pin_code:
            parsed.pin_code = llm_result.get("pincode")
    except Exception:
        parsed.address_type = "minimal"   # Graceful degradation
    _extract_locality(addr, parsed)
```

**Trigger condition:** Only fires when all 5 regex patterns fail (~10% of records). Keeps >90% of parsing rule-based (fast, free).

---

## Step 3 — LLM Hook: `src/entity_resolution/scorer.py` ⭐ Priority 1

**File:** `src/entity_resolution/scorer.py`
**Where:** In `score_pair()`, after `decision` is determined (after line ~75).
**Lane:** 🔴 LOCAL — raw canonical fields are PII.

```python
reviewer_explanation = None
if decision == "REVIEW":
    from src.llm_router import route, TaskType
    prompt = (
        f"Two Karnataka business records scored {calibrated_score:.0%} match confidence.\n\n"
        f"Record A: name='{rec_a.get('raw_name')}', address='{rec_a.get('raw_address')}', "
        f"PAN={rec_a.get('pan', 'N/A')}\n"
        f"Record B: name='{rec_b.get('raw_name')}', address='{rec_b.get('raw_address')}', "
        f"PAN={rec_b.get('pan', 'N/A')}\n\n"
        f"Key signals: name_sim={feature_dict.get('F01', 0):.2f}, "
        f"pan_match={feature_dict.get('F04')}, phone_match={feature_dict.get('F09')}\n\n"
        "Write 2 sentences: (1) strongest evidence they ARE the same business, "
        "(2) strongest evidence they are NOT. Be specific."
    )
    reviewer_explanation = route(TaskType.REVIEWER_EXPLANATION, prompt, max_tokens=150)

# Add to existing return dict:
return {
    "calibrated_score": calibrated_score,
    "decision": decision,
    "shap_values": shap_dict,
    "pan_hard_rule_applied": pan_hard_rule,
    "reviewer_explanation": reviewer_explanation,   # ← NEW
}
```

---

## Step 4 — LLM Hook: `src/activity_engine/signal_scorer.py`

**File:** `src/activity_engine/signal_scorer.py`
**Where:** In `compute_activity_score()`, replace `continue` when `event_type not in SIGNAL_WEIGHTS`.
**Lane:** 🟡 API — event type strings are generic metadata, no PII.

```python
if event_type not in SIGNAL_WEIGHTS:
    try:
        from src.llm_router import route, TaskType
        known_types = list(SIGNAL_WEIGHTS.keys())
        mapped = route(
            TaskType.EVENT_CLASSIFIER,
            f"Map this event to the closest match from: {known_types}\n"
            f"Unknown event: '{event_type}'\n"
            "Return ONLY the matched event type string, nothing else.",
            max_tokens=30
        ).strip().strip('"')
        event_type = mapped if mapped in SIGNAL_WEIGHTS else event_type
    except Exception:
        pass
    if event_type not in SIGNAL_WEIGHTS:
        continue   # Still skip if LLM couldn't map it
```

---

## Step 5 — LLM Hook: `src/activity_engine/activity_classifier.py`

**File:** `src/activity_engine/activity_classifier.py`
**Where:** After `score_data` is computed, before the `return` statement.
**Lane:** 🟡 API — scrambled UBID + generic event metadata, no PII.

```python
# Attach AI narrative to evidence snapshot
try:
    from src.llm_router import explain_activity_status
    narrative = explain_activity_status(
        ubid,
        score_data["activity_status"],
        score_data.get("evidence", [])[:8]
    )
    score_data["activity_narrative"] = narrative
except Exception:
    score_data["activity_narrative"] = None
```

---

## Step 6 — API Update: `src/api/routers/review.py` ⭐ Priority 1

### `GET /review/task/{task_id}` — Add `ai_explanation`
```python
# Before the return statement in get_review_task_detail():
import json
ai_explanation = task.reviewer_summary   # Fast path: pre-generated by pregenerate_summaries.py

if not task.reviewer_summary:
    try:
        from src.llm_router import route, TaskType
        fv = task.feature_vector if isinstance(task.feature_vector, dict) \
             else json.loads(task.feature_vector or "{}")
        prompt = (
            f"Match confidence: {task.calibrated_score:.0%}. "
            f"Feature scores (F01=name, F04=PAN, F06=pin, F09=phone): "
            f"{json.dumps({k: round(v,2) for k,v in fv.items() if v is not None})}\n"
            "In 2 sentences: (1) why this might be a match, (2) what the reviewer should verify."
        )
        # ✅ REVIEWER_SCORE_SUMMARY (API lane) — prompt contains feature scores only, no raw PII.
        # Do NOT use REVIEWER_EXPLANATION here — that forces LOCAL and is for raw name/address/PAN.
        ai_explanation = route(TaskType.REVIEWER_SCORE_SUMMARY, prompt, max_tokens=120)
    except Exception:
        ai_explanation = None

# Add to return dict:
"ai_explanation": ai_explanation,
```

### `GET /review/queue` — Add `ai_teaser` per card
```python
# In the tasks list comprehension, add:
"ai_teaser": t.reviewer_summary.split('.')[0] if t.reviewer_summary else None,
```

### `GET /review/stats` — Add `ai_insights`
```python
# Module-level cache — stats don't change second-to-second, no need to hit Gemini on every refresh
import time
_stats_insights_cache: dict = {"ts": 0.0, "value": None}
_STATS_CACHE_TTL = 300  # 5 minutes

# After computing counts, add:
ai_insights = _stats_insights_cache["value"]  # Serve cached value by default
if time.time() - _stats_insights_cache["ts"] > _STATS_CACHE_TTL:
    try:
        from src.llm_router import route, TaskType
        stats_prompt = (
            f"Review queue stats: {pending} pending, {decided} decided, "
            f"{auto_link_count} auto-links, {manual_link_count} manual links. "
            f"Auto-link rate: {auto_link_rate:.1f}%. "
            "Give 1 sentence of insight for a government data quality officer."
        )
        ai_insights = route(TaskType.ANALYTICS_NARRATION, stats_prompt, max_tokens=80)
        _stats_insights_cache["value"] = ai_insights
        _stats_insights_cache["ts"] = time.time()
    except Exception:
        ai_insights = _stats_insights_cache["value"]  # Stale cache beats None on failure

# Add to return dict:
"ai_insights": ai_insights,
```

---

## Step 7 — API Update: `src/api/routers/activity.py`

### `GET /{ubid}/timeline` — Add `activity_narrative`
```python
# After fetching events, before return:
try:
    from src.llm_router import explain_activity_status
    current_score = db.query(ActivityScore).filter(
        ActivityScore.ubid == ubid, ActivityScore.is_current == True
    ).first()
    current_status = current_score.activity_status if current_score else "UNKNOWN"
    evidence_list = [{"event_type": e.event_type, "contribution": e.signal_weight or 0,
                      "days_since": (datetime.now(timezone.utc) - e.event_timestamp.replace(
                          tzinfo=timezone.utc)).days} for e in events[:8]]
    activity_narrative = explain_activity_status(ubid, current_status, evidence_list)
except Exception:
    activity_narrative = None

# Add to return dict:
"activity_narrative": activity_narrative,
```

---

## Step 8 — New Script: `scripts/pregenerate_summaries.py`

> [!IMPORTANT]
> Run the **night before the demo**. Then run `reset_demo.py`. Zero live API calls during presentation.

```python
"""
Pre-generates AI reviewer summaries via Gemini 2.5 Flash for all REVIEW-bucket tasks.
Input: scrambled canonical fields (safe for API lane).
Output: stored in review_tasks.reviewer_summary (DB).
Rate-limited to 12 req/min (under Gemini free tier 15 RPM).

Run: python scripts/pregenerate_summaries.py
"""
import time, sys
sys.path.insert(0, '.')

from tqdm import tqdm
from src.database.connection import SessionLocal
from src.database.models import ReviewTask
from src.normalisation.pii_scrambler import scramble_record
from src.llm_router import generate_reviewer_summary

_SOURCE_MODELS = None  # Populated lazily to avoid circular imports

def _get_source_models():
    global _SOURCE_MODELS
    if _SOURCE_MODELS is None:
        from src.database.models import (
            DeptShopEstablishment, DeptFactories, DeptLabour, DeptKSPCB
        )
        _SOURCE_MODELS = {
            "shop_establishment": (DeptShopEstablishment, "se_reg_no",        "business_name", "address"),
            "factories":          (DeptFactories,         "factory_licence_no","factory_name",  "address"),
            "labour":             (DeptLabour,            "employer_code",     "employer_name", "address"),
            "kspcb":              (DeptKSPCB,             "consent_order_no",  "unit_name",     "address"),
        }
    return _SOURCE_MODELS

def _fetch_source_record(source_ref: str, db) -> dict:
    """Fetch raw record from the correct dept table and scramble it before sending to API."""
    if ":" not in source_ref:
        raise ValueError(f"source_ref must be 'system:record_id', got: {source_ref!r}")

    source_system, record_id = source_ref.split(":", 1)
    models = _get_source_models()

    if source_system not in models:
        raise ValueError(f"Unknown source_system: {source_system!r}")

    model_cls, pk_field, name_field, addr_field = models[source_system]
    record = db.query(model_cls).filter(
        getattr(model_cls, pk_field) == record_id
    ).first()

    if record is None:
        raise LookupError(f"Record {record_id!r} not found in {source_system}")

    raw = {
        "name":    getattr(record, name_field, None),
        "address": getattr(record, addr_field, None),
        "pan":     getattr(record, "pan", None),
        "phone":   getattr(record, "phone", None),
    }
    return scramble_record(raw)

def pregenerate():
    db = SessionLocal()
    tasks = db.query(ReviewTask).filter(
        ReviewTask.status == "PENDING",
        ReviewTask.reviewer_summary == None
    ).all()

    print(f"Found {len(tasks)} tasks without pre-generated summaries.")

    for task in tqdm(tasks, desc="Generating summaries"):
        try:
            rec_a = _fetch_source_record(task.pair_record_a, db)
            rec_b = _fetch_source_record(task.pair_record_b, db)
            feature_scores = task.feature_vector or {}
            summary = generate_reviewer_summary(
                rec_a, rec_b, feature_scores, task.calibrated_score or 0.0
            )
            task.reviewer_summary = summary
            db.commit()
            time.sleep(5)   # 12 req/min — stays under free tier 15 RPM
        except Exception as e:
            print(f"  ⚠ Failed task {task.task_id}: {e}")
            db.rollback()

    db.close()
    print("✅ Pre-generation complete. Now run: python scripts/reset_demo.py")

if __name__ == "__main__":
    pregenerate()
```

---

## Step 9 — Optional: F14 Semantic Embedding

**File:** `src/entity_resolution/feature_extractor.py`
**Lane:** 🔴 LOCAL — embedding model runs on RTX 4050 GPU, no API call.

### Module-level (load once, cache forever):
```python
try:
    from sentence_transformers import SentenceTransformer, util as st_util
    _EMBED_MODEL = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
    # First load: ~3s on RTX 4050. Subsequent calls: ~5-10ms.
except ImportError:
    _EMBED_MODEL = None
```

### Inside `extract_features()`, after F02:
```python
# F14 — Multilingual semantic cosine similarity
if _EMBED_MODEL and name_a and name_b:
    emb = _EMBED_MODEL.encode([name_a, name_b], convert_to_tensor=True)
    features["F14"] = float(st_util.cos_sim(emb[0], emb[1]))
else:
    features["F14"] = None
```

**Also update `scorer.py`:**
```python
FEATURE_ORDER = ["F01","F02","F03","F04","F05","F06","F07",
                 "F08","F09","F10","F11","F12","F13","F14"]  # Add F14
```

Then **retrain the model**: `python scripts/train_model.py`

> [!TIP]
> Install separately: `pip install sentence-transformers`. Downloads ~400MB model on first run.

---

## Step 10 — Stretch: `POST /api/nl-query`

**File:** `src/api/routers/nlquery.py` (new file)
**Lane:** 🟡 API — query string has no PII.

```python
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from src.database.connection import get_db
import json

router = APIRouter()

@router.post("/nl-query")
def natural_language_query(
    query: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Example: "Show dormant textile factories in 560058 with no inspection in 18 months"
    → {"status": "DORMANT", "pincode": "560058", "no_inspection_days": 540}
    """
    from src.llm_router import route, TaskType
    prompt = (
        f"Convert this query to JSON filter params:\n'{query}'\n\n"
        'Output ONLY valid JSON: {"status": "ACTIVE|DORMANT|CLOSED_SUSPECTED|CLOSED_CONFIRMED|null", '
        '"pincode": "6-digit string|null", "no_inspection_days": number|null}'
    )
    # ✅ NL_QUERY_PARSE — structured extraction, not prose narration. Never use ANALYTICS_NARRATION here.
    params_json = route(TaskType.NL_QUERY_PARSE, prompt, max_tokens=80)
    try:
        params = json.loads(params_json.strip().lstrip("```json").lstrip("```").rstrip("```"))
    except Exception:
        return {"error": "Could not parse query", "raw": params_json}

    # Re-use existing activity query logic
    from src.api.routers.activity import query_businesses
    return query_businesses(
        status=params.get("status"),
        pincode=params.get("pincode"),
        no_inspection_days=params.get("no_inspection_days"),
        db=db
    )
```

Register in `src/api/main.py`:
```python
from src.api.routers import nlquery
app.include_router(nlquery.router, prefix="/api", tags=["NL Query"])
```

---

## Environment Variables Required

Add to `.env` and `.env.example`:
```env
GEMINI_API_KEY=your_google_ai_studio_key_here
GROQ_API_KEY=your_groq_api_key_here
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
FORCE_LOCAL_ONLY=false
```

Add to `docker-compose.yml` backend service:
```yaml
- GEMINI_API_KEY=${GEMINI_API_KEY}
- GROQ_API_KEY=${GROQ_API_KEY}
- OLLAMA_BASE_URL=http://host.docker.internal:11434
- FORCE_LOCAL_ONLY=${FORCE_LOCAL_ONLY:-false}
```

Add to `requirements.txt`:
```
# LLM / AI
google-generativeai>=0.8.0
groq>=0.9.0
sentence-transformers>=2.7.0   # Step 9 only — downloads ~400MB model on first run
```

> [!WARNING]
> These packages are **not** in the main `requirements.txt` yet. Add them before running any LLM code or
> you will get `ImportError` at runtime. `sentence-transformers` is only needed for Step 9 (F14 embedding)
> — keep it separate if your team is not implementing that step.

---

## LLM Sprint Order

```
Hour 1 (Priority):
  ✦ Create src/llm_router.py (Steps 1 complete)
  ✦ Apply scorer.py hook (Step 3)
  ✦ Apply review.py GET /task/{id} hook (Step 6a)

Hour 2:
  ✦ Apply address_parser.py hook (Step 2)
  ✦ Create scripts/pregenerate_summaries.py (Step 8)

Hour 3:
  ✦ Apply activity_classifier.py hook (Step 5)
  ✦ Apply activity.py timeline hook (Step 7)

Hour 4 (Optional):
  ✦ Add F14 embedding to feature_extractor.py (Step 9)
  ✦ Retrain model

Hour 5 (Stretch):
  ✦ Apply signal_scorer.py EVENT_CLASSIFIER hook (Step 4)
  ✦ Create nlquery.py endpoint (Step 10)
```

---

*All LLM work grounded in: `llm_hybrid_strategy.md` (Gemini 2.5 Flash upgrade applied)*
*Hardware: RTX 4050 6GB VRAM — all 32 Llama layers fit on GPU, zero CPU offload*
