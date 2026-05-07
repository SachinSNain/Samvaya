"""
Generates a 12-month activity event stream (2024-05-01 to 2025-04-30) for each entity.
Target: ~120,000 events across ~5,000 entities.
"""
import json
import random
import string
import uuid
from datetime import date, datetime, timedelta

from .entity_generator import GroundTruthEntity

EVENT_START = date(2024, 5, 1)
EVENT_END = date(2025, 4, 30)

SIGNAL_CONFIG = {
    "electricity_consumption_high": {
        "source_system": "bescom",
        "frequency": "monthly",
        "payload_fields": ["kwh_consumed", "billing_month", "consumer_no", "account_type"],
    },
    "electricity_consumption_low": {
        "source_system": "bescom",
        "frequency": "monthly",
        "payload_fields": ["kwh_consumed", "billing_month", "consumer_no", "account_type"],
    },
    "licence_renewal": {
        "source_system": "shop_establishment",
        "frequency": "annual",
        "payload_fields": ["licence_no", "valid_from", "valid_until", "fee_paid"],
    },
    "inspection_visit": {
        "source_system": "factories",
        "frequency": "irregular",
        "payload_fields": ["inspector_id", "inspection_type", "outcome", "violations_noted"],
    },
    "compliance_filing": {
        "source_system": "kspcb",
        "frequency": "quarterly",
        "payload_fields": ["filing_type", "period_covered", "submission_date"],
    },
    "administrative_update": {
        "source_system": "any",
        "frequency": "rare",
        "payload_fields": ["update_type", "old_value", "new_value"],
    },
    "renewal_overdue": {
        "source_system": "shop_establishment",
        "frequency": "derived",
        "payload_fields": ["licence_no", "days_overdue", "original_due_date"],
    },
    "closure_declaration": {
        "source_system": "any",
        "frequency": "once",
        "payload_fields": ["closure_reason", "closure_date", "declared_by"],
    },
}

EVENT_PATTERNS = {
    "active": {
        "kwh_range": (2000, 8000),
        "high_threshold_fraction": 0.50,
        "inspection_per_year": (1, 3),
        "licence_renewal_prob": 0.92,
        "compliance_filing_prob": 0.88,
        "admin_update_prob": 0.20,
    },
    "dormant": {
        "kwh_range": (50, 400),
        "high_threshold_fraction": 0.50,
        "inspection_per_year": (0, 1),
        "licence_renewal_prob": 0.45,
        "compliance_filing_prob": 0.30,
        "admin_update_prob": 0.10,
    },
    "closed": {
        "kwh_range": (0, 30),
        "high_threshold_fraction": 0.50,
        "inspection_per_year": (0, 0),
        "licence_renewal_prob": 0.00,
        "compliance_filing_prob": 0.00,
        "admin_update_prob": 0.00,
    },
    "seasonal_active": {
        "active_months": {10, 11, 12, 1, 2, 3},
        "active_kwh_range": (3000, 9000),
        "inactive_kwh_range": (0, 50),
        "inspection_per_year": (1, 2),
        "licence_renewal_prob": 0.80,
        "compliance_filing_prob": 0.70,
        "admin_update_prob": 0.15,
    },
}


def _random_date_in_month(year: int, month: int) -> datetime:
    day = random.randint(1, 28)
    hour = random.randint(8, 17)
    minute = random.randint(0, 59)
    return datetime(year, month, day, hour, minute)


def _consumer_no() -> str:
    return "BES" + "".join(random.choices(string.digits, k=9))


def _inspector_id() -> str:
    return "INS" + "".join(random.choices(string.digits, k=5))


def _licence_no(entity_id: str, dept: str) -> str:
    prefix = {
        "shop_establishment": "SE",
        "factories": "FAC",
        "labour": "LAB",
        "kspcb": "PCB"}.get(
        dept,
        "REG")
    return f"{prefix}/BNG/{entity_id[-6:]}"


