"""
normalisation/address_parser.py
Parses free-text Karnataka addresses into structured components.

Handles 5 Karnataka address format types:
  1. BBMP ward style   — "#14, 3rd Cross, Peenya Industrial Area, Bengaluru - 560058"
  2. Industrial estate — "Plot No. 14-A, KIADB Industrial Area, Peenya, Bengaluru 560058"
  3. Survey number     — "Sy. No. 247/3, Peenya Industrial Area, 560058"
  4. Landmark-based    — "Near SBI Bank, 3rd Main, Rajajinagar, Bengaluru"
  5. Minimal           — "Peenya Industrial Area, Bengaluru - 560058"
"""
import re
from dataclasses import dataclass, field
from typing import Optional

# ─── Karnataka pin code metadata ─────────────────────────────────────────────
KARNATAKA_PIN_CODES = {
    "560058": {"locality": "Peenya", "district": "Bengaluru Urban", "taluk": "Bengaluru North"},
    "560073": {"locality": "Rajajinagar", "district": "Bengaluru Urban", "taluk": "Bengaluru North"},
    "560032": {"locality": "Yeshwanthpur", "district": "Bengaluru Urban", "taluk": "Bengaluru North"},
    "560022": {"locality": "Peenya", "district": "Bengaluru Urban", "taluk": "Bengaluru North"},
    "560010": {"locality": "Rajajinagar", "district": "Bengaluru Urban", "taluk": "Bengaluru North"},
    "560086": {"locality": "Vijayanagar", "district": "Bengaluru Urban", "taluk": "Bengaluru South"},
    "560040": {"locality": "Basaveshwaranagar", "district": "Bengaluru Urban", "taluk": "Bengaluru North"},
    "560057": {"locality": "Peenya", "district": "Bengaluru Urban", "taluk": "Bengaluru North"},
}

# Adjacency map for Feature F06 (pin code similarity)
PIN_ADJACENCY = {
    "560058": ["560057", "560022", "560032", "560073"],
    "560073": ["560010", "560086", "560058", "560040"],
    "560032": ["560058", "560022", "560057"],
    "560022": ["560058", "560032", "560057"],
}

INDUSTRIAL_AREA_KEYWORDS = [
    "KIADB", "KSSIDC", "PEENYA", "BOMMASANDRA", "WHITEFIELD",
    "JIGANI", "ELECTRONICS CITY", "INDUSTRIAL AREA", "INDL AREA",
    "INDUSTRIAL ESTATE", "INDL ESTATE", "INDUSTRIAL LAYOUT",
]

ADDRESS_STOP_WORDS = {
    "THE", "AND", "OF", "IN", "AT", "NO", "ST", "TH", "RD", "ND",
    "ROAD", "MAIN", "CROSS", "BENGALURU", "BANGALORE", "KARNATAKA", "INDIA",
}


@dataclass
class ParsedAddress:
    building: Optional[str] = None
    street: Optional[str] = None
    locality: Optional[str] = None
    landmark: Optional[str] = None
    ward: Optional[str] = None
    industrial_area: Optional[str] = None
    survey_plot_no: Optional[str] = None
    taluk: Optional[str] = None
    district: Optional[str] = None
    pin_code: Optional[str] = None
    address_type: str = "unknown"
    # 'bbmp' / 'industrial' / 'survey' / 'landmark' / 'minimal' / 'unknown'
    address_tokens: list = field(default_factory=list)


