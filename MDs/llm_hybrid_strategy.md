# Revised LLM Integration Strategy — RTX 4050 Edition
### Samvaya UBID Platform | Hackathon Hybrid Architecture

---

## The 6GB VRAM Advantage

The RTX 3050 (4GB VRAM) forced a painful trade-off: `Q4_K_M` Llama 3.1 8B at 4.7GB **could not fit** — it required mixed CPU/GPU offloading (24/32 layers on GPU, 8 layers spilling to system RAM). Every inference crossed the PCIe bus for those 8 layers, adding 400–900ms of latency and creating a live memory-pressure risk when Docker services (PostgreSQL, Nominatim, FastAPI) were competing for RAM.

The RTX 4050 at 6GB VRAM **eliminates this entirely**:

| Layer Metric | RTX 3050 (4GB) | RTX 4050 (6GB) |
|---|---|---|
| GPU layers (`--n-gpu-layers`) | 24 / 32 | **32 / 32** (all layers on GPU) |
| CPU offload layers | 8 | **0** |
| Avg. NER inference latency | ~1,500–3,000ms | **~200–500ms** |
| VRAM headroom after model load | ~0MB (danger zone) | **~1.3GB free** |
| Memory pressure from Docker stack | Risk of OOM | No risk |

With all 32 layers on GPU, the RTX 4050 runs `Q4_K_M` Llama 3.1 8B at approximately **18–25 tokens/second** — fast enough for real-time reviewer card summaries (< 100 tokens output) in under 5 seconds. More importantly, the 1.3GB of free VRAM acts as a buffer, meaning the Docker stack can run simultaneously without competing for resources.

> [!TIP]
> Ollama automatically detects and uses all available VRAM. A simple `ollama pull llama3.1:8b` is all you need — no `--n-gpu-layers` flag required. Ollama will pack all 32 layers onto the 4050 automatically.

---

## Hybrid Routing Architecture

The core principle: **route by PII exposure risk, not by convenience.**

```
┌─────────────────────────────────────────────────────────────────┐
│                    TASK CLASSIFICATION GATE                      │
│                                                                  │
│  Does the input contain or derive from un-scrambled PII?        │
│                                                                  │
│        YES ──────────────────────►  LOCAL LANE                  │
│        NO  ──────────────────────►  API LANE                    │
└─────────────────────────────────────────────────────────────────┘
```

### LOCAL LANE — Llama 3.1 8B Instruct Q4_K_M (Ollama, port 11434)

These tasks are **hard-routed local** regardless of internet availability:

| Task | Why Local | Input Example |
|---|---|---|
| **Address NER** | Raw address strings from dept records are direct PII. Even post-normalization, they contain street names + pin codes that can re-identify businesses before the scrambler runs. | `"Plot No. 14-A, 3rd Main, Peenya Industrial Area, Bengaluru 560058"` |
| **Ambiguity triage explanation** | The reviewer card shows raw canonical fields (pre-scramble) to help the human understand why two records were flagged. These fields contain real business names. | `canonical_name_a`, `canonical_name_b` diff explanation |
| **PAN/GSTIN mismatch narration** | Explaining *why* a PAN mismatch triggered a hard-reject involves referencing actual identifiers (even partially). Must stay local. | `"PAN AABCP1234Q vs AABCP1234R — single character divergence at position 9"` |
| **Intra-dept duplicate explanation** | Explaining why two records in the same department are likely duplicates involves raw source record fields. | Side-by-side source record comparison |

**Prompt pattern for Address NER (local):**
```
System: You are a structured data extractor for Indian government address records. Output ONLY valid JSON. No explanation.

User: Extract address components from this Karnataka business address:
"{raw_address}"

Output format: {"building": "", "street": "", "locality": "", "area_type": "BBMP|Industrial|Survey|Landmark", "pincode": ""}
```

---

### API LANE — Gemini 2.5 Flash (Google AI Studio, free tier)

These tasks operate **only on scrambled or fully synthetic inputs** and are safe to send to a hosted API:

