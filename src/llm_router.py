"""
src/llm_router.py
Hybrid LLM dispatcher — routes tasks to the correct backend based on PII sensitivity.

Routing policy:
  PII_SENSITIVE  → LOCAL  (Ollama Llama 3.1 8B on RTX 4050, always, no exceptions)
  SAFE           → API    (Gemini 2.5 Flash → Groq → Ollama cascade)
  FORCE_LOCAL_ONLY=true → LOCAL for everything (air-gap demo mode)
"""
import os
import json
import logging
import httpx
from enum import Enum

log = logging.getLogger(__name__)

# ── Task type enum ────────────────────────────────────────────────────────────

class TaskType(Enum):
    # LOCAL LANE — hard-routed, no exceptions
    ADDRESS_NER             = "address_ner"           # Raw address → structured JSON
    REVIEWER_EXPLANATION    = "reviewer_explanation"  # Raw canonical fields → 2-sentence review
    PAN_MISMATCH_NARRATION  = "pan_mismatch"          # PAN hard-reject explanation
    INTRA_DEPT_DUPLICATE    = "intra_dept_duplicate"  # Same-dept duplicate explanation
    NAME_CANONICALISE       = "name_canonicalise"     # Ambiguous name token resolution

    # API LANE — Gemini 2.5 Flash → Groq → Ollama cascade
    REVIEWER_SUMMARY        = "reviewer_summary"       # Scrambled inputs → card summary
    REVIEWER_SCORE_SUMMARY  = "reviewer_score_summary" # Feature scores only → no PII, API-safe
    ACTIVITY_EXPLANATION    = "activity_explanation"   # UBID activity status narration
    ANALYTICS_NARRATION     = "analytics_narration"    # Aggregate dashboard narration
    SYNTHETIC_AUGMENTATION  = "synthetic_augmentation"
    EVENT_CLASSIFIER        = "event_classifier"       # Map unknown event to known type
    NL_QUERY_PARSE          = "nl_query_parse"         # NL string → structured JSON filter params
    SECTOR_BREAKDOWN        = "sector_breakdown"       # Group businesses into sectors


_PII_SENSITIVE_TASKS = {
    TaskType.ADDRESS_NER,
    TaskType.REVIEWER_EXPLANATION,
    TaskType.PAN_MISMATCH_NARRATION,
    TaskType.INTRA_DEPT_DUPLICATE,
    TaskType.NAME_CANONICALISE,
    # REVIEWER_SCORE_SUMMARY intentionally excluded — feature scores only, no raw PII
}

# ── Configuration ─────────────────────────────────────────────────────────────

OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
FORCE_LOCAL_ONLY = os.getenv("FORCE_LOCAL_ONLY", "false").lower() == "true"

# ── Module-level Gemini init (load once at import, not per call) ──────────────

_gemini_model = None
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        log.info("Gemini 2.5 Flash initialised successfully.")
except Exception as _e:
    log.warning(f"Gemini init failed: {_e}. API lane will fall through to Groq.")

# ── Backend callers ───────────────────────────────────────────────────────────

def _call_ollama(prompt: str, system: str = "", max_tokens: int = 512) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": max_tokens,
            "num_gpu": 32,   # All 32 Llama 3.1 8B layers onto RTX 4050 VRAM
        },
    }
    resp = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=30.0
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def _call_gemini(prompt: str, system: str = "", max_tokens: int = 512) -> str:
    if _gemini_model is None:
        raise RuntimeError(
            "Gemini model not initialised (missing GEMINI_API_KEY or import error)"
        )
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    response = _gemini_model.generate_content(
        full_prompt,
        generation_config={"temperature": 0.2, "max_output_tokens": max_tokens},
    )
    return response.text.strip()


def _call_groq(prompt: str, system: str = "", max_tokens: int = 512) -> str:
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
        headers=headers,
        json=payload,
        timeout=20.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

# ── Main dispatcher ───────────────────────────────────────────────────────────

def route(
    task_type: TaskType,
    prompt: str,
    system: str = "",
    max_tokens: int = 512,
) -> str:
    is_pii = task_type in _PII_SENSITIVE_TASKS
    use_local = is_pii or FORCE_LOCAL_ONLY

    if use_local:
        # Hard fail — never send PII to API lane even if Ollama is down
        try:
            return _call_ollama(prompt, system, max_tokens)
        except Exception as e:
            raise RuntimeError(
                f"LOCAL LLM required for PII task '{task_type.value}' "
                f"but Ollama unreachable. Run 'ollama serve'. Error: {e}"
            )

    # API lane: true 3-step cascade — Gemini → Groq → Ollama
    for caller, name in [
        (_call_gemini, "Gemini"),
        (_call_groq,   "Groq"),
        (_call_ollama, "Ollama"),
    ]:
        try:
            return caller(prompt, system, max_tokens)
        except Exception as e:
            log.warning(
                f"[route] {name} failed for task '{task_type.value}': {e}"
            )

    raise RuntimeError(
        f"All LLM backends unavailable for task '{task_type.value}'. "
        "Check Ollama, GEMINI_API_KEY, and GROQ_API_KEY."
    )

# ── Convenience wrappers ──────────────────────────────────────────────────────

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
        clean = (
            result.strip()
            .lstrip("```json")
            .lstrip("```")
            .rstrip("```")
            .strip()
        )
        return json.loads(clean)
    except json.JSONDecodeError:
        return {
            "building": None,
            "street": None,
            "locality": None,
            "area_type": "Unknown",
            "pincode": None,
            "parse_error": True,
        }


def generate_reviewer_summary(
    scrambled_a: dict,
    scrambled_b: dict,
    feature_scores: dict,
    confidence: float,
) -> str:
    """Reviewer card summary. Uses SCRAMBLED inputs — safe for API lane."""
    system = (
        "You are a data analyst reviewing business entity matching "
        "for a government platform."
    )
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
    system = (
        "Explain a business activity classification to a government officer. "
        "Be clear and factual."
    )
    prompt = (
        f"Business UBID {ubid} is classified as {status}.\n"
        "Evidence signals:\n"
        + "\n".join(
            f"  - {e['event_type']}: score={e['contribution']:.3f}, "
            f"{e['days_since']}d ago"
            for e in evidence[:8]
        )
        + "\n\nExplain this in 2 sentences suitable for a government audit report."
    )
    return route(TaskType.ACTIVITY_EXPLANATION, prompt, system, max_tokens=150)


def get_sector_breakdown(businesses: list) -> list:
    """Classify businesses into sectors and aggregate by status. API lane."""
    system = "You are a data analyst. Output ONLY valid JSON."
    prompt = (
        "Classify the following businesses into logical industry sectors (e.g. 'Wearing Apparel', 'Metal Products', 'Retail', 'Food', 'Construction', 'IT/Software', 'Other'). "
        "Then group and count them by sector and status.\n\n"
        f"Businesses:\n{json.dumps(businesses)}\n\n"
        'Output exactly a JSON array of objects, e.g.:\n'
        '[\n  {"name": "Food", "ACTIVE": 2, "DORMANT": 1, "CLOSED": 0}\n]\n'
        'Output ONLY the JSON array.'
    )
    res = route(TaskType.SECTOR_BREAKDOWN, prompt, system, max_tokens=1000)
    try:
        clean = res.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        return []
