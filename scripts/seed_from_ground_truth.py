"""
scripts/seed_from_ground_truth.py
Fast UBID seeder — uses the ground truth entity_clusters.csv to directly
populate ubid_entities and ubid_source_links WITHOUT running the ML pipeline.
Also routes activity events and classifies activity scores.

Run this after load_dept_records.py for an instant demo-ready database.
"""
import sys
import uuid
import logging
import random
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.connection import SessionLocal
from src.database.models import (
    UBIDEntity, UBIDSourceLink, ActivityScore, UBIDActivityEvent,
    DeptShopEstablishment, DeptFactories, DeptLabour, DeptKSPCB,
    ActivityEventRaw,
)
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

GROUND_TRUTH = Path("data/ground_truth/entity_clusters.csv")

# PK field per source system
PK_MAP = {
    "shop_establishment": "se_reg_no",
    "factories": "factory_licence_no",
    "labour": "employer_code",
    "kspcb": "consent_order_no",
}

# PAN/GSTIN field per source system
PAN_MAP = {
    "shop_establishment": ("pan", "gstin"),
    "factories": ("pan", "gstin"),
    "labour": ("pan", "gstin"),
    "kspcb": ("pan", "gstin"),
}

ACTIVITY_STATUSES = ["ACTIVE", "ACTIVE", "ACTIVE", "DORMANT", "CLOSED_SUSPECTED", "CLOSED_CONFIRMED"]


def generate_inspection_events(ubid, activity_status, ref_date):
    from datetime import timedelta
    inspection_types = [
        "inspection_visit",
        "safety_inspection",
        "environmental_inspection"
    ]
    events = []

    if activity_status == "ACTIVE":
        should_have_inspections = random.random() < 0.70
        count = random.randint(1, 4) if should_have_inspections else 0
        day_range = (30, 800)
    elif activity_status == "DORMANT":
        should_have_inspections = random.random() < 0.40
        count = random.randint(1, 2) if should_have_inspections else 0
        day_range = (500, 1500)
    elif activity_status == "CLOSED":
        should_have_inspections = random.random() < 0.20
        count = 1 if should_have_inspections else 0
        day_range = (1000, 3000)
    else:
        count = 0
        day_range = (0, 0)

    for _ in range(count):
        days_ago = random.randint(day_range[0], day_range[1])
        events.append(UBIDActivityEvent(
            ubid=ubid,
            event_type=random.choice(inspection_types),
            event_timestamp=ref_date - timedelta(days=days_ago),
            source_system="mock_seeder",
            signal_weight=round(random.uniform(-1.0, 1.0), 2),
            half_life_days=180,
            payload={}
        ))
    return events


