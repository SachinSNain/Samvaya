"""
scripts/reroute_events.py
Builds an entity_id -> UBID lookup from the DB and re-routes all unmatched events.
Run this after run_pipeline.py when activity events used entity_id as source_record_id.
"""
import sys
import logging
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.connection import SessionLocal
from src.database.models import (
    ActivityEventRaw, UBIDActivityEvent, UnmatchedEvent, ActivityScore,
    UBIDEntity,
)
from src.activity_engine.signal_config import SIGNAL_WEIGHTS, SIGNAL_HALF_LIVES
from src.activity_engine.activity_classifier import classify_all_ubids

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)


def build_entity_to_ubid(db) -> dict:
    """
    Build entity_id -> UBID map by joining each dept table to ubid_source_links.
    A single entity_id may appear in multiple dept tables; we take any UBID found.
    """
    sql = """
        SELECT e.entity_id, usl.ubid
        FROM (
            SELECT entity_id, se_reg_no AS pk, 'shop_establishment' AS src
              FROM dept_shop_establishment WHERE entity_id IS NOT NULL
            UNION ALL
            SELECT entity_id, factory_licence_no, 'factories'
              FROM dept_factories WHERE entity_id IS NOT NULL
            UNION ALL
            SELECT entity_id, employer_code, 'labour'
              FROM dept_labour WHERE entity_id IS NOT NULL
            UNION ALL
            SELECT entity_id, consent_order_no, 'kspcb'
              FROM dept_kspcb WHERE entity_id IS NOT NULL
        ) e
        JOIN ubid_source_links usl
          ON usl.source_record_id = e.pk
         AND usl.source_system     = e.src
        WHERE usl.is_active = true
    """
    rows = db.execute(text(sql)).fetchall()
    mapping = {}
    for entity_id, ubid in rows:
        mapping[entity_id] = ubid   # last-write wins; any UBID for this entity is fine
    log.info("Built entity_id->UBID map: %d entries", len(mapping))
    return mapping


def reroute(db, entity_to_ubid: dict):
    # Clear old unmatched rows (we'll re-evaluate them)
    deleted = db.query(UnmatchedEvent).delete()
    log.info("Cleared %d old unmatched_events rows", deleted)

    # Clear old ubid_activity_events (re-route fresh)
    cleared = db.query(UBIDActivityEvent).delete()
    log.info("Cleared %d old ubid_activity_events rows", cleared)

    # Reset processed flag so we can re-process all events
    db.execute(text("UPDATE activity_events_raw SET processed = FALSE"))
    db.commit()

    events = db.query(ActivityEventRaw).all()
    routed = 0
    unmatched = 0

    for ev in events:
        # Try 1: source_record_id is an entity_id (ENT_xxxxxx) — dept system events
        ubid = entity_to_ubid.get(ev.source_record_id)

        # Try 2: source_record_id is a consumer/licence number (BESCOM, etc.)
        # but the event row itself carries entity_id as ground-truth bridge
        if ubid is None and ev.entity_id:
            ubid = entity_to_ubid.get(ev.entity_id)

        weight   = SIGNAL_WEIGHTS.get(ev.event_type, 0.0)
        half_life = SIGNAL_HALF_LIVES.get(ev.event_type)

        if ubid:
            db.add(UBIDActivityEvent(
                ubid=ubid,
                source_event_id=ev.event_id,
                source_system=ev.source_system,
                event_type=ev.event_type,
                event_timestamp=ev.event_timestamp,
                signal_weight=weight,
                half_life_days=half_life,
                payload=ev.payload,
            ))
            routed += 1
        else:
            db.add(UnmatchedEvent(
                source_event_id=ev.event_id,
                source_system=ev.source_system,
                source_record_id=ev.source_record_id,
                event_type=ev.event_type,
                event_timestamp=ev.event_timestamp,
                reason_unmatched="NO_SOURCE_LINK",
            ))
            unmatched += 1

        ev.processed = True

        if (routed + unmatched) % 10000 == 0:
            log.info("  processed %d events so far...", routed + unmatched)
            db.flush()

    db.commit()
    log.info("Routing complete — routed: %d  unmatched: %d", routed, unmatched)
    return routed, unmatched


def recompute_activity(db, routed: int):
    if routed == 0:
        log.warning("No events routed — skipping activity recomputation.")
        return

    # Clear old activity scores so classify_all_ubids writes fresh ones
    db.query(ActivityScore).delete()
    db.commit()

    ubids = [r[0] for r in db.query(UBIDEntity.ubid).all()]
    log.info("Recomputing activity scores for %d UBIDs...", len(ubids))
    classify_all_ubids(ubids, db)
    log.info("Activity recomputation done.")

    # Summary
    from sqlalchemy import func
    rows = db.query(ActivityScore.activity_status, func.count()).filter(
        ActivityScore.is_current == True
    ).group_by(ActivityScore.activity_status).all()
    for status, cnt in rows:
        log.info("  %s: %d", status, cnt)


def run():
    """Entry point for Celery task — returns summary dict."""
    db = SessionLocal()
    try:
        entity_to_ubid = build_entity_to_ubid(db)
        routed, unmatched = reroute(db, entity_to_ubid)
        recompute_activity(db, routed)
        log.info("=== REROUTE COMPLETE ===")
        return {"routed": routed, "unmatched": unmatched}
    except Exception:
        db.rollback()
        log.exception("Reroute failed")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
