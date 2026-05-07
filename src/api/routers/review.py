"""
api/routers/review.py
Endpoints for manual reviewer queue and adjudication.
"""
import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import (
    ReviewTask, UBIDSourceLink, UBIDLinkEvidence, UBIDEntity, UBIDActivityEvent, ActivityScore,
    DeptShopEstablishment, DeptFactories, DeptLabour, DeptKSPCB,
)
from src.cache import cache_delete, cache_delete_pattern
from src.database.models import AuditEvent

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Module-level stats cache — avoids a Gemini call on every dashboard refresh ──
_stats_insights_cache: dict = {"ts": 0.0, "value": None}
_STATS_CACHE_TTL = 300  # 5 minutes


@router.get("/queue")
def get_review_queue(
    status: str = Query("PENDING", description="PENDING / IN_REVIEW / DECIDED / DEFERRED"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    query = db.query(ReviewTask).filter(ReviewTask.status == status)

    total = query.count()
    tasks = (
        query.order_by(ReviewTask.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "tasks": [
            {
                "task_id": t.task_id,
                "pair_record_a": t.pair_record_a,
                "pair_record_b": t.pair_record_b,
                "calibrated_score": t.calibrated_score,
                "status": t.status,
                "created_at": str(t.created_at),
                # First sentence of the pre-generated summary as a teaser
                "ai_teaser": t.reviewer_summary.split(".")[0] if t.reviewer_summary else None,
            }
            for t in tasks
        ],
    }


@router.get("/task/{task_id}")
def get_review_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(ReviewTask).filter(ReviewTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Fetch evidence (feature vector + SHAP values)
    evidence = (
        db.query(UBIDLinkEvidence)
        .filter(UBIDLinkEvidence.evidence_id == task.evidence_id)
        .first()
    )
    feature_vector = evidence.feature_vector if evidence else {}
    shap_values = evidence.shap_values if evidence else {}

    # Fast path: pre-generated summary stored on the task row
    ai_explanation = task.reviewer_summary

    # If no pre-generated summary, generate on-demand from feature scores only
    # Use REVIEWER_SCORE_SUMMARY (API lane) — prompt contains feature scores only, no raw PII.
    # Do NOT use REVIEWER_EXPLANATION here — that forces LOCAL and is for raw name/address/PAN.
    if not ai_explanation and feature_vector:
        try:
            from src.llm_router import route, TaskType
            fv = (
                feature_vector
                if isinstance(feature_vector, dict)
                else json.loads(feature_vector or "{}")
            )
            prompt = (
                f"Match confidence: {task.calibrated_score:.0%}. "
                f"Feature scores (F01=name, F04=PAN, F06=pin, F09=phone): "
                f"{json.dumps({k: round(v, 2) for k, v in fv.items() if v is not None})}\n"
                "In 2 sentences: (1) why this might be a match, "
                "(2) what the reviewer should verify."
            )
            ai_explanation = route(
                TaskType.REVIEWER_SCORE_SUMMARY, prompt, max_tokens=120
            )
        except Exception:
            ai_explanation = None

    return {
        "task_id": task.task_id,
        "pair_record_a": task.pair_record_a,
        "pair_record_b": task.pair_record_b,
        "record_a": _fetch_source_record(task.pair_record_a, db),
        "record_b": _fetch_source_record(task.pair_record_b, db),
        "calibrated_score": task.calibrated_score,
        "feature_scores": feature_vector,
        "shap_values": shap_values,
        "status": task.status,
        "decision": task.decision,
        "reviewer_notes": task.reviewer_notes,
        "ai_explanation": ai_explanation,
    }


@router.post("/task/{task_id}/decision")
def submit_decision(
    task_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    decision = payload.get("decision")
    notes = payload.get("reason", "")
    reviewer_id = payload.get("reviewer_id", "system_admin")

    valid_decisions = [
        "CONFIRM_MATCH",
        "CONFIRM_NON_MATCH",
        "CONFIRM_PARTIAL",
        "REQUEST_INFO",
        "DEFER",
    ]
    if decision not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision. Must be one of {valid_decisions}",
        )

    task = db.query(ReviewTask).filter(ReviewTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in ("PENDING", "IN_REVIEW"):
        raise HTTPException(status_code=400, detail="Task already decided")

    # ── Mark the task decided ──────────────────────────────────────────────
    task.decision = decision
    if notes:
        task.decision_reason = notes
    task.status = "DECIDED" if decision not in ("REQUEST_INFO", "DEFER") else decision.upper()
    task.decided_at = datetime.now(timezone.utc)
    task.decided_by = reviewer_id

    # ── Act on the decision ────────────────────────────────────────────────
    if decision == "CONFIRM_MATCH":
        _merge_records(task, reviewer_id, db)
    elif decision == "CONFIRM_NON_MATCH":
        _ensure_separate(task, db)
    # CONFIRM_PARTIAL / REQUEST_INFO / DEFER: no structural change, just log

    # Write explicit audit event with full decision context
    db.add(AuditEvent(
        event_type="review_decision",
        actor=reviewer_id,
        target_id=task_id,
        detail={
            "decision": decision,
            "pair_a": task.pair_record_a,
            "pair_b": task.pair_record_b,
            "score": task.calibrated_score,
            "reason": notes,
        },
    ))
    db.commit()

    # Invalidate cached detail pages for both affected records' UBIDs
    for rec_id in (task.pair_record_a, task.pair_record_b):
        sys_, rid = rec_id.split(":", 1)
        link = db.query(UBIDSourceLink).filter(
            UBIDSourceLink.source_system == sys_,
            UBIDSourceLink.source_record_id == rid,
        ).first()
        if link:
            cache_delete(f"ubid:detail:{link.ubid}")
    cache_delete_pattern("ubid:list:*")

    return {
        "status": "success",
        "message": f"Task {task_id} updated with decision {decision}",
    }


_DEPT_MAP = {
    "shop_establishment": (DeptShopEstablishment, "se_reg_no",
        ["business_name", "owner_name", "address", "pin_code", "pan", "gstin", "phone", "registration_date", "status"]),
    "factories":          (DeptFactories, "factory_licence_no",
        ["factory_name", "owner_name", "address", "pin_code", "pan", "gstin", "phone", "nic_code", "num_workers", "registration_date", "status"]),
    "labour":             (DeptLabour, "employer_code",
        ["employer_name", "owner_name", "address", "pin_code", "pan", "gstin", "phone", "industry_type", "num_employees", "registration_date", "status"]),
    "kspcb":              (DeptKSPCB, "consent_order_no",
        ["unit_name", "owner_name", "address", "pin_code", "pan", "gstin", "phone", "nic_code", "consent_type", "consent_valid_until", "registration_date", "status"]),
}


def _fetch_source_record(record_id: str, db: Session) -> dict:
    """Fetch the raw dept record for display in the review card."""
    try:
        source_system, pk = record_id.split(":", 1)
        entry = _DEPT_MAP.get(source_system)
        if not entry:
            return {"note": f"Unknown source: {source_system}"}
        model, pk_field, fields = entry
        row = db.query(model).filter(getattr(model, pk_field) == pk).first()
        if not row:
            return {"note": f"Record {pk} not found in {source_system}"}
        return {f: str(getattr(row, f, None) or "—") for f in fields}
    except Exception as e:
        return {"error": str(e)}


def _merge_records(task: ReviewTask, reviewer_id: str, db: Session):
    """
    CONFIRM_MATCH: ensure both records share a single UBID.

    If both records already belong to the same UBID (e.g. transitively auto-linked),
    nothing changes. If they belong to different UBIDs, re-point all source links of
    the smaller/newer UBID onto the older one, migrate activity events, then delete
    the now-empty entity.
    """
    sys_a, rec_a = task.pair_record_a.split(":", 1)
    sys_b, rec_b = task.pair_record_b.split(":", 1)

    link_a = db.query(UBIDSourceLink).filter(
        UBIDSourceLink.source_system == sys_a,
        UBIDSourceLink.source_record_id == rec_a,
        UBIDSourceLink.is_active,
    ).first()
    link_b = db.query(UBIDSourceLink).filter(
        UBIDSourceLink.source_system == sys_b,
        UBIDSourceLink.source_record_id == rec_b,
        UBIDSourceLink.is_active,
    ).first()

    if not link_a or not link_b:
        logger.warning("CONFIRM_MATCH: one or both records not linked to any UBID, creating new link")
        _create_manual_link(task, reviewer_id, db)
        return

    ubid_a = link_a.ubid
    ubid_b = link_b.ubid

    if ubid_a == ubid_b:
        return  # Already merged

    # Keep the entity that was created first (lower created_at = older)
    ent_a = db.query(UBIDEntity).filter(UBIDEntity.ubid == ubid_a).first()
    ent_b = db.query(UBIDEntity).filter(UBIDEntity.ubid == ubid_b).first()
    keep_ubid = ubid_a if (ent_a.created_at <= ent_b.created_at) else ubid_b
    drop_ubid = ubid_b if keep_ubid == ubid_a else ubid_a

    # Re-point all source links from drop_ubid → keep_ubid
    db.query(UBIDSourceLink).filter(UBIDSourceLink.ubid == drop_ubid).update(
        {"ubid": keep_ubid, "linked_by": reviewer_id}
    )
    # Re-point activity events
    db.query(UBIDActivityEvent).filter(UBIDActivityEvent.ubid == drop_ubid).update(
        {"ubid": keep_ubid}
    )
    # Re-point activity scores (mark old as not current)
    db.query(ActivityScore).filter(
        ActivityScore.ubid == drop_ubid, ActivityScore.is_current
    ).update({"is_current": False})
    db.query(ActivityScore).filter(ActivityScore.ubid == drop_ubid).update(
        {"ubid": keep_ubid}
    )

    # Add a manual link evidence record
    db.add(UBIDLinkEvidence(
        evidence_id=str(uuid.uuid4()),
        link_id=link_a.link_id if keep_ubid == ubid_a else link_b.link_id,
        pair_record_a=task.pair_record_a,
        pair_record_b=task.pair_record_b,
        calibrated_score=task.calibrated_score,
        feature_vector={},
        shap_values={},
        decision="MANUAL_CONFIRM",
        model_version="1.0.0",
    ))

    # Delete the now-empty entity
    db.query(UBIDEntity).filter(UBIDEntity.ubid == drop_ubid).delete()
    logger.info("Merged UBID %s into %s (reviewer: %s)", drop_ubid, keep_ubid, reviewer_id)


def _ensure_separate(task: ReviewTask, db: Session):
    """
    CONFIRM_NON_MATCH: if the two records were mistakenly auto-linked under the
    same UBID, split them apart. If they already live under different UBIDs, nothing to do.
    """
    sys_a, rec_a = task.pair_record_a.split(":", 1)
    sys_b, rec_b = task.pair_record_b.split(":", 1)

    link_a = db.query(UBIDSourceLink).filter(
        UBIDSourceLink.source_system == sys_a,
        UBIDSourceLink.source_record_id == rec_a,
        UBIDSourceLink.is_active,
    ).first()
    link_b = db.query(UBIDSourceLink).filter(
        UBIDSourceLink.source_system == sys_b,
        UBIDSourceLink.source_record_id == rec_b,
        UBIDSourceLink.is_active,
    ).first()

    if not link_a or not link_b or link_a.ubid != link_b.ubid:
        return  # Already separate

    shared_ubid = link_a.ubid

    # Create a new UBID for record_b
    from src.entity_resolution.ubid_assigner import mint_ubid
    new_ubid = mint_ubid()
    db.add(UBIDEntity(
        ubid=new_ubid,
        pan_anchor=None,
        gstin_anchors=[],
        anchor_status="UNANCHORED",
        activity_status="UNKNOWN",
    ))
    db.flush()

    # Move record_b's link to the new UBID
    link_b.ubid = new_ubid
    link_b.linked_by = "reviewer_split"

    # Activity events stay on the original UBID — splitting events accurately
    # would require knowing which events came from which source record, which is
    # not tracked at event level. The activity score will be recomputed on next run.
    logger.info("Split %s off from UBID %s -> new UBID %s", rec_b, shared_ubid, new_ubid)


def _create_manual_link(task: ReviewTask, reviewer_id: str, db: Session):
    """Creates a new UBID and links both records to it when neither has an existing UBID."""
    from src.entity_resolution.ubid_assigner import mint_ubid
    new_ubid = mint_ubid()
    db.add(UBIDEntity(
        ubid=new_ubid, pan_anchor=None, gstin_anchors=[],
        anchor_status="UNANCHORED", activity_status="UNKNOWN",
    ))
    db.flush()
    for rec_id in (task.pair_record_a, task.pair_record_b):
        sys_, rid = rec_id.split(":", 1)
        db.add(UBIDSourceLink(
            link_id=str(uuid.uuid4()), ubid=new_ubid,
            source_system=sys_, source_record_id=rid,
            confidence=task.calibrated_score, link_type="manual",
            linked_by=reviewer_id, is_active=True,
        ))


@router.get("/stats")
def get_review_stats(db: Session = Depends(get_db)):
    pending = db.query(ReviewTask).filter(ReviewTask.status == "PENDING").count()
    decided = db.query(ReviewTask).filter(ReviewTask.status == "DECIDED").count()

    total_links = db.query(UBIDSourceLink).count()
    manual_link_count = db.query(UBIDSourceLink).filter(
        UBIDSourceLink.link_type == "manual"
    ).count()
    auto_link_count = total_links - manual_link_count

    if total_links + pending > 0:
        auto_link_rate = round((auto_link_count / (total_links + pending)) * 100, 2)
    else:
        auto_link_rate = 0.0

    active_count = db.query(UBIDEntity).filter(UBIDEntity.activity_status == "ACTIVE").count()
    dormant_count = db.query(UBIDEntity).filter(UBIDEntity.activity_status == "DORMANT").count()
    closed_suspected = db.query(UBIDEntity).filter(UBIDEntity.activity_status == "CLOSED_SUSPECTED").count()
    closed_confirmed = db.query(UBIDEntity).filter(UBIDEntity.activity_status == "CLOSED_CONFIRMED").count()
    closed_count = closed_suspected + closed_confirmed
    unknown_count = db.query(UBIDEntity).filter(UBIDEntity.activity_status == "UNKNOWN").count()

    # Serve cached insight; refresh only when TTL expires
    ai_insights = _stats_insights_cache["value"]
    if time.time() - _stats_insights_cache["ts"] > _STATS_CACHE_TTL:
        try:
            from src.llm_router import route, TaskType
            stats_prompt = (
                f"Review queue stats: {pending} pending, {decided} decided, "
                f"{auto_link_count} auto-links, {manual_link_count} manual links. "
                f"Auto-link rate: {auto_link_rate:.1f}%. "
                "Give 1 sentence of insight for a government data quality officer."
            )
            ai_insights = route(TaskType.ANALYTICS_NARRATION, stats_prompt, max_tokens=80)
            _stats_insights_cache["value"] = ai_insights
            _stats_insights_cache["ts"] = time.time()
        except Exception:
            # On failure, serve stale cache rather than returning None
            ai_insights = _stats_insights_cache["value"]

    return {
        "queue_depth": pending,
        "decided": decided,
        "auto_link_count": auto_link_count,
        "manual_link_count": manual_link_count,
        "auto_link_rate_pct": auto_link_rate,
        "active_count": active_count,
        "dormant_count": dormant_count,
        "closed_count": closed_count,
        "unknown_count": unknown_count,
        "ai_insights": ai_insights,
    }
