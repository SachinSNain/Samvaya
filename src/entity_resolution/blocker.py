"""
entity_resolution/blocker.py
Reduces O(n^2) comparisons using targeted exact and near-exact blocking keys.

All keys are designed to be small (< ~50 records per bucket for this dataset).
No broad phonetic bucket (pin+soundex on business name) is used — those explode
to 200+ records per bucket when geocoords are unavailable.

Blocking keys:
  K1  PAN exact                              — strongest identity
  K2  GSTIN exact                            — strong identity
  K3  Phone (last 10 digits) exact           — 59% of cross-dept true pairs
  K4  Phone + registration year              — tighter K3
  K5  Pin + year + owner_prefix(4)           — catches comma/case variations
  K6  Pin + year + owner_suffix(4)           — catches initial vs full-name variants
      e.g. "U. Swamy" (USWA) vs "USHA SWAMY" (USHA) → suffix "WAMY" matches
  K7  Pin + year + soundex(owner_words[0])   — catches phonetic name variants
  K8  H3 geocell + first name token          — only when geocoords available
  K9  NIC 2-digit + pin + owner_prefix       — industry+location+owner
  K10 Pin + year + owner_trigram             — catches "N. Rao" vs "Nirmala Rao":
      letters "NRAO" → trigrams {NRA,RAO} match letters "NIRMALARAO" → {NIR,IRM,RMA,MAL,ALA,LAR,ARA,RAO}
      shared "RAO" puts them in same bucket even when phone blank and 4-char windows miss
"""
import os
import re
import logging
import h3
from collections import defaultdict
from typing import List, Tuple, Set

logger = logging.getLogger(__name__)

# Only K8/K9 use this cap; all other keys have naturally small buckets
MAX_BLOCK_SIZE: int = int(os.getenv("MAX_BLOCK_SIZE", "150"))


# ── Utility functions ────────────────────────────────────────────────────────

def _norm_phone(v) -> str:
    digits = re.sub(r"\D", "", str(v or ""))
    return digits[-10:] if len(digits) >= 10 else ""


def _reg_year(rec: dict) -> str:
    yr = rec.get("registration_year")
    return str(int(yr)) if yr else ""


def _owner_letters(rec: dict) -> str:
    """Strip all non-alpha from owner_name and uppercase."""
    return re.sub(r"[^A-Za-z]", "", str(rec.get("owner_name") or "")).upper()


def _soundex_first_word(name: str) -> str:
    """Soundex of the first alpha-word in a name string."""
    words = re.sub(r"[^A-Za-z ]", " ", name).split()
    if not words:
        return ""
    w = words[0].upper()
    if not w:
        return ""
    # Simple soundex (26 letters → digit codes)
    code = w[0]
    table = str.maketrans("AEHIOUYBFPVCGJKQSXZDTLMNR",
                          "0000000011112222222334556")
    prev = "0"
    for ch in w[1:]:
        c = ch.translate(table)
        if c != "0" and c != prev:
            code += c
        prev = c
        if len(code) == 4:
            break
    return (code + "0000")[:4]


def _first_token(name: str) -> str:
    parts = (name or "").split()
    return parts[0] if parts else ""


def _owner_trigrams(rec: dict) -> set:
    """All 3-char substrings of the alphabetic owner letters.

    "N. Rao" → "NRAO" → {"NRA", "RAO"}
    "Nirmala Rao" → "NIRMALARAO" → {"NIR","IRM","RMA","MAL","ALA","LAR","ARA","RAO"}
    Shared "RAO" is enough to place both in the same bucket.
    Only trigrams from names with ≥4 alpha chars are emitted (avoids single-letter false keys).
    """
    letters = _owner_letters(rec)
    if len(letters) < 4:
        return set()
    return {letters[i:i+3] for i in range(len(letters) - 2)}


# ── Main function ────────────────────────────────────────────────────────────

