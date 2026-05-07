"""
normalisation/name_normaliser.py
Converts raw business names into a canonical comparison form + phonetic keys.

Pipeline:
  1. Uppercase + strip
  2. Transliterate Kannada → Latin (if Kannada script detected)
  3. Normalise city variants (Bangalore → BENGALURU)
  4. Strip legal suffixes (Pvt Ltd, LLP, & Co., etc.)
  5. Expand abbreviations (Inds → INDUSTRIES, Mfg → MANUFACTURING)
  6. Remove punctuation + collapse whitespace
  7. Generate Soundex + Double-Metaphone phonetic keys from first significant word
"""
import re
import unicodedata
from metaphone import doublemetaphone
import jellyfish

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    _INDIC_AVAILABLE = True
except ImportError:
    _INDIC_AVAILABLE = False

# ─── Legal suffix patterns ───────────────────────────────────────────────────
# All variants that should be stripped from the end (or anywhere) of a name.
LEGAL_SUFFIX_PATTERNS = [
    r'\bPRIVATE\s+LIMITED\b', r'\bPVT\.?\s*LTD\.?\b', r'\bP\.?\s*LTD\.?\b',
    r'\bLIMITED\b', r'\bLTD\.?\b',
    r'\bLIMITED\s+LIABILITY\s+PARTNERSHIP\b', r'\bLLP\b', r'\bL\.L\.P\.?\b',
    r'\bPROPRIETORSHIP\b', r'\bPROPR?\.?\b',
    r'\bFIRM\b',
    r'\bCO-OPERATIVE\b', r'\bCO-OP\b',
    r'\bSOCIETY\b', r'\bSOC\.?\b',
    r'\bENTERPRISES?\b',
    r'\bINDUSTRIES?\b(?!\s+\w)',  # only as terminal suffix
    r'\b&\s*CO\.?\b', r'\b&\s*SONS?\b',
    r'\bAND\s+COMPANY\b', r'\bAND\s+CO\.?\b',
    r'\bINC\.?\b', r'\bCORP\.?\b', r'\bCORPORATION\b',
    r'\bPVT\b', r'\bPRIVATE\b',
    r'\bAND\s+ASSOCIATES?\b', r'\b&\s*ASSOCIATES?\b',
    r'\bCONSULTANTS?\b(?!\s+\w)',
    r'\bSERVICES?\b(?!\s+\w)',
    r'\bSOLUTIONS?\b(?!\s+\w)',
    r'\bGROUP\b(?!\s+\w)',
]

# ─── Abbreviation expansions ─────────────────────────────────────────────────
ABBREVIATION_EXPANSIONS = {
    # Industry
    "INDS": "INDUSTRIES", "IND": "INDUSTRIES",
    "MFG": "MANUFACTURING", "MFRS": "MANUFACTURERS", "MFGR": "MANUFACTURER",
    "ENG": "ENGINEERING", "ENGG": "ENGINEERING",
    "TRD": "TRADING", "TRDG": "TRADING",
    "EXPTS": "EXPORTS", "EXP": "EXPORTS",
    "INTL": "INTERNATIONAL", "INT": "INTERNATIONAL",
    "AGRO": "AGRO",
    "CHEM": "CHEMICALS",
    "PHARMA": "PHARMACEUTICALS",
    "TECH": "TECHNOLOGIES", "TECHNO": "TECHNOLOGIES",
    "MKTG": "MARKETING", "MKT": "MARKETING",
    "ASSOC": "ASSOCIATION", "ASSN": "ASSOCIATION",
    "CORP": "CORPORATION",
    "GOVT": "GOVERNMENT", "GOV": "GOVERNMENT",
    # City / Place
    "BLR": "BENGALURU", "BLORE": "BENGALURU", "BANGALORE": "BENGALURU",
    "KA": "KARNATAKA", "KARN": "KARNATAKA",
    # Common business words
    "INFRA": "INFRASTRUCTURE",
    "CONST": "CONSTRUCTION",
    "CONSTR": "CONSTRUCTION",
    "AUTO": "AUTOMOBILES",
    "ELEC": "ELECTRICAL",
    "ELECTRO": "ELECTRONICS",
    "GRANITS": "GRANITES",
    "GRANTZ": "GRANITES",
}

