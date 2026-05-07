"""
api/routers/activity.py
Endpoints for querying business activity.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from src.database.connection import get_db
from src.database.models import (
    ActivityScore, UBIDEntity, UBIDActivityEvent, UBIDSourceLink,
    DeptShopEstablishment, DeptFactories, DeptLabour, DeptKSPCB,
)
from typing import Optional, List
from datetime import datetime, timedelta, timezone

_reference_date_cache: dict = {"ts": 0.0, "value": None}

# ---------- helpers for display_name lookup ----------

def _get_display_name(ubid: str, db: Session) -> Optional[str]:
    """Return first business name found for a UBID across all dept tables."""
    link = db.query(UBIDSourceLink).filter(
        UBIDSourceLink.ubid == ubid,
        UBIDSourceLink.is_active == True,
    ).first()
    if not link:
        return None
    sys = link.source_system
    rid = link.source_record_id
    if sys == "shop_establishment":
        row = db.query(DeptShopEstablishment).filter(
            DeptShopEstablishment.se_reg_no == rid).first()
        return row.business_name if row else None
    if sys == "factories":
        row = db.query(DeptFactories).filter(
            DeptFactories.factory_licence_no == rid).first()
        return row.factory_name if row else None
    if sys == "labour":
        row = db.query(DeptLabour).filter(
            DeptLabour.employer_code == rid).first()
        return row.employer_name if row else None
    if sys == "kspcb":
        row = db.query(DeptKSPCB).filter(
            DeptKSPCB.consent_order_no == rid).first()
        return row.unit_name if row else None
    return None


def _get_dept_count(ubid: str, db: Session) -> int:
    return db.query(UBIDSourceLink).filter(
        UBIDSourceLink.ubid == ubid,
        UBIDSourceLink.is_active == True,
    ).count()


def _get_last_event_info(ubid: str, db: Session):
    """Returns (last_event_date_str, days_since_last_inspection)."""
    last_ev = db.query(UBIDActivityEvent).filter(
        UBIDActivityEvent.ubid == ubid,
    ).order_by(UBIDActivityEvent.event_timestamp.desc()).first()

    last_event_date = None
    if last_ev and last_ev.event_timestamp:
        last_event_date = str(last_ev.event_timestamp)[:10]

    inspection_types = [
        "inspection_visit", "safety_inspection", "environmental_inspection"]
    last_insp = db.query(UBIDActivityEvent).filter(
        UBIDActivityEvent.ubid == ubid,
        UBIDActivityEvent.event_type.in_(inspection_types),
    ).order_by(UBIDActivityEvent.event_timestamp.desc()).first()

    days_since_insp = None
    if last_insp and last_insp.event_timestamp:
        ts = last_insp.event_timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        days_since_insp = (datetime.now(timezone.utc) - ts).days

    return last_event_date, days_since_insp


def _get_reference_date(db: Session) -> datetime:
    """Returns data-relative reference date (MAX event_timestamp), cached for 5 min."""
    import time
    if time.time() - _reference_date_cache["ts"] < 300 and _reference_date_cache["value"]:
        return _reference_date_cache["value"]
    latest = db.query(func.max(UBIDActivityEvent.event_timestamp)).scalar()
    ref = latest.replace(tzinfo=timezone.utc) if latest and latest.tzinfo is None else (
        latest or datetime.now(timezone.utc))
    _reference_date_cache["value"] = ref
    _reference_date_cache["ts"] = time.time()
    return ref

router = APIRouter()


@router.get("/stats")
def get_activity_stats(db: Session = Depends(get_db)):
    """Aggregate counts for KPI strip and donut chart."""
    rows = db.query(
        ActivityScore.activity_status,
        func.count(ActivityScore.score_id).label("cnt")
    ).filter(
        ActivityScore.is_current == True
    ).group_by(ActivityScore.activity_status).all()

    counts = {r.activity_status: r.cnt for r in rows}
    total = sum(counts.values())
    return {
        "total": total,
        "active": counts.get("ACTIVE", 0),
        "dormant": counts.get("DORMANT", 0),
        "closed_suspected": counts.get("CLOSED_SUSPECTED", 0),
        "closed_confirmed": counts.get("CLOSED_CONFIRMED", 0),
    }


@router.get("/query")
def query_businesses(
        status: Optional[str] = Query(None, description="ACTIVE / DORMANT / CLOSED_SUSPECTED / CLOSED_CONFIRMED"),
        pincode: Optional[str] = Query(None),
        sector_nic: Optional[str] = Query(None, description="2-digit NIC code"),
        no_inspection_days: Optional[int] = Query(None, description="No inspection event in last N days"),
        db: Session = Depends(get_db)):
    return _run_activity_query(status, pincode, sector_nic, no_inspection_days, db)


def _run_activity_query(
        status: Optional[str],
        pincode: Optional[str],
        sector_nic: Optional[str],
        no_inspection_days: Optional[int],
        db: Session):
    """
    Core logic for activity queries — callable from both the GET endpoint
    and the NL query router without FastAPI Query() default values interfering.
    """
    q = db.query(ActivityScore).filter(ActivityScore.is_current)

    if status:
        status_upper = status.upper()
        if status_upper == "CLOSED":
            q = q.filter(ActivityScore.activity_status.in_(["CLOSED_SUSPECTED", "CLOSED_CONFIRMED"]))
        else:
            q = q.filter(ActivityScore.activity_status == status_upper)

    results = q.all()

    if pincode:
        ubids_in_pin = _get_ubids_in_pincode(pincode, db)
        results = [r for r in results if r.ubid in ubids_in_pin]

    if sector_nic:
        ubids_in_sector = _get_ubids_in_sector(sector_nic, db)
        results = [r for r in results if r.ubid in ubids_in_sector]

    if no_inspection_days:
        ref = _get_reference_date(db)
        cutoff_date = ref - timedelta(days=no_inspection_days)
        results = [
            r for r in results
            if not _has_recent_inspection(r.ubid, cutoff_date, db)
        ]

    enriched = []
    for r in results[:200]:
        display_name = _get_display_name(r.ubid, db)
        dept_count = _get_dept_count(r.ubid, db)
        last_event_date, days_since_insp = _get_last_event_info(r.ubid, db)
        enriched.append({
            "ubid": r.ubid,
            "display_name": display_name,
            "dept_count": dept_count,
            "activity_status": r.activity_status,
            "activity_score": r.raw_score,
            "computed_at": str(r.computed_at),
            "last_event_date": last_event_date,
            "days_since_last_inspection": days_since_insp,
            "evidence_summary": _summarise_evidence(r.evidence_snapshot)
        })

    return {
        "query": {
            "status": status,
            "pincode": pincode,
            "sector_nic": sector_nic,
            "no_inspection_days": no_inspection_days
        },
        "result_count": len(results),
        "results": enriched
    }


def _has_recent_inspection(ubid: str, cutoff: datetime, db: Session) -> bool:
    inspection_types = [
        "inspection_visit",
        "safety_inspection",
        "environmental_inspection"]
    recent = db.query(UBIDActivityEvent).filter(
        UBIDActivityEvent.ubid == ubid,
        UBIDActivityEvent.event_type.in_(inspection_types),
        UBIDActivityEvent.event_timestamp >= cutoff
    ).first()
    return recent is not None


def _get_ubids_in_pincode(pincode: str, db: Session) -> set:
    """Returns set of UBIDs that have at least one source record in the given pin code.
    Queries pin_code column across all four dept tables via source links.
    """
    # Collect (source_system, primary_key) pairs that match the pin code
    matching_keys = set()

    se_rows = db.query(DeptShopEstablishment.se_reg_no).filter(
        DeptShopEstablishment.pin_code == pincode).all()
    matching_keys.update(("shop_establishment", r[0]) for r in se_rows)

    fac_rows = db.query(DeptFactories.factory_licence_no).filter(
        DeptFactories.pin_code == pincode).all()
    matching_keys.update(("factories", r[0]) for r in fac_rows)

    lab_rows = db.query(DeptLabour.employer_code).filter(
        DeptLabour.pin_code == pincode).all()
    matching_keys.update(("labour", r[0]) for r in lab_rows)

    kspcb_rows = db.query(DeptKSPCB.consent_order_no).filter(
        DeptKSPCB.pin_code == pincode).all()
    matching_keys.update(("kspcb", r[0]) for r in kspcb_rows)

    if not matching_keys:
        return set()

    ubids = set()
    for source_system, source_record_id in matching_keys:
        link = db.query(UBIDSourceLink.ubid).filter(
            UBIDSourceLink.source_system == source_system,
            UBIDSourceLink.source_record_id == source_record_id,
            UBIDSourceLink.is_active == True,
        ).first()
        if link:
            ubids.add(link[0])

    return ubids


def _get_ubids_in_sector(nic_code: str, db: Session) -> set:
    """Returns set of UBIDs that match the given NIC sector.
    Queries nic_code column across DeptFactories and DeptShopEstablishment via source links.
    """
    matching_keys = set()

    fac_rows = db.query(DeptFactories.factory_licence_no).filter(
        DeptFactories.nic_code == nic_code).all()
    matching_keys.update(("factories", r[0]) for r in fac_rows)

    se_rows = db.query(DeptShopEstablishment.se_reg_no).filter(
        DeptShopEstablishment.nic_code == nic_code).all()
    matching_keys.update(("shop_establishment", r[0]) for r in se_rows)

    if not matching_keys:
        return set()

    ubids = set()
    for source_system, source_record_id in matching_keys:
        link = db.query(UBIDSourceLink.ubid).filter(
            UBIDSourceLink.source_system == source_system,
            UBIDSourceLink.source_record_id == source_record_id,
            UBIDSourceLink.is_active == True,
        ).first()
        if link:
            ubids.add(link[0])

    return ubids


def _summarise_evidence(evidence_snapshot) -> dict:
    if not evidence_snapshot:
        return {}
    events = evidence_snapshot.get("evidence", [])
    top_positive = [e for e in events if e.get("contribution", 0) > 0][:3]
    top_negative = [e for e in events if e.get("contribution", 0) < 0][:2]
    return {
        "top_positive_signals": [
            {"event_type": e["event_type"], "contribution": e["contribution"]}
            for e in top_positive
        ],
        "top_negative_signals": [
            {"event_type": e["event_type"], "contribution": e["contribution"]}
            for e in top_negative
        ],
        "total_events_in_window": evidence_snapshot.get("event_count", 0)
    }


@router.get("/{ubid}/timeline")
def get_activity_timeline(ubid: str, db: Session = Depends(get_db)):
    """All activity events for a UBID in chronological order."""
    events = db.query(UBIDActivityEvent).filter(
        UBIDActivityEvent.ubid == ubid
    ).order_by(UBIDActivityEvent.event_timestamp.desc()).all()

    # Get the current activity score + status
    current_score = db.query(ActivityScore).filter(
        ActivityScore.ubid == ubid,
        ActivityScore.is_current == True,
    ).first()
    current_status = current_score.activity_status if current_score else "UNKNOWN"

    # Build evidence list from recent events (contribution = signal_weight as proxy)
    try:
        from src.llm_router import explain_activity_status
        evidence_list = [
            {
                "event_type": e.event_type,
                "contribution": e.signal_weight or 0.0,
                "days_since": max(
                    0,
                    (datetime.now(timezone.utc)
                     - e.event_timestamp.replace(tzinfo=timezone.utc)).days,
                ),
            }
            for e in events[:8]
        ]
        activity_narrative = explain_activity_status(
            ubid, current_status, evidence_list
        )
    except Exception:
        activity_narrative = None

    return {
        "ubid": ubid,
        "event_count": len(events),
        "activity_status": current_status,
        "activity_narrative": activity_narrative,
        "events": [
            {
                "event_type": e.event_type,
                "source_system": e.source_system,
                "event_timestamp": str(e.event_timestamp),
                "signal_weight": e.signal_weight,
                "half_life_days": e.half_life_days,
                "payload": e.payload,
            }
            for e in events
        ],
    }


from pydantic import BaseModel

class SectorBreakdownRequest(BaseModel):
    businesses: list

@router.post("/sector-breakdown")
def generate_sector_breakdown(req: SectorBreakdownRequest):
    """Uses LLM to group businesses into sectors and count by status."""
    from src.llm_router import get_sector_breakdown

    simple_list = []
    for b in req.businesses:
        status = b.get("activity_status", "UNKNOWN")
        if status.startswith("CLOSED"):
            status = "CLOSED"
        simple_list.append({
            "name": b.get("display_name", "Unknown"),
            "status": status
        })

    return get_sector_breakdown(simple_list)
