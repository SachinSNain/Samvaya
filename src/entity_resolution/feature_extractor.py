"""
entity_resolution/feature_extractor.py
Computes a 14-feature vector for every candidate pair.
F14 is a multilingual semantic cosine similarity (sentence-transformers).
"""
import math
import os
from rapidfuzz import fuzz, distance
from geopy.distance import geodesic
from src.normalisation.address_parser import PIN_ADJACENCY

# F14 — load embedding model once at import time (~3s on RTX 4050, then cached)
# Disabled when SKIP_SEMANTIC_EMBED=true (bulk training/pipeline runs for speed)
_SKIP_EMBED = os.getenv("SKIP_SEMANTIC_EMBED", "false").lower() == "true"
try:
    if not _SKIP_EMBED:
        from sentence_transformers import SentenceTransformer, util as st_util
        _EMBED_MODEL = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
    else:
        _EMBED_MODEL = None
except ImportError:
    _EMBED_MODEL = None


def extract_features(rec_a: dict, rec_b: dict) -> dict:
    """
    Computes all 13 features for a candidate pair.
    Returns dict with keys F01..F13 and None for missing features.
    """
    features = {}

    name_a = rec_a.get("canonical_name", "")
    name_b = rec_b.get("canonical_name", "")

    # F01 — Name Jaro-Winkler on canonical names
    features["F01"] = distance.JaroWinkler.similarity(
        name_a, name_b) if name_a and name_b else None

    # F02 — Token Set Ratio (handles reordered tokens well)
    features["F02"] = fuzz.token_set_ratio(
        name_a, name_b) / 100.0 if name_a and name_b else None

    # F14 — Multilingual semantic cosine similarity (LOCAL — runs on RTX 4050, no API call)
    if _EMBED_MODEL is not None and name_a and name_b:
        emb = _EMBED_MODEL.encode([name_a, name_b], convert_to_tensor=True)
        features["F14"] = float(st_util.cos_sim(emb[0], emb[1]))
    else:
        features["F14"] = None

    # F03 — Abbreviation match
    features["F03"] = _abbreviation_match_score(name_a, name_b)

    # F04 — PAN match
    features["F04"] = _identifier_match_score(
        rec_a.get("pan"), rec_b.get("pan"))

    # F05 — GSTIN match
    features["F05"] = _identifier_match_score(
        rec_a.get("gstin"), rec_b.get("gstin"))

    # F06 — Pin code match
    pin_a, pin_b = rec_a.get("pin_code"), rec_b.get("pin_code")
    if pin_a and pin_b:
        if pin_a == pin_b:
            features["F06"] = 1.0
        elif pin_b in PIN_ADJACENCY.get(pin_a, []):
            features["F06"] = 0.7
        else:
            features["F06"] = 0.0
    else:
        features["F06"] = None

    # F07 — Haversine geo-distance, normalised to [0, 1] (0 = same spot, 1 = >=2 km apart)
    lat_a, lng_a, qual_a = rec_a.get("lat"), rec_a.get(
        "lng"), rec_a.get("geocode_quality")
    lat_b, lng_b, qual_b = rec_b.get("lat"), rec_b.get(
        "lng"), rec_b.get("geocode_quality")
    if (lat_a is not None and lng_a is not None and lat_b is not None and lng_b is not None and
            qual_a in ("HIGH", "MEDIUM") and qual_b in ("HIGH", "MEDIUM")):
        dist_m = geodesic((lat_a, lng_a), (lat_b, lng_b)).meters
        features["F07"] = min(dist_m / 2000.0, 1.0)
    else:
        features["F07"] = None

    # F08 — Address token Jaccard similarity
    tokens_a = set(rec_a.get("address_tokens", []))
    tokens_b = set(rec_b.get("address_tokens", []))
    if tokens_a and tokens_b:
        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        features["F08"] = intersection / union if union > 0 else 0.0
    else:
        features["F08"] = None

    # F09 — Phone match (normalised to digits only)
    phone_a = ''.join(filter(str.isdigit, str(
        rec_a.get("phone", "") or "")))[-10:]
    phone_b = ''.join(filter(str.isdigit, str(
        rec_b.get("phone", "") or "")))[-10:]
    if phone_a and phone_b:
        if phone_a == phone_b:
            features["F09"] = 1.0
        elif phone_a[-7:] == phone_b[-7:]:  # Last 7 match
            features["F09"] = 0.5
        else:
            features["F09"] = 0.0
    else:
        features["F09"] = None

    # F10 — NIC code compatibility
    nic_a = str(rec_a.get("nic_code", "") or "")
    nic_b = str(rec_b.get("nic_code", "") or "")
    if nic_a and nic_b:
        if nic_a == nic_b:
            features["F10"] = 1.0
        elif nic_a[:2] == nic_b[:2]:
            features["F10"] = 0.7
        elif nic_a[:1] == nic_b[:1]:
            features["F10"] = 0.4
        else:
            features["F10"] = 0.0
    else:
        features["F10"] = None

    # F11 — Owner name similarity
    owner_a = rec_a.get("owner_name", "")
    owner_b = rec_b.get("owner_name", "")
    if owner_a and owner_b:
        features["F11"] = distance.JaroWinkler.similarity(
            owner_a.upper(), owner_b.upper())
    else:
        features["F11"] = None

    # F12 — Same-source flag (duplicate check)
    features["F12"] = 1.0 if rec_a.get(
        "source_system") == rec_b.get("source_system") else 0.0

    # F13 — Registration date proximity: 1.0 = same year, 0.0 = >=10 years apart
    year_a = rec_a.get("registration_year")
    year_b = rec_b.get("registration_year")
    if year_a is not None and year_b is not None:
        features["F13"] = 1.0 - min(abs(int(year_a) - int(year_b)), 10) / 10.0
    else:
        features["F13"] = None

    return features


def _identifier_match_score(id_a, id_b) -> float:
    """
    Returns:
     +1.0  if both present and match
     +0.5  if one or both absent (cannot determine)
      0.0  if both present and absent
     -1.0  if both present and MISMATCH (strong negative signal)
    """
    has_a = bool(id_a and str(id_a).strip())
    has_b = bool(id_b and str(id_b).strip())

    if has_a and has_b:
        return 1.0 if str(id_a).strip().upper() == str(
            id_b).strip().upper() else -1.0
    elif has_a or has_b:
        return 0.5
    else:
        return 0.0


def _abbreviation_match_score(name_a: str, name_b: str) -> float:
    """
    Checks if one name is a valid abbreviation of the other.
    """
    if not name_a or not name_b:
        return 0.0

    words_a = name_a.split()
    words_b = name_b.split()

    if len(name_a) <= 6 and len(words_b) >= 2:
        acronym = ''.join(w[0] for w in words_b if w)
        if name_a == acronym:
            return 1.0
        if name_a in acronym or acronym in name_a:
            return 0.5

    if len(name_b) <= 6 and len(words_a) >= 2:
        acronym = ''.join(w[0] for w in words_a if w)
        if name_b == acronym:
            return 1.0
        if name_b in acronym or acronym in name_b:
            return 0.5

    return 0.0