def _make_event(
        entity: GroundTruthEntity,
        event_type: str,
        ts: datetime,
        source_system: str,
        source_record_id: str,
        payload: dict) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "source_system": source_system,
        "source_record_id": source_record_id,
        "event_type": event_type,
        "event_timestamp": ts.isoformat(),
        "entity_id": entity.entity_id,
        "payload_json": json.dumps(payload),
        "processed": False,
    }


def _generate_electricity_events(
        entity: GroundTruthEntity,
        pattern: dict,
        status: str) -> list:
    events = []
    consumer_no = _consumer_no()
    months = []
    d = EVENT_START.replace(day=1)
    while d <= EVENT_END:
        months.append((d.year, d.month))
        next_month = d.month + 1
        next_year = d.year + (1 if next_month > 12 else 0)
        next_month = next_month if next_month <= 12 else 1
        d = d.replace(year=next_year, month=next_month)

    for year, month in months:
        if status == "seasonal_active":
            kwh_range = pattern["active_kwh_range"] if month in pattern["active_months"] else pattern["inactive_kwh_range"]
        else:
            kwh_range = pattern["kwh_range"]

        kwh = round(random.uniform(*kwh_range), 1)
        high_threshold = kwh_range[1] * \
            pattern.get("high_threshold_fraction", 0.50)
        event_type = "electricity_consumption_high" if kwh >= high_threshold else "electricity_consumption_low"
        ts = _random_date_in_month(year, month)

        payload = {
            "kwh_consumed": kwh,
            "billing_month": f"{year}-{month:02d}",
            "consumer_no": consumer_no,
            "account_type": "commercial" if entity.entity_type != "home_based" else "domestic",
        }
        events.append(
            _make_event(
                entity,
                event_type,
                ts,
                "bescom",
                consumer_no,
                payload))

    return events


def _generate_licence_renewal_events(
        entity: GroundTruthEntity,
        pattern: dict) -> list:
    events = []
    renewal_prob = pattern.get("licence_renewal_prob", 0)
    if random.random() > renewal_prob:
        return events

    for dept in ["shop_establishment", "factories"]:
        if random.random() < 0.5:
            continue
        ts = _random_date_in_month(
            random.choice([2024, 2025]),
            random.choice([1, 2, 3, 4, 11, 12])
        )
        if ts.date() < EVENT_START or ts.date() > EVENT_END:
            ts = datetime(2024, random.randint(5, 12), random.randint(1, 28))

        lic_no = _licence_no(entity.entity_id, dept)
        payload = {
            "licence_no": lic_no,
            "valid_from": ts.date().isoformat(),
            "valid_until": ts.date().replace(year=ts.year + 1).isoformat(),
            "fee_paid": round(random.uniform(500, 5000), 2),
        }
        source_systems = {
            "shop_establishment": "shop_establishment",
            "factories": "factories"}
        events.append(_make_event(entity, "licence_renewal", ts,
                                  source_systems[dept], lic_no, payload))

        # Check if renewal was overdue (20% chance for dormant)
        if entity.ground_truth_status == "dormant" and random.random() < 0.30:
            overdue_ts = ts + timedelta(days=random.randint(30, 180))
            if overdue_ts.date() <= EVENT_END:
                due_date = ts.date().isoformat()
                days_overdue = random.randint(30, 180)
                overdue_payload = {
                    "licence_no": lic_no,
                    "days_overdue": days_overdue,
                    "original_due_date": due_date,
                }
                events.append(
                    _make_event(
                        entity,
                        "renewal_overdue",
                        overdue_ts,
                        dept,
                        lic_no,
                        overdue_payload))

    return events


def _generate_inspection_events(
        entity: GroundTruthEntity,
        pattern: dict) -> list:
    events = []
    min_insp, max_insp = pattern.get("inspection_per_year", (0, 0))
    count = random.randint(min_insp, max_insp)

    inspection_sources = ["factories", "labour", "kspcb"]
    for _ in range(count):
        source = random.choice(inspection_sources)
        ts = EVENT_START + \
            timedelta(days=random.randint(0, (EVENT_END - EVENT_START).days))
        ts = datetime(
            ts.year, ts.month, ts.day, random.randint(
                9, 16), random.randint(
                0, 59))

        payload = {
            "inspector_id": _inspector_id(),
            "inspection_type": random.choice(["routine", "surprise", "complaint-based", "follow-up"]),
            "outcome": random.choice(["compliant", "minor_violations", "major_violations", "compliant"]),
            "violations_noted": random.randint(0, 3),
        }
        events.append(_make_event(entity, "inspection_visit", ts,
                                  source, entity.entity_id, payload))

    return events


