"""
Generates per-department records from ground-truth entities.
Each entity appears in 1–4 departments with controlled variation and
intra-department duplicates injected at 8% rate.
"""
import random
import string
from dataclasses import dataclass
from typing import Optional

from .entity_generator import GroundTruthEntity
from .variation_injector import (
    inject_name_variation, inject_address_variation,
    inject_pan, inject_gstin,
    inject_owner_name_variation, inject_phone_variation,
)
from .dictionaries.nic_codes import NIC_HIERARCHY

DEPT_PRESENCE = {
    "shop_establishment": {
        "factory": 0.90, "shop": 0.99, "service": 0.95, "home_based": 0.70}, "factories": {
            "factory": 0.95, "shop": 0.05, "service": 0.10, "home_based": 0.00}, "labour": {
                "factory": 0.85, "shop": 0.40, "service": 0.50, "home_based": 0.10}, "kspcb": {
                    "factory": 0.80, "shop": 0.05, "service": 0.05, "home_based": 0.00}, }

PAN_PRESENCE_RATE = {
    "shop_establishment": 0.15,
    "factories": 0.45,
    "labour": 0.40,
    "kspcb": 0.65,
}

INTRA_DEPT_DUPLICATE_RATE = 0.08


def _reg_no_se(year: int, seq: int) -> str:
    return f"SE/BNG/{year}/{seq:06d}"


def _reg_no_factory(year: int, seq: int) -> str:
    return f"KA/FAC/{year}/{seq:06d}"


def _employer_code(year: int, seq: int) -> str:
    return f"KA/LAB/{year}/{seq:06d}"


def _consent_order_no(year: int, seq: int) -> str:
    return f"KSPCB/CO/{year}/{seq:06d}"


def _trade_category(entity: GroundTruthEntity) -> str:
    cats = NIC_HIERARCHY.get(
        entity.nic_code_2digit,
        {}).get(
        "trade_categories",
        ["General Trade"])
    return random.choice(cats)


def _product_description(entity: GroundTruthEntity) -> str:
    descs = NIC_HIERARCHY.get(
        entity.nic_code_2digit,
        {}).get(
        "product_descriptions",
        ["General manufacturing"])
    return random.choice(descs)


def _num_workers(entity: GroundTruthEntity) -> int:
    if entity.entity_type == "factory":
        return random.randint(10, 500)
    if entity.entity_type == "shop":
        return random.randint(1, 20)
    return random.randint(1, 50)


def _registration_date(entity: GroundTruthEntity) -> str:
    year = entity.registration_year
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year}-{month:02d}-{day:02d}"


def _licence_valid_until(reg_date: str) -> str:
    year = int(reg_date[:4]) + random.choice([1, 2, 3, 5])
    return f"{year}-{reg_date[5:7]}-{reg_date[8:10]}"


def _build_se_record(
        entity: GroundTruthEntity,
        seq: int,
        duplicate: bool = False) -> dict:
    dept = "shop_establishment"
    pan = inject_pan(entity.true_pan, PAN_PRESENCE_RATE[dept])
    gstin = inject_gstin(entity.true_gstin, pan)
    fmt = random.choice(
        [0, 4, 5]) if not duplicate else random.choice([1, 2, 3])
    reg_date = _registration_date(entity)

    return {
        "se_reg_no": _reg_no_se(entity.registration_year, seq),
        "business_name": inject_name_variation(entity.true_name) if not duplicate
        else inject_name_variation(inject_name_variation(entity.true_name)),
        "owner_name": inject_owner_name_variation(entity.owner_name),
        "address": inject_address_variation(entity.true_address, format_index=fmt),
        "pin_code": entity.true_address["pin_code"],
        "pan": pan,
        "gstin": gstin,
        "phone": inject_phone_variation(entity.phone),
        "trade_category": _trade_category(entity),
        "registration_date": reg_date,
        "status": entity.ground_truth_status if entity.ground_truth_status != "seasonal_active" else "active",
        "entity_id": entity.entity_id,
    }


