"""
scripts/load_dept_records.py
Loads generated CSV department records and activity events into PostgreSQL.
Run this after generate_synthetic_data.py and before train_model.py.
"""
import sys
import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.connection import SessionLocal
from src.database.models import (
    DeptShopEstablishment, DeptFactories, DeptLabour, DeptKSPCB, ActivityEventRaw
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

def clear_tables(db):
    """Truncate all department and activity tables so load is always idempotent."""
    from sqlalchemy import text
    log.info("Clearing existing data from all department tables...")
    # Must truncate in dependency order (child tables first)
    tables = [
        "activity_events_raw",
        "dept_kspcb",
        "dept_labour",
        "dept_factories",
        "dept_shop_establishment",
    ]
    for table in tables:
        try:
            db.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        except Exception:
            db.rollback()  # Table may not exist yet on very first run — that's OK
            log.warning("Could not truncate %s — may not exist yet, skipping.", table)
    db.commit()
    log.info("Tables cleared.")


def to_none(v):
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    s = str(v).strip()
    return None if s in ('', 'nan', 'None', 'NaT') else s


def parse_dt(v):
    if not to_none(v):
        return None
    try:
        return datetime.fromisoformat(str(v))
    except Exception:
        return None


def parse_int(v):
    try:
        return int(v)
    except Exception:
        return None


def load_shop_establishment(db):
    df = pd.read_csv(DATA_RAW / "shop_establishment.csv", dtype=str)
    df = df.where(pd.notna(df), None)
    objs = []
    for r in df.to_dict("records"):
        objs.append(DeptShopEstablishment(
            se_reg_no=r["se_reg_no"],
            business_name=r["business_name"],
            owner_name=to_none(r.get("owner_name")),
            address=to_none(r.get("address")),
            pin_code=to_none(r.get("pin_code")),
            pan=to_none(r.get("pan")),
            gstin=to_none(r.get("gstin")),
            phone=to_none(r.get("phone")),
            trade_category=to_none(r.get("trade_category")),
            registration_date=parse_dt(r.get("registration_date")),
            status=to_none(r.get("status")),
            entity_id=to_none(r.get("entity_id")),
        ))
    db.bulk_save_objects(objs)
    db.commit()
    log.info("shop_establishment: %d rows inserted.", len(objs))


def load_factories(db):
    df = pd.read_csv(DATA_RAW / "factories.csv", dtype=str)
    df = df.where(pd.notna(df), None)
    objs = []
    for r in df.to_dict("records"):
        objs.append(DeptFactories(
            factory_licence_no=r["factory_licence_no"],
            factory_name=r["factory_name"],
            owner_name=to_none(r.get("owner_name")),
            address=to_none(r.get("address")),
            pin_code=to_none(r.get("pin_code")),
            pan=to_none(r.get("pan")),
            gstin=to_none(r.get("gstin")),
            phone=to_none(r.get("phone")),
            product_description=to_none(r.get("product_description")),
            nic_code=to_none(r.get("nic_code")),
            num_workers=parse_int(r.get("num_workers")),
            licence_valid_until=parse_dt(r.get("licence_valid_until")),
            registration_date=parse_dt(r.get("registration_date")),
            status=to_none(r.get("status")),
            entity_id=to_none(r.get("entity_id")),
        ))
    db.bulk_save_objects(objs)
    db.commit()
    log.info("factories: %d rows inserted.", len(objs))


def load_labour(db):
    df = pd.read_csv(DATA_RAW / "labour.csv", dtype=str)
    df = df.where(pd.notna(df), None)
    objs = []
    for r in df.to_dict("records"):
        objs.append(DeptLabour(
            employer_code=r["employer_code"],
            employer_name=r["employer_name"],
            owner_name=to_none(r.get("owner_name")),
            address=to_none(r.get("address")),
            pin_code=to_none(r.get("pin_code")),
            pan=to_none(r.get("pan")),
            gstin=to_none(r.get("gstin")),
            phone=to_none(r.get("phone")),
            industry_type=to_none(r.get("industry_type")),
            num_employees=parse_int(r.get("num_employees")),
            registration_date=parse_dt(r.get("registration_date")),
            status=to_none(r.get("status")),
            entity_id=to_none(r.get("entity_id")),
        ))
    db.bulk_save_objects(objs)
    db.commit()
    log.info("labour: %d rows inserted.", len(objs))


def load_kspcb(db):
    df = pd.read_csv(DATA_RAW / "kspcb.csv", dtype=str)
    df = df.where(pd.notna(df), None)
    objs = []
    for r in df.to_dict("records"):
        objs.append(DeptKSPCB(
            consent_order_no=r["consent_order_no"],
            unit_name=r["unit_name"],
            owner_name=to_none(r.get("owner_name")),
            address=to_none(r.get("address")),
            pin_code=to_none(r.get("pin_code")),
            pan=to_none(r.get("pan")),
            gstin=to_none(r.get("gstin")),
            phone=to_none(r.get("phone")),
            nic_code=to_none(r.get("nic_code")),
            consent_type=to_none(r.get("consent_type")),
            consent_valid_until=parse_dt(r.get("consent_valid_until")),
            registration_date=parse_dt(r.get("registration_date")),
            status=to_none(r.get("status")),
            entity_id=to_none(r.get("entity_id")),
        ))
    db.bulk_save_objects(objs)
    db.commit()
    log.info("kspcb: %d rows inserted.", len(objs))


def load_activity_events(db):
    df = pd.read_csv(DATA_RAW / "activity_events.csv", dtype=str)
    df = df.where(pd.notna(df), None)
    objs = []
    for r in df.to_dict("records"):
        payload = None
        if r.get("payload_json"):
            try:
                payload = json.loads(r["payload_json"])
            except Exception:
                payload = {"raw": r["payload_json"]}
        objs.append(ActivityEventRaw(
            event_id=r["event_id"],
            source_system=r["source_system"],
            source_record_id=r["source_record_id"],
            event_type=r["event_type"],
            event_timestamp=parse_dt(r.get("event_timestamp")),
            payload=payload,
            entity_id=to_none(r.get("entity_id")),
            processed=False,
        ))
    db.bulk_save_objects(objs)
    db.commit()
    log.info("activity_events_raw: %d rows inserted.", len(objs))


def main():
    db = SessionLocal()
    try:
        log.info("=== Loading department records into PostgreSQL ===")
        clear_tables(db)  # Always wipe first — safe to re-run
        load_shop_establishment(db)
        load_factories(db)
        load_labour(db)
        load_kspcb(db)
        load_activity_events(db)
        log.info("=== ALL DATA LOADED SUCCESSFULLY ===")
    except Exception:
        db.rollback()
        log.exception("Load failed — rolled back.")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