def _generate_compliance_events(
        entity: GroundTruthEntity,
        pattern: dict) -> list:
    events = []
    if random.random() > pattern.get("compliance_filing_prob", 0):
        return events

    quarters = [
        ("2024-05-01", "2024-07-31"),
        ("2024-08-01", "2024-10-31"),
        ("2024-11-01", "2025-01-31"),
        ("2025-02-01", "2025-04-30"),
    ]
    for q_start, q_end in quarters:
        if random.random() < 0.25:
            continue
        q_start_d = date.fromisoformat(q_start)
        q_end_d = date.fromisoformat(q_end)
        filing_date = q_end_d + timedelta(days=random.randint(1, 30))
        if filing_date > EVENT_END:
            filing_date = EVENT_END
        ts = datetime(filing_date.year, filing_date.month,
                      min(filing_date.day, 28), random.randint(9, 17))

        payload = {
            "filing_type": random.choice(["annual_return", "half_yearly_return", "quarterly_statement"]),
            "period_covered": f"{q_start} to {q_end}",
            "submission_date": filing_date.isoformat(),
        }
        events.append(_make_event(entity, "compliance_filing", ts,
                                  "kspcb", entity.entity_id, payload))

    return events


def _generate_admin_update_events(
        entity: GroundTruthEntity,
        pattern: dict) -> list:
    events = []
    if random.random() > pattern.get("admin_update_prob", 0):
        return events

    ts = EVENT_START + \
        timedelta(days=random.randint(0, (EVENT_END - EVENT_START).days))
    ts = datetime(ts.year, ts.month, ts.day, random.randint(9, 17))
    update_types = [
        "address_change",
        "owner_change",
        "phone_update",
        "trade_category_update"]
    payload = {
        "update_type": random.choice(update_types),
        "old_value": "old_data",
        "new_value": "new_data",
    }
    source = random.choice(["shop_establishment", "factories", "labour"])
    events.append(_make_event(entity, "administrative_update", ts,
                              source, entity.entity_id, payload))
    return events


def _generate_closure_event(entity: GroundTruthEntity) -> list:
    if entity.ground_truth_status != "closed" or not entity.closure_date:
        return []

    closure_dt = date.fromisoformat(entity.closure_date)
    if closure_dt < EVENT_START:
        closure_dt = EVENT_START + timedelta(days=random.randint(0, 30))
    if closure_dt > EVENT_END:
        closure_dt = EVENT_END

    ts = datetime(
        closure_dt.year, closure_dt.month, min(
            closure_dt.day, 28), 10, 0)
    payload = {
        "closure_reason": random.choice(["voluntary", "licence_expired", "owner_retired", "business_sold"]),
        "closure_date": closure_dt.isoformat(),
        "declared_by": random.choice(["owner", "dept_officer", "court_order"]),
    }
    source = random.choice(["shop_establishment", "factories", "labour"])
    return [
        _make_event(
            entity,
            "closure_declaration",
            ts,
            source,
            entity.entity_id,
            payload)]


def generate_activity_events(entities: list) -> list:
    """Generate full 12-month event stream for all entities."""
    all_events = []

    for entity in entities:
        status = entity.ground_truth_status
        pattern = EVENT_PATTERNS.get(status, EVENT_PATTERNS["active"])

        all_events.extend(
            _generate_electricity_events(
                entity, pattern, status))
        all_events.extend(_generate_licence_renewal_events(entity, pattern))
        all_events.extend(_generate_inspection_events(entity, pattern))
        all_events.extend(_generate_compliance_events(entity, pattern))
        all_events.extend(_generate_admin_update_events(entity, pattern))
        all_events.extend(_generate_closure_event(entity))

    return all_events
