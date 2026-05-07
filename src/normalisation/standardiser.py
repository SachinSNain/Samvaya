"""
normalisation/standardiser.py
Orchestrator — runs all normalisation modules in the correct order on a single raw record.

Input:  one raw department record dict (from any of the 4 departments)
Output: one standardised record in the unified internal schema

This is the ONLY file the pipeline calls for normalisation.
"""
from .name_normaliser import canonicalise_name
from .address_parser import parse_address
from .identifier_validator import validate_and_normalise_pan, validate_and_normalise_gstin
from .geocoder import geocode_address

# Fields that mean "business name" across different source tables
_NAME_FIELDS = ["business_name", "factory_name", "employer_name", "unit_name"]


def standardise_record(raw_record: dict, skip_geocoding: bool = False) -> dict:
    """
    Takes a raw record dict from any department table and returns a
    unified standardised dict suitable for blocking + feature extraction.

    skip_geocoding=True is useful for unit tests / fast local runs without Nominatim.

    Output schema:
    {
        record_id:       str,   — source_system + ":" + primary_key
        source_system:   str,
        primary_key:     str,   — se_reg_no / factory_licence_no / etc.
        entity_id:       str,   — ground truth (NEVER used by pipeline)

        # Business name
        raw_name:        str,
        canonical_name:  str,
        soundex:         str,
        metaphone:       tuple,

        # Identifiers
        pan:             str | None,
        pan_valid:       bool,
        gstin:           str | None,
        gstin_valid:     bool,
        pan_has_value:   bool,
        gstin_has_value: bool,

        # Address
        raw_address:     str,
        pin_code:        str | None,
        address_tokens:  list[str],
        address_type:    str,

        # Geocoordinates
        lat:             float | None,
        lng:             float | None,
        geocode_quality: str,    — HIGH / MEDIUM / LOW / FAILED

        # Other fields (preserved as-is for feature extraction)
        owner_name:      str,
        phone:           str,
        nic_code:        str | None,
        registration_year: int | None,
        status:          str,
    }
    """
    rec = raw_record  # alias for readability

    # ── Identify source system and primary key ────────────────────────────
    source_system = rec.get("source_system", "unknown")
    primary_key = _get_primary_key(rec, source_system)
    record_id = f"{source_system}:{primary_key}"

    # ── Business name ─────────────────────────────────────────────────────
    raw_name = ""
    for field in _NAME_FIELDS:
        if rec.get(field):
            raw_name = str(rec[field])
            break

    name_result = canonicalise_name(raw_name)

    # ── Identifiers ───────────────────────────────────────────────────────
    pan_result = validate_and_normalise_pan(rec.get("pan"))
    gstin_result = validate_and_normalise_gstin(rec.get("gstin"))

    # ── Address ───────────────────────────────────────────────────────────
    raw_address = str(rec.get("address", "") or "")
    # Prefer explicit pin_code field; fall back to what was in address text
    pin_code_field = str(rec.get("pin_code", "") or "")
    parsed_addr = parse_address(raw_address)
    if pin_code_field and not parsed_addr.pin_code:
        parsed_addr.pin_code = pin_code_field

    # ── Geocoding ─────────────────────────────────────────────────────────
    if skip_geocoding:
        geo = {"lat": None, "lng": None, "quality": "FAILED"}
    else:
        geo = geocode_address(parsed_addr)

    # ── Registration year ─────────────────────────────────────────────────
    reg_year = None
    reg_date_raw = rec.get("registration_date")
    if reg_date_raw:
        try:
            reg_year = int(str(reg_date_raw)[:4])
        except (ValueError, TypeError):
            pass

    return {
        # Identity
        "record_id": record_id,
        "source_system": source_system,
        "primary_key": primary_key,
        # ground truth — pipeline ignores this
        "entity_id": rec.get("entity_id"),

        # Name
        "raw_name": raw_name,
        "canonical_name": name_result["canonical"],
        "soundex": name_result["soundex"],
        "metaphone": name_result["metaphone"],

        # Identifiers
        "pan": pan_result["normalised"],
        "pan_valid": pan_result["valid"],
        "pan_has_value": pan_result["has_value"],
        "gstin": gstin_result["normalised"],
        "gstin_valid": gstin_result["valid"],
        "gstin_has_value": gstin_result["has_value"],

        # Address
        "raw_address": raw_address,
        "pin_code": parsed_addr.pin_code or pin_code_field or None,
        "address_tokens": parsed_addr.address_tokens,
        "address_type": parsed_addr.address_type,
        "locality": parsed_addr.locality,
        "industrial_area": parsed_addr.industrial_area,

        # Geocoordinates
        "lat": geo["lat"],
        "lng": geo["lng"],
        "geocode_quality": geo["quality"],

        # Other fields
        "owner_name": str(rec.get("owner_name") or ""),
        "phone": str(rec.get("phone") or ""),
        "nic_code": str(rec.get("nic_code") or ""),
        "registration_year": reg_year,
        "status": str(rec.get("status") or ""),
    }


# ─── Source-system primary key mapping ───────────────────────────────────────

_PRIMARY_KEY_FIELDS = {
    "shop_establishment": "se_reg_no",
    "factories": "factory_licence_no",
    "labour": "employer_code",
    "kspcb": "consent_order_no",
}


def _get_primary_key(rec: dict, source_system: str) -> str:
    field = _PRIMARY_KEY_FIELDS.get(source_system)
    if field and rec.get(field):
        return str(rec[field])
    # Fallback: find the first non-empty key that looks like a primary key
    for k, v in rec.items():
        if v and any(
            kw in k for kw in (
                "reg_no",
                "licence_no",
                "code",
                "order_no")):
            return str(v)
    return "UNKNOWN"
