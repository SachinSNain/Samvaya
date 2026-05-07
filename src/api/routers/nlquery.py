"""
api/routers/nlquery.py
Natural-language query endpoint — converts plain English to structured filter params
and delegates to the existing activity query logic.

Example: "Show dormant textile factories in 560058 with no inspection in 18 months"
→ {"status": "DORMANT", "pincode": "560058", "no_inspection_days": 540}
"""
import json
import logging
import re

log = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from src.database.connection import get_db

router = APIRouter()

# Valid status values the activity engine understands
_VALID_STATUSES = {"ACTIVE", "DORMANT", "CLOSED_SUSPECTED", "CLOSED_CONFIRMED", "CLOSED"}


def _extract_json(raw: str) -> dict:
    """
    Robustly pull the first JSON object out of any LLM response,
    regardless of markdown fences or surrounding explanation text.
    """
    # 1. Try direct parse first
    try:
        return json.loads(raw.strip())
    except Exception:
        pass

    # 2. Find the first '{' and scan forward to the matching '}'
    start = raw.find('{')
    if start != -1:
        depth = 0
        for i, ch in enumerate(raw[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start:i + 1])
                    except Exception:
                        break

    raise ValueError(f"No valid JSON object found in: {raw!r}")


def _keyword_fallback_parse(query: str) -> dict:
    """
    Pure regex/keyword fallback parser — runs instantly, no LLM required.
    Used when all LLM backends fail (rate limits, network, etc.).
    """
    q = query.lower()
    params: dict = {"status": None, "pincode": None, "sector_nic": None, "no_inspection_days": None}

    # --- Status detection ---
    if any(w in q for w in ["closed", "closure", "shut down", "shut", "closed business", "closed businesses"]):
        if "confirmed" in q:
            params["status"] = "CLOSED_CONFIRMED"
        elif "suspected" in q:
            params["status"] = "CLOSED_SUSPECTED"
        else:
            params["status"] = "CLOSED"
    elif any(w in q for w in ["active", "operating", "running", "open"]):
        params["status"] = "ACTIVE"
    elif any(w in q for w in ["dormant", "inactive", "idle", "not active"]):
        params["status"] = "DORMANT"

    # --- Pincode detection (6-digit number) ---
    pincode_match = re.search(r'\b(\d{6})\b', query)
    if pincode_match:
        params["pincode"] = pincode_match.group(1)

    # --- No-inspection-days detection ---
    # e.g. "18 months", "2 years", "540 days"
    insp_match = re.search(r'(\d+)\s*(month|year|day)', q)
    if insp_match and any(w in q for w in ["no inspection", "without inspection", "no insp"]):
        val = int(insp_match.group(1))
        unit = insp_match.group(2)
        if unit.startswith("month"):
            val = val * 30
        elif unit.startswith("year"):
            val = val * 365
        params["no_inspection_days"] = val

    # --- Sector NIC detection ---
    sector_map = {
        "apparel": "14", "garment": "14", "textile": "14", "wearing": "14",
        "metal": "25", "fabricated": "25",
        "retail": "47", "shop": "47",
        "wholesale": "46",
        "food": "10", "beverage": "10",
        "software": "62", "it ": "62", "tech": "62",
        "construction": "43", "building": "43",
        "manufacturing": "32", "factory": "32", "factories": "32",
    }
    for keyword, nic in sector_map.items():
        if keyword in q:
            params["sector_nic"] = nic
            break

    return params


@router.post("/nl-query")
def natural_language_query(
    query: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """
    Accepts a natural-language business query and returns matching UBIDs.
    Tries Gemini → Groq (API lane) first, falls back to keyword parser.
    """
    from src.llm_router import route, TaskType

    parse_prompt = (
        f"Convert this business query to a JSON object.\n"
        f"Query: \"{query}\"\n\n"
        "Rules:\n"
        "- Output ONLY a JSON object, no explanation, no markdown.\n"
        "- Keys: status, pincode, sector_nic, no_inspection_days\n"
        "- status must be one of: ACTIVE, DORMANT, CLOSED_SUSPECTED, CLOSED_CONFIRMED, CLOSED, or null. Use CLOSED when the user asks for all closed businesses.\n"
        "- pincode must be a 6-digit string or null\n"
        "- sector_nic must be a 2-digit NIC code (e.g. '14' for apparel, '25' for metal, '43' for construction, '10' for food, '32' for manufacturing, '62' for software) or null\n"
        "- no_inspection_days must be an integer (e.g. 18 months -> 540). Must be null if not specified.\n\n"
        'Example: {"status": "DORMANT", "pincode": "560058", "sector_nic": "14", "no_inspection_days": 540}'
    )

    params = None
    llm_used = "keyword_fallback"

    # Try LLM first (Gemini → Groq cascade)
    try:
        raw = route(TaskType.NL_QUERY_PARSE, parse_prompt, max_tokens=200)
        params = _extract_json(raw)
        llm_used = "llm"
    except Exception as e:
        log.warning(f"[nl-query] All LLM backends failed: {e}. Falling back to keyword parser.")
        params = _keyword_fallback_parse(query)

    # Sanitise params
    status = params.get("status")
    if status and status not in _VALID_STATUSES:
        status = None

    pincode = params.get("pincode")
    if pincode:
        pincode = str(pincode).strip()
        if not re.match(r'^\d{6}$', pincode):
            pincode = None

    sector_nic = params.get("sector_nic")
    if sector_nic:
        sector_nic = str(sector_nic).strip()

    no_inspection_days = params.get("no_inspection_days")
    if no_inspection_days is not None:
        try:
            no_inspection_days = int(no_inspection_days)
        except Exception:
            no_inspection_days = None

    from src.api.routers.activity import _run_activity_query
    result = _run_activity_query(
        status=status,
        pincode=pincode,
        sector_nic=sector_nic,
        no_inspection_days=no_inspection_days,
        db=db,
    )
    result["_parsed_by"] = llm_used
    result["query"] = {
        "status": status,
        "pincode": pincode,
        "sector_nic": sector_nic,
        "no_inspection_days": no_inspection_days,
    }
    return result
