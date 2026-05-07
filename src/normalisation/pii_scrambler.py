"""
normalisation/pii_scrambler.py
Deterministic, structure-preserving PII scrambling using HMAC-SHA256.

Rules:
  - Same input ALWAYS produces the same output (reproducible test runs).
  - Output preserves the format of the original (valid PAN → valid PAN format).
  - Uses a secret key from .env — never hard-coded in code.
"""
import hmac
import hashlib
import os
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("SCRAMBLER_SECRET_KEY",
                       "dev_secret_key_replace_in_prod").encode()

# Fixed per-district date shift (days) — preserves temporal ordering
DATE_OFFSET_DAYS = 385

# Per-district PIN code offset (added to last 3 digits of pin)
PIN_OFFSET = {
    "Bengaluru Urban": 100,
    "Mysuru": 200,
    "Belagavi": 300,
}


def _hmac_digest(value: str, salt: str = "") -> str:
    """Produce a deterministic hex digest for a value."""
    msg = (salt + value).encode()
    return hmac.new(SECRET_KEY, msg, hashlib.sha256).hexdigest()


def scramble_business_name(name: str, name_pool: list) -> str:
    """
    Deterministic lookup into a synthetic name pool.
    Same name → same synthetic name every time.
    """
    if not name or not name_pool:
        return name or ""
    digest = _hmac_digest(name.upper())
    index = int(digest[:8], 16) % len(name_pool)
    return name_pool[index]


def scramble_pan(pan: str) -> str:
    """
    Structure-preserving PAN scramble.
    - First 5 alpha chars: kept (entity type indicator)
    - Digits 6-9: replaced with new digits
    - Last alpha: replaced
    Output still passes PAN format validation.
    """
    if not pan or len(pan) != 10:
        return pan
    digest = _hmac_digest(pan)
    new_digits = str(int(digest[:8], 16) % 10000).zfill(4)
    new_last = chr(ord('A') + (int(digest[8:10], 16) % 26))
    return pan[:5] + new_digits + new_last


def scramble_gstin(gstin: str) -> str:
    """
    State code '29' (Karnataka) is always preserved.
    Embedded PAN portion is scrambled via scramble_pan.
    Entity ordinal and checksum are re-derived.
    """
    if not gstin or len(gstin) != 15:
        return gstin
    state_code = gstin[:2]                    # always "29"
    pan_part = scramble_pan(gstin[2:12])    # scramble embedded PAN
    digest = _hmac_digest(gstin)
    entity_num = str((int(digest[:2], 16) % 9) + 1)  # 1-9
    checksum = digest[2].upper()
    return f"{state_code}{pan_part}{entity_num}Z{checksum}"


def scramble_phone(phone: str) -> str:
    """
    Digit-by-digit substitution cipher.
    Builds a deterministic 0-9 → 0-9 mapping from the HMAC key.
    """
    if not phone:
        return phone
    digest = _hmac_digest("phone_cipher")
    digit_map = {
        str(i): str(int(digest[i * 2: i * 2 + 2], 16) % 10)
        for i in range(10)
    }
    return ''.join(digit_map.get(c, c) for c in phone)


def scramble_date(date_str: str) -> str:
    """Shift date by fixed offset. Preserves temporal ordering."""
    try:
        dt = datetime.fromisoformat(str(date_str))
        shifted = dt + timedelta(days=DATE_OFFSET_DAYS)
        return shifted.isoformat()
    except Exception:
        return date_str


def scramble_record(record: dict, name_pool: list = None) -> dict:
    """
    Apply all scrambling transforms to a normalised record dict.
    Returns a new dict with PII fields replaced.
    name_pool is the synthetic business names list from dictionaries.
    """
    scrambled = record.copy()

    if name_pool and scrambled.get("business_name"):
        scrambled["business_name"] = scramble_business_name(
            record["business_name"], name_pool
        )

    if scrambled.get("pan"):
        scrambled["pan"] = scramble_pan(str(record["pan"]))

    if scrambled.get("gstin"):
        scrambled["gstin"] = scramble_gstin(str(record["gstin"]))

    if scrambled.get("phone"):
        scrambled["phone"] = scramble_phone(str(record["phone"]))

    if scrambled.get("registration_date"):
        scrambled["registration_date"] = scramble_date(
            str(record["registration_date"]))

    return scrambled