def main():
    db = SessionLocal()
    try:
        # Check if UBIDs already exist
        existing = db.query(UBIDEntity).count()
        if existing > 0:
            if "--reset" in sys.argv:
                log.info("Reset flag found. Deleting existing UBID data...")
                db.query(ActivityScore).delete()
                db.query(UBIDActivityEvent).delete()
                db.query(UBIDSourceLink).delete()
                db.query(UBIDEntity).delete()
                db.commit()
            else:
                log.info("UBIDs already exist (%d rows). Skipping seeding. Use --reset to wipe.", existing)
                return

        log.info("=== Fast UBID Seeder from Ground Truth ===")
        clusters = pd.read_csv(GROUND_TRUTH, dtype=str)
        log.info("Loaded %d cluster rows covering %d unique entities.",
                 len(clusters), clusters["entity_id"].nunique())

        FACTORY_NIC_CODES = [
            "10", "11", "13", "14", "15", "16", "17", "20", "21", "22", 
            "24", "25", "26", "27", "28", "29"
        ]
        SHOP_NIC_CODES = [
            "45", "46", "47", "55", "56", "62", "63", "69", "70", "72", "82"
        ]

        # Build lookup: source_record_id -> (pan, gstin) from dept tables
        log.info("Building PAN/GSTIN lookup from dept tables...")
        pan_lookup: dict = {}  # record_id -> (pan, gstin)

        for model, sys_name in [
            (DeptShopEstablishment, "shop_establishment"),
            (DeptFactories, "factories"),
            (DeptLabour, "labour"),
            (DeptKSPCB, "kspcb"),
        ]:
            pk_field = PK_MAP[sys_name]
            rows = db.query(model).all()
            for r in rows:
                if model == DeptFactories:
                    r.nic_code = random.choice(FACTORY_NIC_CODES)
                elif model == DeptShopEstablishment:
                    r.nic_code = random.choice(SHOP_NIC_CODES)
                
                pk_val = getattr(r, pk_field, None)
                pan = getattr(r, "pan", None)
                gstin = getattr(r, "gstin", None)
                pan_lookup[f"{sys_name}:{pk_val}"] = (pan, gstin)
        
        db.commit() # Commit the nic_code updates back to the DB

        log.info("PAN/GSTIN lookup built: %d records.", len(pan_lookup))

        # Group clusters by entity_id
        grouped = clusters.groupby("entity_id")
        log.info("Creating UBID entities and source links...")

        ubid_entities = []
        source_links = []
        mock_events = []
        ref_date = datetime.now()
        counter = 1

        for entity_id, group in grouped:
            ubid = f"KA-UBID-{counter:06d}"
            counter += 1

            # Collect all PANs/GSTINs for this entity
            pans = set()
            gstins = set()
            for _, row in group.iterrows():
                key = f"{row['source_system']}:{row['source_record_id']}"
                pan, gstin = pan_lookup.get(key, (None, None))
                if pan and pan not in ("nan", "None", ""):
                    pans.add(pan)
                if gstin and gstin not in ("nan", "None", ""):
                    gstins.add(gstin)

            pan_anchor = next(iter(pans), None)
            gstin_anchors = list(gstins)

            status = random.choice(ACTIVITY_STATUSES)

            ubid_entities.append(UBIDEntity(
                ubid=ubid,
                pan_anchor=pan_anchor,
                gstin_anchors=gstin_anchors if gstin_anchors else [],
                anchor_status="ANCHORED" if pan_anchor else "UNANCHORED",
                activity_status=status,
            ))
            
            mock_events.extend(generate_inspection_events(ubid, status, ref_date))

            for _, row in group.iterrows():
                source_links.append(UBIDSourceLink(
                    link_id=str(uuid.uuid4()),
                    ubid=ubid,
                    source_system=row["source_system"],
                    source_record_id=row["source_record_id"],
                    confidence=round(random.uniform(0.92, 1.0), 3),
                    link_type="auto",
                    linked_by="system",
                    is_active=True,
                ))

        # Bulk insert
        log.info("Inserting %d UBIDEntity rows...", len(ubid_entities))
        db.bulk_save_objects(ubid_entities)
        db.commit()
        
        log.info("Inserting %d Mock Inspection Events...", len(mock_events))
        for i in range(0, len(mock_events), 1000):
            db.bulk_save_objects(mock_events[i:i+1000])
        db.commit()

        log.info("Inserting %d UBIDSourceLink rows...", len(source_links))
        # Insert in chunks to avoid memory issues
        chunk = 500
        for i in range(0, len(source_links), chunk):
            db.bulk_save_objects(source_links[i:i+chunk])
            db.commit()
            if i % 5000 == 0:
                log.info("  ... inserted %d/%d source links", i, len(source_links))

        log.info("Source links done.")

        # Build record_id -> ubid mapping for event routing
        log.info("Building record->ubid map for activity event routing...")
        record_to_ubid: dict = {}
        for link in source_links:
            record_to_ubid[f"{link.source_system}:{link.source_record_id}"] = link.ubid

        # Route raw activity events to UBIDs
        log.info("Routing activity events...")
        events = db.query(ActivityEventRaw).filter(ActivityEventRaw.processed == False).all()
        log.info("Found %d unprocessed events.", len(events))

        routed = []
        for ev in events:
            key = f"{ev.source_system}:{ev.source_record_id}"
            ubid = record_to_ubid.get(key)
            if ubid:
                routed.append(UBIDActivityEvent(
                    ubid=ubid,
                    source_event_id=ev.event_id,
                    event_type=ev.event_type,
                    source_system=ev.source_system,
                    event_timestamp=ev.event_timestamp,
                    signal_weight=round(random.uniform(-1.0, 1.0), 2),
                    half_life_days=90,
                    payload=ev.payload,
                ))
            ev.processed = True

        if routed:
            for i in range(0, len(routed), 1000):
                db.bulk_save_objects(routed[i:i+1000])
            db.commit()
        log.info("Routed %d events to UBIDs.", len(routed))

        # Create activity scores for each UBID
        log.info("Creating activity scores...")
        scores = []
        for ent in ubid_entities:
            scores.append(ActivityScore(
                score_id=str(uuid.uuid4()),
                ubid=ent.ubid,
                raw_score=round(random.uniform(0.1, 1.0), 3),
                activity_status=ent.activity_status,
                lookback_days=365,
                is_current=True,
                evidence_snapshot={},
            ))

        for i in range(0, len(scores), 1000):
            db.bulk_save_objects(scores[i:i+1000])
            db.commit()

        log.info("Activity scores created.")

        # Summary
        final_count = db.query(UBIDEntity).count()
        link_count = db.query(UBIDSourceLink).count()
        log.info("=== SEEDING COMPLETE ===")
        log.info("  UBIDEntities    : %d", final_count)
        log.info("  UBIDSourceLinks : %d", link_count)
        log.info("  ActivityScores  : %d", len(scores))
        log.info("  Events Routed   : %d", len(routed))
        log.info("Open http://localhost:3000 — companies should now appear!")

    except Exception:
        db.rollback()
        log.exception("Seeding failed — rolled back.")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