| Task | Why API | Input Safety |
|---|---|---|
| **Reviewer card summaries (bulk pre-generation)** | Run `scripts/run_pipeline.py` the night before demo — all summaries pre-computed from scrambled canonical fields and stored in DB. Zero live API calls during the presentation. | Scrambled names only (HMAC-SHA256 output) |
| **Activity status explanation** | Natural-language explanation of *why* a UBID is classified Active/Dormant/Closed, based on the JSONB evidence snapshot (event types + decayed weights). Event types are generic strings (`"licence_renewal"`, `"electricity_consumption_high"`) — no PII. | Pure event metadata, zero identifying info |
| **Synthetic data generation (Phase 1 augmentation)** | If you need more variation in your `variation_injector.py` outputs (e.g., more realistic address paraphrases, more Kannada name transliterations), Gemini 2.5 Flash can generate synthetic variants at scale. No real data involved. | Faker-generated fictitious names only |
| **Aggregate analytics narration** | C&I executive dashboard: "What does this sector distribution chart mean?" Uses only aggregate counts and percentages — no individual records. | `{"sector": "14", "active_count": 342, "dormant_count": 67}` |
| **Demo query explanation** | Natural-language explanation of the "impossible query" result: *"Active factories in 560058 with no inspection in 18 months."* The result set shows scrambled UBIDs, not raw business names. | Scrambled UBID + aggregate stats |

---

## Updated API Choice

### Primary: **Google Gemini 2.5 Flash** (`gemini-2.5-flash`)

| Parameter | Value |
|---|---|
| Free tier limits | 15 RPM · 1,000,000 TPM · 1,500 req/day |
| Context window | 1,000,000 tokens (entire evidence JSONB, no truncation risk) |
| Latency | 200–500ms (faster reasoning) |
| Structured output | Native JSON mode (`response_mime_type="application/json"`) — critical for NER-style tasks in the API lane |
| SDK | `pip install google-generativeai` |

### Fallback: **Groq** (`llama-3.1-8b-instant`)

Groq is the **perfect fallback** because it runs the *identical model family* as your local Llama 3.1 8B — so prompt templates are 100% portable between local and Groq with no changes.