def _build_factory_record(
        entity: GroundTruthEntity,
        seq: int,
        duplicate: bool = False) -> dict:
    dept = "factories"
    pan = inject_pan(entity.true_pan, PAN_PRESENCE_RATE[dept])
    gstin = inject_gstin(entity.true_gstin, pan)
    fmt = random.choice([1, 2]) if not duplicate else random.choice([3, 4])
    reg_date = _registration_date(entity)

    return {
        "factory_licence_no": _reg_no_factory(entity.registration_year, seq),
        "factory_name": inject_name_variation(entity.true_name) if not duplicate
        else inject_name_variation(inject_name_variation(entity.true_name)),
        "owner_name": inject_owner_name_variation(entity.owner_name),
        "address": inject_address_variation(entity.true_address, format_index=fmt),
        "pin_code": entity.true_address["pin_code"],
        "pan": pan,
        "gstin": gstin,
        "phone": inject_phone_variation(entity.phone),
        "product_description": _product_description(entity),
        "nic_code": entity.nic_code_4digit,
        "num_workers": _num_workers(entity),
        "licence_valid_until": _licence_valid_until(reg_date),
        "registration_date": reg_date,
        "status": entity.ground_truth_status if entity.ground_truth_status != "seasonal_active" else "active",
        "entity_id": entity.entity_id,
    }


def _build_labour_record(
        entity: GroundTruthEntity,
        seq: int,
        duplicate: bool = False) -> dict:
    dept = "labour"
    pan = inject_pan(entity.true_pan, PAN_PRESENCE_RATE[dept])
    gstin = inject_gstin(entity.true_gstin, pan)
    fmt = random.choice([0, 5]) if not duplicate else random.choice([2, 4])
    reg_date = _registration_date(entity)

    return {
        "employer_code": _employer_code(entity.registration_year, seq),
        "employer_name": inject_name_variation(entity.true_name) if not duplicate
        else inject_name_variation(inject_name_variation(entity.true_name)),
        "owner_name": inject_owner_name_variation(entity.owner_name),
        "address": inject_address_variation(entity.true_address, format_index=fmt),
        "pin_code": entity.true_address["pin_code"],
        "pan": pan,
        "gstin": gstin,
        "phone": inject_phone_variation(entity.phone),
        "industry_type": _trade_category(entity),
        "num_employees": _num_workers(entity),
        "registration_date": reg_date,
        "status": entity.ground_truth_status if entity.ground_truth_status != "seasonal_active" else "active",
        "entity_id": entity.entity_id,
    }


def _build_kspcb_record(
        entity: GroundTruthEntity,
        seq: int,
        duplicate: bool = False) -> dict:
    dept = "kspcb"
    pan = inject_pan(entity.true_pan, PAN_PRESENCE_RATE[dept])
    gstin = inject_gstin(entity.true_gstin, pan)
    fmt = random.choice([1, 2]) if not duplicate else random.choice([3, 5])
    reg_date = _registration_date(entity)

    return {
        "consent_order_no": _consent_order_no(entity.registration_year, seq),
        "unit_name": inject_name_variation(entity.true_name) if not duplicate
        else inject_name_variation(inject_name_variation(entity.true_name)),
        "owner_name": inject_owner_name_variation(entity.owner_name),
        "address": inject_address_variation(entity.true_address, format_index=fmt),
        "pin_code": entity.true_address["pin_code"],
        "pan": pan,
        "gstin": gstin,
        "phone": inject_phone_variation(entity.phone),
        "nic_code": entity.nic_code_4digit,
        "consent_type": random.choice(["establish", "operate"]),
        "consent_valid_until": _licence_valid_until(reg_date),
        "registration_date": reg_date,
        "status": entity.ground_truth_status if entity.ground_truth_status != "seasonal_active" else "active",
        "entity_id": entity.entity_id,
    }


_BUILDERS = {
    "shop_establishment": _build_se_record,
    "factories": _build_factory_record,
    "labour": _build_labour_record,
    "kspcb": _build_kspcb_record,
}


def generate_department_records(entities: list) -> dict:
    """
    Returns dict: { "shop_establishment": [...], "factories": [...], "labour": [...], "kspcb": [...] }
    """
    records = {dept: [] for dept in _BUILDERS}
    counters = {dept: 1 for dept in _BUILDERS}

    # Identify which entities get intra-dept duplicates (~8%)
    dup_entities = set(
        e.entity_id for e in random.sample(
            entities,
            k=int(
                len(entities) *
                INTRA_DEPT_DUPLICATE_RATE)))

    for entity in entities:
        for dept, builder in _BUILDERS.items():
            presence_prob = DEPT_PRESENCE[dept].get(entity.entity_type, 0.0)
            if random.random() > presence_prob:
                continue

            record = builder(entity, counters[dept])
            records[dept].append(record)
            counters[dept] += 1

            # Intra-department duplicate
            if entity.entity_id in dup_entities:
                dup_record = builder(entity, counters[dept], duplicate=True)
                records[dept].append(dup_record)
                counters[dept] += 1

    return records