# ─── City name normalisation ────────────────────────────────────────────
CITY_NORMALISATION = {
    "BANGALORE": "BENGALURU",
    "B'LORE": "BENGALURU",
    "BLR": "BENGALURU",
    "BLORE": "BENGALURU",
    "MANGALORE": "MANGALURU",
    "MYSORE": "MYSURU",
    "BELGAUM": "BELAGAVI",
    "GULBARGA": "KALABURAGI",
    "HUBLI": "HUBBALLI",
    "DHARWAD": "DHARWAD",
    "SHIMOGA": "SHIVAMOGGA",
    "TUMKUR": "TUMAKURU",
    "HASSAN": "HASSAN",
}

# ─── Phonetic stop-words (don't use these as the phonetic key) ───────────────
PHONETIC_STOPWORDS = {
    "THE", "AND", "OF", "IN", "AT", "SRI", "SHRI", "SMT", "MR", "MRS",
    "NEW", "OLD", "GOOD", "BEST", "GREAT",
}


def canonicalise_name(raw_name: str) -> dict:
    """
    Takes a raw business name and returns:
    {
        "canonical":  cleaned comparison string,
        "soundex":    Soundex key of first significant word,
        "metaphone":  (primary, secondary) Double-Metaphone keys,
        "original":   original input, uppercased,
    }
    """
    if not raw_name or not str(raw_name).strip():
        return {
            "canonical": "",
            "soundex": "",
            "metaphone": (
                "",
                ""),
            "original": ""}

    # Step 1: Uppercase + strip
    name = str(raw_name).upper().strip()
    original = name

    # Step 2: Transliterate Kannada script if present
    if _INDIC_AVAILABLE and any('\u0C80' <= c <= '\u0CFF' for c in name):
        try:
            name = transliterate(name, sanscript.KANNADA, sanscript.IAST)
            name = _iast_to_simple_latin(name).upper()
        except Exception:
            pass  # Fall through with original if transliteration fails

    # Step 3: Normalise city names
    for variant, canonical_city in CITY_NORMALISATION.items():
        name = re.sub(r'\b' + re.escape(variant) + r'\b', canonical_city, name)

    # Step 4: Strip legal suffixes (repeat twice to catch nested e.g. "Pvt Ltd
    # & Co.")
    for _ in range(2):
        for pattern in LEGAL_SUFFIX_PATTERNS:
            name = re.sub(pattern, ' ', name, flags=re.IGNORECASE)

    # Step 5: Expand abbreviations (word-boundary match)
    words = re.sub(r'[^\w\s]', ' ', name).split()
    expanded = []
    for word in words:
        clean_word = re.sub(r'[^A-Z0-9]', '', word)
        expanded.append(ABBREVIATION_EXPANSIONS.get(clean_word, word))
    name = ' '.join(expanded)

    # Step 6: Remove remaining punctuation + collapse whitespace
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()

    # Step 7: Phonetic keys from first significant word
    words_final = [w for w in name.split(
    ) if w not in PHONETIC_STOPWORDS and len(w) > 1]
    first_word = words_final[0] if words_final else (
        name.split()[0] if name.split() else "")

    soundex_key = jellyfish.soundex(first_word) if first_word else ""
    metaphone_key = doublemetaphone(first_word) if first_word else ("", "")

    return {
        "canonical": name,
        "soundex": soundex_key,
        "metaphone": metaphone_key,
        "original": original,
    }


def _iast_to_simple_latin(iast_text: str) -> str:
    """Strip diacritics from IAST transliteration to get plain ASCII."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', iast_text)
        if unicodedata.category(c) != 'Mn'
    )
