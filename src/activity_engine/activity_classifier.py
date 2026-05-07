"""
activity_engine/activity_classifier.py
Bulk-runs activity scoring for UBIDs and persists status.
"""
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database.models import UBIDActivityEvent, ActivityScore, UBIDEntity
from .signal_scorer import compute_activity_score
import logging
import uuid

logger = logging.getLogger(__name__)


def classify_all_ubids(ubid_list: List[str], db: Session, reference_date: Optional[datetime] = None) -> dict:
    """
    Computes activity score for all specified UBIDs, writes new ActivityScore row,
    and updates UBIDEntity.activity_status.

    reference_date: if None, uses the latest event timestamp in the DB so the
    lookback window is data-relative (avoids all-DORMANT when data is historic).
    """
    if reference_date is None:
        latest = db.query(func.max(UBIDActivityEvent.event_timestamp)).scalar()
        if latest:
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            reference_date = latest
            logger.info("Using data-relative reference date: %s", reference_date.date())

    results = {}

    for ubid in ubid_list:
        # 1. Fetch all events for this UBID
        events_orm = db.query(UBIDActivityEvent).filter(
            UBIDActivityEvent.ubid == ubid).all()
        events = [
            {
                "event_type": e.event_type,
                "event_timestamp": e.event_timestamp,
                "source_system": e.source_system,
                "payload": e.payload
            }
            for e in events_orm
        ]

        # 2. Compute score (pass reference_date so lookback is data-relative)
        score_data = compute_activity_score(ubid, events, reference_date=reference_date)

        # Attach AI narrative — skipped during bulk pipeline runs (enable via ENABLE_ACTIVITY_LLM=true)
        import os
        score_data["activity_narrative"] = None
        if os.getenv("ENABLE_ACTIVITY_LLM", "false").lower() == "true":
            try:
                from src.llm_router import explain_activity_status
                narrative = explain_activity_status(
                    ubid,
                    score_data["activity_status"],
                    score_data.get("evidence", [])[:8],
                )
                score_data["activity_narrative"] = narrative
            except Exception:
                pass

        # 3. Set old rows to is_current=False
        db.query(ActivityScore).filter(
            ActivityScore.ubid == ubid,
            ActivityScore.is_current
        ).update({"is_current": False})

        # 4. Write new ActivityScore row
        new_score = ActivityScore(
            score_id=str(uuid.uuid4()),
            ubid=ubid,
            raw_score=score_data["raw_score"],
            activity_status=score_data["activity_status"],
            evidence_snapshot=score_data,
            is_current=True
        )
        db.add(new_score)

        # 5. Update UBIDEntity
        db.query(UBIDEntity).filter(UBIDEntity.ubid == ubid).update(
            {"activity_status": score_data["activity_status"]}
        )

        results[ubid] = score_data["activity_status"]

    db.commit()
    logger.info(f"Classified {len(ubid_list)} UBIDs.")
    return results
