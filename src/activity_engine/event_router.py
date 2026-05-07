"""
activity_engine/event_router.py
Polls unprocessed events and routes them to UBIDs.
"""
from sqlalchemy.orm import Session
from src.database.models import ActivityEventRaw, UBIDActivityEvent, UnmatchedEvent
from .signal_config import SIGNAL_WEIGHTS, SIGNAL_HALF_LIVES
import logging

logger = logging.getLogger(__name__)


def route_all_events(record_to_ubid: dict, db: Session) -> dict:
    """
    Poll unprocessed events, look up their UBID, write to ubid_activity_events or unmatched_events.

    record_to_ubid supports two key formats:
      1. "source_system:licence_no"  — for licence_renewal events whose source_record_id IS the licence number
      2. "any:entity_id"             — for events (inspection, compliance, admin, closure) whose
                                       source_record_id is the entity_id (e.g. "ENT_000042")
    """
    unprocessed_events = db.query(ActivityEventRaw).filter(
        ActivityEventRaw.processed == False).all()

    routed_count = 0
    unmatched_count = 0

    for event in unprocessed_events:
        # Try exact source_system:source_record_id match first (licence_renewal events)
        lookup_key = f"{event.source_system}:{event.source_record_id}"
        ubid = record_to_ubid.get(lookup_key)

        # Fallback: some events use entity_id as source_record_id — try cross-system lookup
        if ubid is None:
            ubid = record_to_ubid.get(f"any:{event.source_record_id}")

        # Second fallback: events like BESCOM use consumer_no as source_record_id but carry
        # the ground-truth entity_id column — use it to route cross-system events
        if ubid is None and event.entity_id:
            ubid = record_to_ubid.get(f"any:{event.entity_id}")

        weight = SIGNAL_WEIGHTS.get(event.event_type, 0.0)
        half_life = SIGNAL_HALF_LIVES.get(event.event_type)

        if ubid:
            # Write to ubid_activity_events
            ubid_event = UBIDActivityEvent(
                ubid=ubid,
                source_event_id=event.event_id,
                source_system=event.source_system,
                event_type=event.event_type,
                event_timestamp=event.event_timestamp,
                signal_weight=weight,
                half_life_days=half_life,
                payload=event.payload
            )
            db.add(ubid_event)
            routed_count += 1
        else:
            # Write to unmatched_events
            unmatched = UnmatchedEvent(
                source_system=event.source_system,
                source_record_id=event.source_record_id,
                event_type=event.event_type,
                event_timestamp=event.event_timestamp,
                payload=event.payload,
                reason_unmatched="NO_SOURCE_LINK"
            )
            db.add(unmatched)
            unmatched_count += 1

        # Always mark processed so we never silently drop or re-process
        event.processed = True

    db.commit()
    logger.info(
        f"Routed {routed_count} events to UBIDs. Sent {unmatched_count} to unmatched queue.")

    return {"routed": routed_count, "unmatched": unmatched_count}