| Parameter | Value |
|---|---|
| Free tier | 14,400 req/day · 30 RPM · 6,000 TPM per request |
| Latency | ~150–400ms (Groq's LPU is extremely fast) |
| Key advantage | If Gemini quota is exhausted during demo, one env var change switches to Groq with zero code changes |

> [!IMPORTANT]
> **Demo Day API Priority Order:** Local Ollama → Gemini 2.5 Flash → Groq → Graceful degradation (cached pre-computed response). This cascade is implemented in `llm_router.py` below.

---

## The Demo Day "Flex"

### Scoring Maximum Points: Data Privacy + System Reliability

**Pre-Demo Setup (night before):**
1. Run `scripts/run_pipeline.py` — populates UBID registry, pre-generates all reviewer summaries via Gemini API, stores results in `review_tasks.reviewer_summary` (JSONB column).
2. Run `scripts/reset_demo.py` — wipes only the UBID registry, leaving pre-generated summaries intact in a separate cache table.
3. Confirm Ollama is running: `ollama ps` should show `llama3.1:8b` loaded and warm.

**During the Presentation — The "Privacy Kill Switch" Moment:**

> *"We'll now demonstrate that this system's most sensitive operations — address parsing and reviewer card generation — are completely air-gapped from the internet."*

1. **Physically disconnect from Wi-Fi** (or toggle airplane mode visible to judges).
2. Open the Reviewer Queue in the React frontend.
3. Pick an ambiguous REVIEW-bucket pair. Click the record.
4. The reviewer card loads — the address NER and side-by-side comparison explanation were generated **locally by Llama 3.1 8B on the RTX 4050**. The judges will see it generate in real-time (< 2 seconds).
5. Submit a CONFIRM_MATCH decision. The DB updates. The queue depth counter decrements.
6. Say: *"The entire reviewer workflow — including AI-generated explanations — just ran with zero internet. This is the architecture Karnataka's government network requires."*
7. Reconnect Wi-Fi. Navigate to the Analytics Dashboard. *"For non-PII aggregate analytics, we leverage Gemini 2.5 Flash — but only for data that has no individual identifiers."*

**Key talking points for judges:**

- **"Three-zone data policy enforced in code, not just policy"** — show `llm_router.py` with the `TaskType` enum and routing logic. The code *physically cannot* send PII to an external API.
- **"No single point of failure"** — if the cloud API is down, the system degrades gracefully: local Ollama handles everything. The fallback chain is automatic.
- **"Pre-computation for demo stability"** — explains why there's zero latency during the live demo for reviewer summaries: they were computed offline and cached.

---

## Code Blueprint: `llm_router.py`

```python
# src/llm_router.py
"""
Hybrid LLM Router for Samvaya UBID Platform
============================================
Routing policy:
  - PII_SENSITIVE tasks  → LOCAL  (Ollama Llama 3.1 8B, always)
  - SAFE tasks           → API    (Gemini 2.5 Flash → Groq fallback)
  - OFFLINE mode         → LOCAL  (all tasks, no exceptions)

Environment variables:
  OLLAMA_BASE_URL      : default http://localhost:11434
  GEMINI_API_KEY       : Google AI Studio API key
  GROQ_API_KEY         : Groq API key (fallback)
  FORCE_LOCAL_ONLY     : "true" to disable all API calls (air-gap mode)
"""

import os
import json
import httpx
from enum import Enum
from loguru import logger

# ── Task Classification ──────────────────────────────────────────────────────

class TaskType(Enum):
    # PII_SENSITIVE → hard-routed LOCAL, no exceptions
    ADDRESS_NER             = "address_ner"           # Raw address → structured components
    REVIEWER_EXPLANATION    = "reviewer_explanation"  # Why two records may match (raw canonical fields)
    PAN_MISMATCH_NARRATION  = "pan_mismatch"          # PAN hard-reject explanation
    INTRA_DEPT_DUPLICATE    = "intra_dept_duplicate"  # Same-dept duplicate explanation

    # SAFE → routed to API, local fallback if API unavailable
    REVIEWER_SUMMARY        = "reviewer_summary"      # Scrambled-input summary for reviewer card
    ACTIVITY_EXPLANATION    = "activity_explanation"  # Why UBID is Active/Dormant/Closed
    ANALYTICS_NARRATION     = "analytics_narration"   # C&I executive dashboard explanations
    SYNTHETIC_AUGMENTATION  = "synthetic_augmentation" # Faker + variation generation

# Tasks that must NEVER leave the local machine
_PII_SENSITIVE_TASKS = {
    TaskType.ADDRESS_NER,
    TaskType.REVIEWER_EXPLANATION,
    TaskType.PAN_MISMATCH_NARRATION,
    TaskType.INTRA_DEPT_DUPLICATE,
}

# ── Configuration ─────────────────────────────────────────────────────────────

OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
FORCE_LOCAL_ONLY = os.getenv("FORCE_LOCAL_ONLY", "false").lower() == "true"

# ── Local Inference (Ollama) ──────────────────────────────────────────────────

def _call_ollama(prompt: str, system: str = "", max_tokens: int = 512) -> str:
    """Call local Ollama endpoint. Raises on connection failure."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.0,      # Deterministic for structured extraction
            "num_predict": max_tokens,
            "num_gpu": 99,           # Use all available GPU layers (RTX 4050 = all 32)
        }
    }
    resp = httpx.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=30.0)
    resp.raise_for_status()
    return resp.json()["response"].strip()

# ── API Inference (Gemini → Groq cascade) ────────────────────────────────────

def _call_gemini(prompt: str, system: str = "", max_tokens: int = 512) -> str:
    """Call Gemini 2.5 Flash. Falls back to Groq if unavailable."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system or None,
        )
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2, "max_output_tokens": max_tokens},
        )
        logger.debug("LLM → Gemini 2.5 Flash")
        return response.text.strip()

    except Exception as gemini_err:
        logger.warning(f"Gemini unavailable ({gemini_err}), falling back to Groq")
        return _call_groq(prompt, system, max_tokens)

def _call_groq(prompt: str, system: str = "", max_tokens: int = 512) -> str:
    """Call Groq llama-3.1-8b-instant. Last resort API fallback."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    resp = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers, json=payload, timeout=20.0
    )
    resp.raise_for_status()
    logger.debug("LLM → Groq llama-3.1-8b-instant (fallback)")
    return resp.json()["choices"][0]["message"]["content"].strip()

# ── Main Router ───────────────────────────────────────────────────────────────

def route(task_type: TaskType, prompt: str, system: str = "", max_tokens: int = 512) -> str:
    """
    Route an LLM request based on task type and PII policy.

    Args:
        task_type:  Classification of the task (determines routing)
        prompt:     The user-facing prompt content
        system:     Optional system instruction
        max_tokens: Max tokens to generate

    Returns:
        Generated text from the appropriate model

    Raises:
        RuntimeError: If local Ollama is unreachable for a PII-sensitive task
    """
    is_pii_sensitive = task_type in _PII_SENSITIVE_TASKS
    use_local        = is_pii_sensitive or FORCE_LOCAL_ONLY

    if use_local:
        reason = "PII_SENSITIVE task" if is_pii_sensitive else "FORCE_LOCAL_ONLY=true"
        logger.info(f"LLM → LOCAL (Ollama) | task={task_type.value} | reason={reason}")
        try:
            return _call_ollama(prompt, system, max_tokens)
        except Exception as e:
            # For PII-sensitive tasks, we CANNOT fall back to API — raise hard
            raise RuntimeError(
                f"LOCAL LLM required for PII-sensitive task '{task_type.value}' "
                f"but Ollama is unreachable. Ensure 'ollama serve' is running. Error: {e}"
            )
    else:
        logger.info(f"LLM → API (Gemini/Groq) | task={task_type.value}")
        try:
            return _call_gemini(prompt, system, max_tokens)
        except Exception as api_err:
            # For safe tasks, fall back to local if all APIs are down
            logger.warning(f"All APIs failed ({api_err}). Falling back to local Ollama.")
            return _call_ollama(prompt, system, max_tokens)

# ── Convenience Wrappers ──────────────────────────────────────────────────────

def extract_address_components(raw_address: str) -> dict:
    """NER on raw address string. Always runs locally."""
    system = (
        "You are a structured data extractor for Karnataka government address records. "
        "Output ONLY valid JSON. No explanation, no markdown."
    )
    prompt = (
        f'Extract address components from this Karnataka business address:\n"{raw_address}"\n\n'
        'Output format: {"building": "", "street": "", "locality": "", '
        '"area_type": "BBMP|Industrial|Survey|Landmark|Unknown", "pincode": ""}'
    )
    result = route(TaskType.ADDRESS_NER, prompt, system, max_tokens=200)
    try:
        # Strip markdown code fences if model adds them
        clean = result.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        logger.warning(f"Address NER returned non-JSON: {result[:100]}")
        return {"building": None, "street": None, "locality": None,
                "area_type": "Unknown", "pincode": None, "parse_error": True}

def generate_reviewer_summary(scrambled_record_a: dict, scrambled_record_b: dict,
                               feature_scores: dict, confidence: float) -> str:
    """Reviewer card summary. Uses scrambled inputs — safe for API lane."""
    system = (
        "You are an expert data analyst reviewing business entity matching decisions "
        "for a government platform. Be concise and precise."
    )
    prompt = (
        f"Two scrambled business records have a match confidence of {confidence:.0%}.\n\n"
        f"Record A: {json.dumps(scrambled_record_a, indent=2)}\n"
        f"Record B: {json.dumps(scrambled_record_b, indent=2)}\n"
        f"Feature scores (0=no match, 1=perfect match): {json.dumps(feature_scores)}\n\n"
        "Write exactly 2 sentences for a human reviewer: "
        "(1) the strongest evidence these are the same business, "
        "(2) the strongest evidence they are different. "
        "Be specific about which features drove each conclusion."
    )
    return route(TaskType.REVIEWER_SUMMARY, prompt, system, max_tokens=200)

def explain_activity_status(ubid: str, status: str, evidence_snapshot: list) -> str:
    """Plain-English explanation of why a UBID has its current activity status."""
    system = "You are explaining a business activity classification to a government officer. Be clear and factual."
    prompt = (
        f"Business UBID {ubid} is classified as {status}.\n"
        f"Evidence signals (type, contribution score, days ago):\n"
        + "\n".join(
            f"  - {e['event_type']}: score={e['contribution']:.3f}, {e['days_since']}d ago"
            for e in evidence_snapshot[:8]  # top 8 signals
        )
        + "\n\nExplain this classification in 2 sentences suitable for a government audit report."
    )
    return route(TaskType.ACTIVITY_EXPLANATION, prompt, system, max_tokens=150)
```

---

## Quick-Start Checklist

```bash
# 1. Pull the model once (4.7 GB download)
ollama pull llama3.1:8b

# 2. Verify all 32 layers are on GPU (RTX 4050 should show 0 CPU layers)
ollama run llama3.1:8b "ping" --verbose

# 3. Add to .env
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
FORCE_LOCAL_ONLY=false   # Set to "true" for air-gap demo mode

# 4. Pre-generate all reviewer summaries before demo
python scripts/pregenerate_summaries.py   # Calls generate_reviewer_summary() for all REVIEW-bucket tasks

# 5. Demo day — flip to air-gap mode
FORCE_LOCAL_ONLY=true docker compose up   # All LLM calls go local, zero internet dependency
```

---

*Analysis grounded in: `problem_statement.md`, `prototype.md`, `implementation_spec.md`, `task.md`, `ppt.md`, `ppt_second_V.md`, `full_detailed_plan.md` | Hardware: Intel i7-13th Gen + NVIDIA RTX 4050 6GB VRAM*

---

## Layer-by-Layer LLM Integration Map

This section maps every module in the current prototype to its concrete LLM insertion point, using the routing policy defined above.

```
src/
├── normalisation/        ← Layer 1
├── entity_resolution/    ← Layer 2
├── activity_engine/      ← Layer 3
├── api/routers/          ← Layer 4
└── frontend/src/         ← Layer 5
```

---

### Layer 1 — Normalisation (`src/normalisation/`)

**Current approach:** Pure regex + hardcoded dictionaries + phonetic keys (Soundex, Double-Metaphone).

| File | Current Limit | LLM Insertion Point | Router Lane |
|---|---|---|---|
| `name_normaliser.py` | 30-entry abbreviation dict — misses novel variants, mixed Kannada-English, regional slang | After Step 5 (abbrev expansion, ~L151) — call `route(TaskType.NAME_CANONICALISE, ...)` only when the canonical result still contains unknown tokens | **LOCAL** — raw names are PII |
| `address_parser.py` | 5 regex patterns — freeform addresses like *"opp ganesh temple, near peenya signal"* fall through to `address_type = "unknown"` | In the `else` block (L131) — replace the minimal fallback with `extract_address_components()` already defined in `llm_router.py` | **LOCAL** — raw addresses are PII |
| `standardiser.py` | Sequential pipeline, no confidence signal | No change needed — just ensure it calls the LLM-augmented `parse_address()` and `canonicalise_name()` | — |

**Exact code change for `address_parser.py`:**
```python
# In parse_address(), replace the else: block (line 131-133)
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
        parsed.address_type = "minimal"  # graceful degradation
    _extract_locality(addr, parsed)
```

**Trigger condition for `name_normaliser.py`:** Only call LLM when `len(canonical_name.split()) >= 2` AND any token is not in `ABBREVIATION_EXPANSIONS`. This keeps >90% of records rule-based (fast, free).

---

### Layer 2 — Entity Resolution (`src/entity_resolution/`) — 🔥 Highest Priority

**Current approach:** 13-feature vector → LightGBM binary classifier → SHAP explainability.

| File | Current Limit | LLM Insertion Point | Router Lane |
|---|---|---|---|
| `scorer.py` | `REVIEW` bucket (score 0.75–0.95) sends raw SHAP values to human reviewers — meaningless to non-technical staff | After routing decision (~L75), when `decision == "REVIEW"`: call `generate_reviewer_explanation()` | **LOCAL** — raw canonical fields are PII |
| `feature_extractor.py` | F01 (Jaro-Winkler) misses semantic equivalents: *"KANAKA GRANTZ" ≈ "KANAKA GRANITES"* | Add **F14** — semantic embedding cosine similarity using `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (free, local, RTX 3050 compatible) | **LOCAL** — embedded, no API call |
| `blocker.py` | Blocks only on exact phonetic/prefix keys | No change for now — phonetic blocking is fast and sufficient | — |

**Exact code change for `scorer.py`:**
```python
# In score_pair(), after decision is determined (~line 75)
reviewer_explanation = None
if decision == "REVIEW":
    from src.llm_router import route, TaskType
    import json
    prompt = (
        f"Two Karnataka business records scored {calibrated_score:.0%} match confidence.\n\n"
        f"Record A: name='{rec_a.get('raw_name')}', address='{rec_a.get('raw_address')}', "
        f"PAN={rec_a.get('pan', 'N/A')}\n"
        f"Record B: name='{rec_b.get('raw_name')}', address='{rec_b.get('raw_address')}', "
        f"PAN={rec_b.get('pan', 'N/A')}\n\n"
        f"Key signals: name_similarity={feature_dict.get('F01'):.2f}, "
        f"pin_match={feature_dict.get('F06')}, phone_match={feature_dict.get('F09')}, "
        f"pan_match={feature_dict.get('F04')}\n\n"
        "Write 2 sentences: (1) strongest evidence they ARE the same business, "
        "(2) strongest evidence they are NOT. Be specific."
    )
    reviewer_explanation = route(TaskType.REVIEWER_EXPLANATION, prompt, max_tokens=150)

return {
    "calibrated_score": calibrated_score,
    "decision": decision,
    "shap_values": shap_dict,
    "pan_hard_rule_applied": pan_hard_rule,
    "reviewer_explanation": reviewer_explanation,   # ← NEW
}
```

**F14 embedding feature for `feature_extractor.py`:**
```python
# Add after F02 (~line 27)
# F14 — Semantic embedding cosine similarity
try:
    from sentence_transformers import SentenceTransformer, util
    _EMBED_MODEL = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")

    def _embedding_similarity(a: str, b: str) -> float:
        if not a or not b:
            return None
        emb = _EMBED_MODEL.encode([a, b], convert_to_tensor=True)
        return float(util.cos_sim(emb[0], emb[1]))

    features["F14"] = _embedding_similarity(name_a, name_b)
except ImportError:
    features["F14"] = None  # graceful degradation if library not installed
```

> [!TIP]
> Cache the `SentenceTransformer` model at module load time (not inside the function) so it's only loaded once. First load takes ~3 seconds on RTX 3050; subsequent calls are ~5–10ms.

---

### Layer 3 — Activity Engine (`src/activity_engine/`)

**Current approach:** Rule-based decay scoring. Classifies UBIDs as ACTIVE / DORMANT / CLOSED.

| File | Current Limit | LLM Insertion Point | Router Lane |
|---|---|---|---|
| `signal_scorer.py` | Unknown `event_type` keys are silently skipped (L66 `continue`) — loses real signal | Before the `continue`, call `route(TaskType.EVENT_CLASSIFIER, ...)` to map the unknown event to a known type | **API** — event types are generic strings, no PII |
| `activity_classifier.py` | Classification output is just a status string (`"ACTIVE"`) — no narrative for government officers | After `score_data` is computed (~L37): call `explain_activity_status()` already defined in `llm_router.py` and attach to `evidence_snapshot` | **API** — uses `explain_activity_status()` with scrambled UBID + event metadata only |

**Exact code change for `signal_scorer.py`:**
```python
# In compute_activity_score(), replace line ~66
if event_type not in SIGNAL_WEIGHTS:
    # Attempt LLM mapping for unrecognised event types
    try:
        from src.llm_router import route, TaskType
        known_types = list(SIGNAL_WEIGHTS.keys())
        mapped = route(
            TaskType.EVENT_CLASSIFIER,
            f"Map this event type to the closest match from: {known_types}\n"
            f"Unknown event: '{event_type}'\nPayload keys: {list(event.get('payload', {}).keys())}\n"
            "Return ONLY the matched event type string, nothing else.",
            max_tokens=30
        ).strip().strip('"')
        event_type = mapped if mapped in SIGNAL_WEIGHTS else event_type
    except Exception:
        pass
    if event_type not in SIGNAL_WEIGHTS:
        continue  # still skip if LLM couldn't map it
```

> [!NOTE]
> Add `EVENT_CLASSIFIER = "event_classifier"` to the `TaskType` enum in `llm_router.py` and route it to the **API lane** (event metadata contains no PII — just generic strings like `"licence_renewal"`).

---

### Layer 4 — Review API (`src/api/routers/review.py`)

**Current approach:** Returns raw `feature_vector`, `shap_values`, numeric `score`. No AI guidance.

| Endpoint | Current Response | LLM Addition | Router Lane |
|---|---|---|---|
| `GET /review/task/{task_id}` | `feature_vector`, `shap_values`, `score` | Add `ai_explanation` field — retrieved from DB if pre-computed, or generated on-demand | **LOCAL** — involves raw canonical fields |
| `POST /review/task/{task_id}/decision` | Accepts `decision` + `reason` string | Validate reviewer notes are meaningful (optional) | — |
| `GET /review/stats` | Aggregate counts only | Add `ai_insights` — e.g. *"PAN mismatch is the top override reason this week"* | **API** — aggregate stats only, no PII |

**Exact code change for `GET /review/task/{task_id}`:**
```python
# In get_review_task(), before return (line ~63)
ai_explanation = task.reviewer_notes  # existing fallback

# If explanation not pre-generated, generate on-demand
if not task.reviewer_notes and task.feature_vector:
    try:
        from src.llm_router import route, TaskType
        import json
        fv = task.feature_vector if isinstance(task.feature_vector, dict) else json.loads(task.feature_vector)
        prompt = (
            f"Match confidence: {task.score:.0%}. "
            f"Feature scores (F01=name_similarity, F04=PAN, F05=GSTIN, F06=pin, F09=phone): "
            f"{json.dumps({k: round(v,2) for k,v in fv.items() if v is not None})}\n"
            "In 2 sentences explain: (1) why this might be a match, (2) what the reviewer should verify."
        )
        ai_explanation = route(TaskType.REVIEWER_EXPLANATION, prompt, max_tokens=120)
    except Exception:
        ai_explanation = None

return {
    ...,
    "ai_explanation": ai_explanation,   # ← NEW
}
```

---

### Layer 5 — Frontend (`frontend/src/`)

**Current approach:** React pages call REST endpoints and display raw JSON data.

| Page | LLM Surface | Implementation |
|---|---|---|
| **Review Queue** | Show a 1-sentence AI teaser per task card — *"Names 87% similar, phone differs"* — so reviewer can triage without opening each task | Render `tasks[i].ai_explanation.split('.')[0]` from the queue endpoint; no extra API call |
| **UBID Detail** | *"Business Health Narrative"* section — plain English status from `explain_activity_status()` | Add `activity_narrative` field to `GET /ubid/{ubid}` response |
| **Search / Lookup** | Natural language search input: *"show dormant textile factories in Peenya with no inspection in 18 months"* | New `POST /api/nl-query` endpoint — LLM converts the sentence to filter parameters (`status=DORMANT`, `nic_prefix=17`, `pin=560058`, `days_since_inspection>540`) |
| **Admin Dashboard** | Anomaly callout: *"3 records with same PAN assigned to different UBIDs — flagged for review"* | Aggregate query + `route(TaskType.ANALYTICS_NARRATION, ...)` — API lane safe |

---

### Integration Priority Matrix

| Layer | File | Opportunity | Effort | Demo Impact | Do When |
|---|---|---|---|---|---|
| Entity Resolution | `scorer.py` | Reviewer plain-English explanation | Low | 🔥 Very High | **Hour 1** |
| Review API | `review.py` GET task | Surface `ai_explanation` in response | Low | 🔥 Very High | **Hour 1** |
| Frontend | Review Queue cards | Show AI teaser per task | Low | High | **Hour 2** |
| Normalisation | `address_parser.py` | LLM fallback for unknown format | Low | High | **Hour 3** |
| Entity Resolution | `feature_extractor.py` | F14 embedding similarity | Medium | High | **Hour 4** |
| Activity Engine | `activity_classifier.py` | Business health narrative | Low | Medium | **Hour 5** |
| Activity Engine | `signal_scorer.py` | Unknown event type mapping | Medium | Medium | Hour 6 |
| Normalisation | `name_normaliser.py` | Ambiguous name fallback | Medium | Medium | Post-hackathon |
| Frontend | NL search | Natural language query | High | High | Post-hackathon |

### Hackathon Sprint Order

```
Hour 1: Add reviewer_explanation to scorer.py → surface in review.py GET /task/{id}
Hour 2: Render ai_explanation teaser on Review Queue cards in React
Hour 3: Plug extract_address_components() into address_parser.py else block
Hour 4: Add F14 sentence-transformer embedding to feature_extractor.py
Hour 5: Add explain_activity_status() call in activity_classifier.py
Hour 6: Wire activity_narrative into UBID Detail page + demo polish
```

> [!IMPORTANT]
> All new `TaskType` values (`NAME_CANONICALISE`, `EVENT_CLASSIFIER`) need to be added to the `TaskType` enum and `_PII_SENSITIVE_TASKS` set in `llm_router.py` before any integration work begins.

---

*Layer map grounded in: `src/normalisation/`, `src/entity_resolution/`, `src/activity_engine/`, `src/api/routers/`, `frontend/src/` — direct code inspection.*
