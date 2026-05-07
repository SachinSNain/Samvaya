"""
Ground-truth business entity generator.
Produces 5,000 canonical entities before any departmental variation is applied.
"""
import random
import string
from dataclasses import dataclass, field
from typing import Optional

from .dictionaries.karnataka_business_names import (
    BUSINESS_PREFIXES, BUSINESS_CORE, LEGAL_SUFFIXES,
    OWNER_FIRST_NAMES, OWNER_LAST_NAMES,
)
from .dictionaries.karnataka_street_names import (
    STREET_NAMES, BUILDING_TYPES, PIN_CODE_LOCALITY_MAP,
)
from .dictionaries.nic_codes import NIC_HIERARCHY, NIC_DISTRIBUTION
from .dictionaries.pin_codes import PIN_CODES, PIN_CODE_METADATA

ENTITY_TYPE_DISTRIBUTION = {
    "factory": 0.35,
    "shop": 0.40,
    "service": 0.20,
    "home_based": 0.05,
}

STATUS_DISTRIBUTION = {
    "active": 0.75,
    "dormant": 0.15,
    "closed": 0.05,
    "seasonal_active": 0.05,
}

SEASONAL_MONTHS = [10, 11, 12, 1, 2, 3]


@dataclass
class GroundTruthEntity:
    entity_id: str
    true_name: str
    true_pan: Optional[str]
    true_gstin: Optional[str]
    true_address: dict
    true_lat: float
    true_lng: float
    nic_code_2digit: str
    nic_code_4digit: str
    owner_name: str
    phone: str
    registration_year: int
    entity_type: str
    is_seasonal: bool
    seasonal_months: list
    ground_truth_status: str
    closure_date: Optional[str]


def _weighted_choice(distribution: dict) -> str:
    keys = list(distribution.keys())
    weights = list(distribution.values())
    return random.choices(keys, weights=weights, k=1)[0]


def _generate_pan() -> str:
    letters = string.ascii_uppercase
    return (
        "".join(random.choices(letters, k=5))
        + "".join(random.choices(string.digits, k=4))
        + random.choice(letters)
    )


def _pan_to_gstin(pan: str, state_code: str = "29") -> str:
    return f"{state_code}{pan}1Z5"


def _generate_phone() -> str:
    prefixes = [
        "98450",
        "98440",
        "99000",
        "99001",
        "80950",
        "80951",
        "97310",
        "63660",
        "70220"]
    return random.choice(prefixes) + \
        "".join(random.choices(string.digits, k=5))


def _generate_business_name(entity_type: str) -> str:
    prefix = random.choice(BUSINESS_PREFIXES)
    core = random.choice(BUSINESS_CORE)
    suffix = random.choice(LEGAL_SUFFIXES)
    if entity_type == "home_based":
        suffix = random.choice(["", "", "Enterprises", "& Co."])
    name = f"{prefix} {core}"
    if suffix:
        name = f"{name} {suffix}"
    return name


def _generate_address(pin_code: str) -> dict:
    meta = PIN_CODE_METADATA[pin_code]
    localities = PIN_CODE_LOCALITY_MAP[pin_code]
    building_type = random.choice(BUILDING_TYPES)
    building_number = f"{random.randint(1, 200)}-{'ABCDE'[random.randint(0, 4)]}"
    street = random.choice(STREET_NAMES)
    locality = random.choice(localities)
    return {
        "building": f"{building_type} {building_number}",
        "street": street,
        "locality": locality,
        "ward": None,
        "taluk": meta["taluk"],
        "district": meta["district"],
        "pin_code": pin_code,
        "industrial_area": meta["industrial_area"],
    }


def _generate_coords(pin_code: str) -> tuple:
    meta = PIN_CODE_METADATA[pin_code]
    lat = round(random.uniform(*meta["lat_range"]), 6)
    lng = round(random.uniform(*meta["lng_range"]), 6)
    return lat, lng


def _pick_nic(pin_code: str) -> tuple:
    skew = PIN_CODE_METADATA[pin_code]["nic_skew"]
    code_2 = _weighted_choice(skew)
    four_digit_options = list(NIC_HIERARCHY[code_2]["four_digit"].keys())
    code_4 = random.choice(four_digit_options)
    return code_2, code_4


def generate_entities(n: int = 5000, seed: int = 42) -> list:
    random.seed(seed)
    entities = []
    per_pin = n // len(PIN_CODES)

    for idx, pin_code in enumerate(PIN_CODES):
        count = per_pin if idx < len(PIN_CODES) - 1 else n - len(entities)
        for _ in range(count):
            entity_num = len(entities) + 1
            entity_id = f"ENT_{entity_num:06d}"

            entity_type = _weighted_choice(ENTITY_TYPE_DISTRIBUTION)
            status = _weighted_choice(STATUS_DISTRIBUTION)
            nic_2, nic_4 = _pick_nic(pin_code)

            has_pan = random.random() < 0.40
            true_pan = _generate_pan() if has_pan else None
            has_gstin = has_pan and random.random() < 0.60
            true_gstin = _pan_to_gstin(true_pan) if has_gstin else None

            reg_year = random.randint(2000, 2022)
            lat, lng = _generate_coords(pin_code)

            is_seasonal = status == "seasonal_active"
            closure_date = None
            if status == "closed":
                close_year = random.randint(reg_year + 1, 2024)
                closure_date = f"{close_year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"

            owner = f"{random.choice(OWNER_FIRST_NAMES)} {random.choice(OWNER_LAST_NAMES)}"

            entities.append(GroundTruthEntity(
                entity_id=entity_id,
                true_name=_generate_business_name(entity_type),
                true_pan=true_pan,
                true_gstin=true_gstin,
                true_address=_generate_address(pin_code),
                true_lat=lat,
                true_lng=lng,
                nic_code_2digit=nic_2,
                nic_code_4digit=nic_4,
                owner_name=owner,
                phone=_generate_phone(),
                registration_year=reg_year,
                entity_type=entity_type,
                is_seasonal=is_seasonal,
                seasonal_months=SEASONAL_MONTHS if is_seasonal else [],
                ground_truth_status=status,
                closure_date=closure_date,
            ))

    return entities