def generate_candidate_pairs(normalised_records: List[dict]) -> List[Tuple[str, str]]:
    """Returns deduplicated (record_id_a, record_id_b) candidate pairs."""
    pairs: Set[Tuple[str, str]] = set()

    pan_idx         = defaultdict(list)
    gstin_idx       = defaultdict(list)
    phone_idx       = defaultdict(list)
    phone_year_idx  = defaultdict(list)
    pin_year_pfx_idx = defaultdict(list)   # K5 — owner prefix 4
    pin_year_sfx_idx = defaultdict(list)   # K6 — owner suffix 4
    pin_year_sdx_idx = defaultdict(list)   # K7 — soundex of owner first word
    geocell_idx     = defaultdict(list)    # K8
    nic_owner_idx   = defaultdict(list)    # K9
    pin_year_tri_idx = defaultdict(list)   # K10 — owner trigrams

    for rec in normalised_records:
        rid  = rec["record_id"]
        pin  = rec.get("pin_code", "") or ""
        yr   = _reg_year(rec)
        letters = _owner_letters(rec)

        # K1 — PAN
        if rec.get("pan") and rec.get("pan_valid"):
            pan_idx[rec["pan"]].append(rid)

        # K2 — GSTIN
        if rec.get("gstin") and rec.get("gstin_valid"):
            gstin_idx[rec["gstin"]].append(rid)

        # K3/K4 — Phone
        ph = _norm_phone(rec.get("phone"))
        if ph:
            phone_idx[ph].append(rid)
            if yr:
                phone_year_idx[f"{ph}_{yr}"].append(rid)

        # K5 — Pin + year + owner prefix(4)
        if pin and yr and len(letters) >= 4:
            pin_year_pfx_idx[f"{pin}_{yr}_{letters[:4]}"].append(rid)

        # K6 — Pin + year + owner suffix(4)  ("WAMY" catches "Swamy"/"U. Swamy")
        if pin and yr and len(letters) >= 4:
            pin_year_sfx_idx[f"{pin}_{yr}_{letters[-4:]}"].append(rid)

        # K7 — Pin + year + soundex(owner first word)
        if pin and yr and letters:
            sdx = _soundex_first_word(str(rec.get("owner_name") or ""))
            if sdx:
                pin_year_sdx_idx[f"{pin}_{yr}_{sdx}"].append(rid)

        # K8 — H3 geocell + first name token
        lat  = rec.get("lat")
        lng  = rec.get("lng")
        qual = rec.get("geocode_quality")
        if lat is not None and lng is not None and qual in ("HIGH", "MEDIUM"):
            cell = h3.geo_to_h3(lat, lng, resolution=7)
            tok  = _first_token(rec.get("canonical_name", ""))
            if tok:
                geocell_idx[f"{cell}_{tok}"].append(rid)

        # K9 — NIC 2-digit + pin + owner prefix
        nic = str(rec.get("nic_code", "") or "")
        if nic and pin and len(letters) >= 4:
            nic_owner_idx[f"{nic[:2]}_{pin}_{letters[:4]}"].append(rid)

        # K10 — Pin + year + owner trigram (catches "N. Rao" vs "Nirmala Rao")
        if pin and yr:
            for tri in _owner_trigrams(rec):
                pin_year_tri_idx[f"{pin}_{yr}_{tri}"].append(rid)

    # ── Pair generation ───────────────────────────────────────────────────

    def add_all(idx: dict):
        for rids in idx.values():
            n = len(rids)
            if n < 2:
                continue
            for i in range(n):
                for j in range(i + 1, n):
                    pairs.add((min(rids[i], rids[j]), max(rids[i], rids[j])))

    skipped = 0

    def add_capped(idx: dict, label: str):
        nonlocal skipped
        for key, rids in idx.items():
            n = len(rids)
            if n < 2:
                continue
            if n > MAX_BLOCK_SIZE:
                skipped += 1
                logger.debug("Skipping oversized %s bucket '%s' (%d)", label, key, n)
                continue
            for i in range(n):
                for j in range(i + 1, n):
                    pairs.add((min(rids[i], rids[j]), max(rids[i], rids[j])))

    # K1–K7: uncapped (exact or near-exact, buckets are naturally small)
    add_all(pan_idx)
    add_all(gstin_idx)
    add_all(phone_idx)
    add_all(phone_year_idx)
    add_all(pin_year_pfx_idx)
    add_all(pin_year_sfx_idx)
    add_all(pin_year_sdx_idx)

    exact_count = len(pairs)

    # K8–K10: capped (broader keys — trigram buckets can be noisy in dense pin areas)
    add_capped(geocell_idx,    "geocell+token")
    add_capped(nic_owner_idx,  "nic+pin+owner")
    add_capped(pin_year_tri_idx, "pin+year+trigram")

    logger.info(
        "Blocking — near-exact pairs: %d  broad added: %d  total: %d  "
        "skipped oversized: %d  (MAX_BLOCK_SIZE=%d)",
        exact_count, len(pairs) - exact_count, len(pairs), skipped, MAX_BLOCK_SIZE,
    )

    return list(pairs)
