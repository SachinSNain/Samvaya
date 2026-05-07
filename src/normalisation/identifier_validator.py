"""
normalisation/identifier_validator.py
Validates and normalises PAN and GSTIN identifiers.

PAN format:  AAAAA9999A  (5 alpha + 4 numeric + 1 alpha)
GSTIN format: 29AAAAA9999A1Z5  (2-digit state + 10-char PAN + 1 entity + Z + 1 checksum)
Karnataka state code: 29
"""
import re

# Common null/placeholder values that mean "no identifier provided"
NULL_VALUES = {'', 'NA', 'N/A', 'NIL', 'NONE', 'NULL', 'NOT APPLICABLE',
               '0', 'NO', 'N.A', 'N.A.', '-', '--', 'NOTAVAILABLE'}

PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
GSTIN_PATTERN = re.compile(
    r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')


def validate_and_normalise_pan(raw_pan) -> dict:
    """
    Returns:
    {
        has_value: bool,   # False if field was blank/null
        valid:     bool,   # True if format is correct
        normalised: str | None,  # cleaned PAN if valid
        raw: str,
    }
    """
    if raw_pan is None:
        return {
            "has_value": False,
            "valid": False,
            "normalised": None,
            "raw": ""}

    pan = str(raw_pan).strip().upper().replace(' ', '').replace('-', '')

    if pan in NULL_VALUES:
        return {
            "has_value": False,
            "valid": False,
            "normalised": None,
            "raw": str(raw_pan)}

    is_valid = bool(PAN_PATTERN.match(pan))
    return {
        "has_value": True,
        "valid": is_valid,
        "normalised": pan if is_valid else None,
        "raw": str(raw_pan),
    }


def validate_and_normalise_gstin(raw_gstin) -> dict:
    """
    Returns:
    {
        has_value:    bool,
        valid:        bool,
        normalised:   str | None,
        state_code:   str | None,   # e.g. "29"
        is_karnataka: bool,
        pan_embedded: str | None,   # positions 2-11 of GSTIN = PAN
        raw:          str,
    }
    """
    if raw_gstin is None:
        return {
            "has_value": False,
            "valid": False,
            "normalised": None,
            "state_code": None,
            "is_karnataka": False,
            "pan_embedded": None,
            "raw": ""}

    gstin = str(raw_gstin).strip().upper().replace(' ', '')

    if gstin in NULL_VALUES:
        return {
            "has_value": False,
            "valid": False,
            "normalised": None,
            "state_code": None,
            "is_karnataka": False,
            "pan_embedded": None,
            "raw": str(raw_gstin)}

    is_valid = bool(GSTIN_PATTERN.match(gstin))
    state_code = gstin[:2] if len(gstin) >= 2 else None
    pan_embedded = gstin[2:12] if len(gstin) >= 12 else None
    is_karnataka = (state_code == "29")

    return {
        "has_value": True,
        "valid": is_valid,
        "normalised": gstin if is_valid else None,
        "state_code": state_code,
        "is_karnataka": is_karnataka,
        "pan_embedded": pan_embedded,
        "raw": str(raw_gstin),
    }