def parse_address(raw_address: str) -> ParsedAddress:
    """
    Parse a raw free-text Karnataka address into structured components.
    Returns a ParsedAddress dataclass instance.
    """
    if not raw_address or not str(raw_address).strip():
        return ParsedAddress()

    addr = str(raw_address).upper().strip()
    parsed = ParsedAddress()

    # 1. Extract and remove pin code (always 6 digits)
    pin_match = re.search(r'\b(\d{6})\b', addr)
    if pin_match:
        parsed.pin_code = pin_match.group(1)
        addr = addr.replace(pin_match.group(0), ' ').strip()

    # 2. Detect address type and parse accordingly
    if re.search(r'\bSY\.?\s*NO\.?\b|\bSURVEY\s+NO\b', addr, re.IGNORECASE):
        parsed.address_type = "survey"
        survey_match = re.search(
            r'SY\.?\s*NO\.?\s*([\d/]+)', addr, re.IGNORECASE)
        if survey_match:
            parsed.survey_plot_no = survey_match.group(1)
        _extract_locality(addr, parsed)

    elif re.search(r'#\s*\d+|(?<!PLOT\s)NO\.\s*\d+|\d+\s*,\s*\d+\s*(ST|ND|RD|TH)', addr):
        parsed.address_type = "bbmp"
        building_match = re.search(r'#\s*([\w\-/]+)', addr)
        if building_match:
            parsed.building = building_match.group(1)
        cross_match = re.search(
            r'(\d+)\s*(ST|ND|RD|TH)\s*(CROSS|MAIN|ROAD)',
            addr,
            re.IGNORECASE)
        if cross_match:
            parsed.street = f"{cross_match.group(1)}{cross_match.group(2)} {cross_match.group(3)}"
        _extract_locality(addr, parsed)

    elif any(kw in addr for kw in INDUSTRIAL_AREA_KEYWORDS):
        parsed.address_type = "industrial"
        plot_match = re.search(
            r'PLOT\s*(?:NO\.?)?\s*([\w\-/]+)',
            addr,
            re.IGNORECASE)
        if plot_match:
            parsed.building = "Plot " + plot_match.group(1)
        for kw in INDUSTRIAL_AREA_KEYWORDS:
            if kw in addr:
                parsed.industrial_area = kw
                break
        _extract_locality(addr, parsed)

    elif re.search(r'\bNEAR\b|\bOPP\.?\b|\bOPPOSITE\b|\bBEHIND\b|\bADJACENT\b', addr, re.IGNORECASE):
        parsed.address_type = "landmark"
        landmark_match = re.search(
            r'(?:NEAR|OPP\.?|OPPOSITE|BEHIND|ADJACENT\s+TO)\s+(.+?)(?:,|$)',
            addr, re.IGNORECASE
        )
        if landmark_match:
            parsed.landmark = landmark_match.group(1).strip()
        _extract_locality(addr, parsed)

    else:
        # LLM fallback — disabled during bulk/training runs via env var
        import os
        if os.getenv("SKIP_LLM_PARSING", "false").lower() != "true":
            try:
                from src.llm_router import extract_address_components
                llm_result = extract_address_components(addr)
                parsed.address_type = llm_result.get("area_type", "unknown").lower()
                parsed.locality = llm_result.get("locality") or parsed.locality
                if not parsed.pin_code:
                    parsed.pin_code = llm_result.get("pincode")
            except Exception:
                parsed.address_type = "minimal"
        else:
            parsed.address_type = "minimal"
        _extract_locality(addr, parsed)

    # 3. Extract ward number
    ward_match = re.search(r'WARD\s*(?:NO\.?)?\s*(\d+)', addr, re.IGNORECASE)
    if ward_match:
        parsed.ward = ward_match.group(1)

    # 4. Extract taluk
    taluk_match = re.search(r'TALUK\s*:?\s*(\w+)', addr, re.IGNORECASE)
    if taluk_match:
        parsed.taluk = taluk_match.group(1)

    # 5. Fill district/taluk/locality from pin code metadata if still empty
    if parsed.pin_code and parsed.pin_code in KARNATAKA_PIN_CODES:
        meta = KARNATAKA_PIN_CODES[parsed.pin_code]
        parsed.district = parsed.district or meta["district"]
        parsed.taluk = parsed.taluk or meta["taluk"]
        parsed.locality = parsed.locality or meta["locality"]

    # 6. Generate address tokens for Jaccard similarity (Feature F08)
    tokens = re.sub(r'[^\w\s]', ' ', addr).split()
    parsed.address_tokens = [
        t for t in tokens
        if len(t) > 2 and t not in ADDRESS_STOP_WORDS and not t.isdigit()
    ]

    return parsed


def _extract_locality(addr: str, parsed: ParsedAddress):
    """
    Heuristic: if not already set, take the last non-digit, non-empty
    comma-separated component as the locality.
    """
    if parsed.locality:
        return
    parts = [p.strip() for p in addr.split(',') if p.strip()]
    for part in reversed(parts):
        if part and not re.match(r'^\d+$', part) and len(part) > 2:
            # Skip if it's just BENGALURU or KARNATAKA
            if part not in {"BENGALURU", "BANGALORE", "KARNATAKA", "INDIA"}:
                parsed.locality = part
                break
