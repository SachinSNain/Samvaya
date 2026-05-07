"""
api/routers/ubid.py
Endpoints for UBID lookup and detail retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, exists, and_
from src.database.connection import get_db
from src.database.models import (
    UBIDEntity, UBIDSourceLink, UBIDLinkEvidence, ActivityScore,
    DeptShopEstablishment, DeptFactories, DeptLabour, DeptKSPCB,
)
from typing import Optional, List
from src.cache import cache_get, cache_set, cache_delete_pattern

UBID_DETAIL_TTL = 300   # 5 min
UBID_LIST_TTL   = 60    # 1 min

# Maps source_system name → (model class, name field, pk field)
_DEPT_NAME_MAP = {
    "shop_establishment": (DeptShopEstablishment, "business_name", "se_reg_no"),
    "factories":          (DeptFactories,          "factory_name",  "factory_licence_no"),
    "labour":             (DeptLabour,             "employer_name", "employer_code"),
    "kspcb":              (DeptKSPCB,              "unit_name",     "consent_order_no"),
}


def _resolve_display_name(db: Session, source_system: str, source_record_id: str) -> str:
    """Fetch the actual business name from the relevant dept table."""
    entry = _DEPT_NAME_MAP.get(source_system)
    if not entry:
        return source_record_id
    model, name_field, pk_field = entry
    row = db.query(model).filter(getattr(model, pk_field) == source_record_id).first()
    if row:
        return getattr(row, name_field, None) or source_record_id
    return source_record_id


def _fetch_source_record_details(db: Session, source_system: str, source_record_id: str) -> dict:
    """
    Fetch complete source record details from the appropriate department table.
    
    Args:
        db: Database session
        source_system: Source system name (shop_establishment, factories, labour, kspcb)
        source_record_id: Primary key value for the source record
    
    Returns:
        Dict with all relevant fields (business_name, address, PAN, GSTIN, phone, 
        pin_code, owner_name, registration_date). Returns None for missing values.
    """
    entry = _DEPT_NAME_MAP.get(source_system)
    if not entry:
        # Unknown source system - return empty dict with None values
        return {
            "business_name": None,
            "address": None,
            "pan": None,
            "gstin": None,
            "phone": None,
            "pin_code": None,
            "owner_name": None,
            "registration_date": None,
        }
    
    model, name_field, pk_field = entry
    row = db.query(model).filter(getattr(model, pk_field) == source_record_id).first()
    
    if not row:
        # Record not found - return empty dict with None values
        return {
            "business_name": None,
            "address": None,
            "pan": None,
            "gstin": None,
            "phone": None,
            "pin_code": None,
            "owner_name": None,
            "registration_date": None,
        }
    
    # Extract fields from the row, using None for missing values
    return {
        "business_name": getattr(row, name_field, None),
        "address": getattr(row, "address", None),
        "pan": getattr(row, "pan", None),
        "gstin": getattr(row, "gstin", None),
        "phone": getattr(row, "phone", None),
        "pin_code": getattr(row, "pin_code", None),
        "owner_name": getattr(row, "owner_name", None),
        "registration_date": str(getattr(row, "registration_date", None)) if getattr(row, "registration_date", None) else None,
    }


def _calculate_confidence_stats(confidence_scores: List[float]) -> dict:
    """
    Calculate confidence statistics across all link confidence scores.
    
    Args:
        confidence_scores: List of confidence scores (floats between 0 and 1)
    
    Returns:
        Dict with min, max, avg, and distribution histogram:
        {
            "min": float,
            "max": float,
            "avg": float,
            "distribution": [
                {"range": "high", "count": int},    # >0.95
                {"range": "medium", "count": int},  # 0.75-0.95
                {"range": "low", "count": int}      # <0.75
            ]
        }
    """
    if not confidence_scores:
        # No scores - return zeros
        return {
            "min": 0.0,
            "max": 0.0,
            "avg": 0.0,
            "distribution": [
                {"range": "high", "count": 0},
                {"range": "medium", "count": 0},
                {"range": "low", "count": 0}
            ]
        }
    
    # Calculate min, max, avg
    min_score = min(confidence_scores)
    max_score = max(confidence_scores)
    avg_score = sum(confidence_scores) / len(confidence_scores)
    
    # Calculate distribution buckets
    high_count = sum(1 for score in confidence_scores if score > 0.95)
    medium_count = sum(1 for score in confidence_scores if 0.75 <= score <= 0.95)
    low_count = sum(1 for score in confidence_scores if score < 0.75)
    
    return {
        "min": min_score,
        "max": max_score,
        "avg": avg_score,
        "distribution": [
            {"range": "high", "count": high_count},
            {"range": "medium", "count": medium_count},
            {"range": "low", "count": low_count}
        ]
    }


def _calculate_department_coverage(source_systems: List[str]) -> dict:
    """
    Calculate department coverage by counting records from each department.
    
    Args:
        source_systems: List of source_system strings from linked records
    
    Returns:
        Dict with counts for each department:
        {
            "shop_establishment": int,
            "factories": int,
            "labour": int,
            "kspcb": int
        }
    """
    # Initialize all departments with 0 count
    coverage = {
        "shop_establishment": 0,
        "factories": 0,
        "labour": 0,
        "kspcb": 0
    }
    
    # Count occurrences of each department
    for source_system in source_systems:
        if source_system in coverage:
            coverage[source_system] += 1
    
    return coverage

router = APIRouter()


@router.get("/filters")
def get_filters(db: Session = Depends(get_db)):
    """
    Returns available filter options with counts for the UBID directory.
    Used by the FilterPanel component to populate filter choices.
    """
    from sqlalchemy import distinct

    # Activity status options
    activity_statuses = (
        db.query(ActivityScore.activity_status, func.count(ActivityScore.ubid).label("count"))
        .filter(ActivityScore.is_current == True)
        .group_by(ActivityScore.activity_status)
        .all()
    )

    # Anchor status options
    anchor_statuses = (
        db.query(UBIDEntity.anchor_status, func.count(UBIDEntity.ubid).label("count"))
        .group_by(UBIDEntity.anchor_status)
        .all()
    )

    # Link count options (1, 2, 3, 4+) — compute in Python for SQLAlchemy compatibility
    link_counts_raw = (
        db.query(func.count(UBIDSourceLink.link_id).label("link_count"))
        .filter(UBIDSourceLink.is_active == True)
        .group_by(UBIDSourceLink.ubid)
        .all()
    )
    link_count_bucket_map: dict = {}
    for row in link_counts_raw:
        bucket = str(row.link_count) if row.link_count < 4 else "4+"
        link_count_bucket_map[bucket] = link_count_bucket_map.get(bucket, 0) + 1
    link_count_buckets = [
        {"value": k, "label": f"{k} Link{'s' if k != '1' else ''}", "count": v}
        for k, v in sorted(link_count_bucket_map.items(), key=lambda x: (x[0] == "4+", x[0]))
    ]

    # Department options
    departments = (
        db.query(UBIDSourceLink.source_system, func.count(distinct(UBIDSourceLink.ubid)).label("count"))
        .filter(UBIDSourceLink.is_active == True)
        .group_by(UBIDSourceLink.source_system)
        .all()
    )

    dept_labels = {
        "shop_establishment": "Shop & Establishment",
        "factories": "Factories",
        "labour": "Labour",
        "kspcb": "KSPCB",
    }

    return {
        "activity_status": [
            {"value": row.activity_status, "label": row.activity_status, "count": row.count}
            for row in activity_statuses if row.activity_status
        ],
        "anchor_status": [
            {"value": row.anchor_status, "label": row.anchor_status, "count": row.count}
            for row in anchor_statuses if row.anchor_status
        ],
        "link_count": link_count_buckets,
        "departments": [
            {"value": row.source_system, "label": dept_labels.get(row.source_system, row.source_system), "count": row.count}
            for row in departments if row.source_system
        ],
    }


@router.post("/revert-link")
def revert_link(
    data: dict,
    db: Session = Depends(get_db)
):
    """
    Reverts (deactivates) a UBID source link by link_id.
    This unlinks the record from its current UBID.
    The action is irreversible and creates an audit trail.
    """
    link_id = data.get("link_id")
    if not link_id:
        raise HTTPException(status_code=400, detail="link_id is required")

    link = db.query(UBIDSourceLink).filter(
        UBIDSourceLink.link_id == link_id,
        UBIDSourceLink.is_active == True
    ).first()

    if not link:
        raise HTTPException(
            status_code=404,
            detail=f"Active link with link_id={link_id} not found"
        )

    ubid = link.ubid
    link.is_active = False
    db.commit()

    # Invalidate cache for this UBID
    try:
        cache_delete_pattern(f"ubid:*:{ubid}*")
    except Exception:
        pass

    return {
        "success": True,
        "message": f"Link {link_id} has been reverted. Record unlinked from UBID {ubid}.",
        "new_ubid": None,
        "audit_event_id": f"revert_{link_id}",
    }


@router.get("/list")
def list_ubids(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    name: Optional[str] = Query(None, description="Filter by company name"),
    activity_status: Optional[str] = Query(None, description="Comma-separated activity statuses"),
    anchor_status: Optional[str] = Query(None, description="Comma-separated anchor statuses"),
    link_count: Optional[str] = Query(None, description="Filter by link count (1, 2, 3, 4+)"),
    departments: Optional[str] = Query(None, description="Comma-separated department system keys"),
    pincode: Optional[str] = Query(None, description="Filter by pincode"),
    db: Session = Depends(get_db)
):
    """
    Returns a paginated directory of all UBIDs with advanced filtering.
    Supports filtering by activity status, departments, and pincode.
    """
    offset = (page - 1) * page_size

    # Parse comma-separated filter params
    activity_status_list: List[str] = [s.strip() for s in activity_status.split(',') if s.strip()] if activity_status else []
    departments_list: List[str] = [s.strip() for s in departments.split(',') if s.strip()] if departments else []
    anchor_status_list: List[str] = [s.strip() for s in anchor_status.split(',') if s.strip()] if anchor_status else []
    pincode_val = pincode.strip() if pincode else None

    # Build cache key with all filter parameters
    filter_key_parts = [
        str(page),
        str(page_size),
        name or '',
        ','.join(sorted(activity_status_list)),
        ','.join(sorted(departments_list)),
        pincode_val or '',
    ]
    cache_key = f"ubid:list:{':'.join(filter_key_parts)}"
    
    # Check cache (skip if name search is used)
    if not name:
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

    # Start with base query
    query = db.query(UBIDEntity)

    # Apply anchor_status filter (kept for backwards compat)
    if anchor_status_list:
        query = query.filter(UBIDEntity.anchor_status.in_(anchor_status_list))

    # Apply activity_status filter (requires join with ActivityScore)
    if activity_status_list:
        query = query.join(
            ActivityScore,
            and_(
                ActivityScore.ubid == UBIDEntity.ubid,
                ActivityScore.is_current == True
            )
        ).filter(ActivityScore.activity_status.in_(activity_status_list))

    # Apply departments filter (EXISTS subquery matching any of the selected depts)
    if departments_list:
        dept_exists = exists().where(
            and_(
                UBIDSourceLink.ubid == UBIDEntity.ubid,
                UBIDSourceLink.source_system.in_(departments_list),
                UBIDSourceLink.is_active == True
            )
        )
        query = query.filter(dept_exists)
    # Apply pincode filter — find UBIDs where any linked source record has matching pin_code
    if pincode_val:
        from sqlalchemy import text as sa_text
        pincode_rows = db.execute(
            sa_text("""
                SELECT DISTINCT usl.ubid
                FROM ubid_source_links usl
                WHERE usl.is_active = true AND (
                    EXISTS (
                        SELECT 1 FROM dept_shop_establishment d
                        WHERE usl.source_system = 'shop_establishment'
                          AND usl.source_record_id = d.se_reg_no
                          AND d.pin_code = :pin
                    ) OR EXISTS (
                        SELECT 1 FROM dept_factories d
                        WHERE usl.source_system = 'factories'
                          AND usl.source_record_id = d.factory_licence_no
                          AND d.pin_code = :pin
                    ) OR EXISTS (
                        SELECT 1 FROM dept_labour d
                        WHERE usl.source_system = 'labour'
                          AND usl.source_record_id = d.employer_code
                          AND d.pin_code = :pin
                    ) OR EXISTS (
                        SELECT 1 FROM dept_kspcb d
                        WHERE usl.source_system = 'kspcb'
                          AND usl.source_record_id = d.consent_order_no
                          AND d.pin_code = :pin
                    )
                )
            """),
            {"pin": pincode_val}
        ).fetchall()
        valid_ubids = [row[0] for row in pincode_rows]
        if valid_ubids:
            query = query.filter(UBIDEntity.ubid.in_(valid_ubids))
        else:
            # No UBIDs match this pincode — return empty
            query = query.filter(UBIDEntity.ubid == None)

    # Apply link_count filter (subquery to count active links)
    if link_count:
        if link_count == '4+':
            # Count >= 4
            link_count_subquery = (
                db.query(UBIDSourceLink.ubid)
                .filter(UBIDSourceLink.is_active == True)
                .group_by(UBIDSourceLink.ubid)
                .having(func.count(UBIDSourceLink.link_id) >= 4)
            )
            query = query.filter(UBIDEntity.ubid.in_(link_count_subquery))
        else:
            # Exact count
            try:
                count_value = int(link_count)
                link_count_subquery = (
                    db.query(UBIDSourceLink.ubid)
                    .filter(UBIDSourceLink.is_active == True)
                    .group_by(UBIDSourceLink.ubid)
                    .having(func.count(UBIDSourceLink.link_id) == count_value)
                )
                query = query.filter(UBIDEntity.ubid.in_(link_count_subquery))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="link_count must be one of: 1, 2, 3, 4+"
                )

    # Apply departments filter (EXISTS subquery)
    if departments:
        for dept in departments:
            dept_exists = exists().where(
                and_(
                    UBIDSourceLink.ubid == UBIDEntity.ubid,
                    UBIDSourceLink.source_system == dept,
                    UBIDSourceLink.is_active == True
                )
            )
            query = query.filter(dept_exists)

    # Handle name search via ILIKE on source tables
    if name:
        from sqlalchemy import text as sa_text
        search_pattern = f"%{name.strip()}%"
        name_search_query = sa_text("""
            SELECT DISTINCT usl.ubid
            FROM ubid_source_links usl
            WHERE usl.is_active = true AND (
                EXISTS (
                    SELECT 1 FROM dept_shop_establishment d
                    WHERE usl.source_system = 'shop_establishment'
                      AND usl.source_record_id = d.se_reg_no
                      AND d.business_name ILIKE :name_pattern
                ) OR EXISTS (
                    SELECT 1 FROM dept_factories d
                    WHERE usl.source_system = 'factories'
                      AND usl.source_record_id = d.factory_licence_no
                      AND d.factory_name ILIKE :name_pattern
                ) OR EXISTS (
                    SELECT 1 FROM dept_labour d
                    WHERE usl.source_system = 'labour'
                      AND usl.source_record_id = d.employer_code
                      AND d.employer_name ILIKE :name_pattern
                ) OR EXISTS (
                    SELECT 1 FROM dept_kspcb d
                    WHERE usl.source_system = 'kspcb'
                      AND usl.source_record_id = d.consent_order_no
                      AND d.unit_name ILIKE :name_pattern
                )
            )
        """)
        matching_rows = db.execute(name_search_query, {"name_pattern": search_pattern}).fetchall()
        matching_ubids = [row[0] for row in matching_rows]
        
        if matching_ubids:
            query = query.filter(UBIDEntity.ubid.in_(matching_ubids))
        else:
            # No UBIDs match this name
            query = query.filter(UBIDEntity.ubid == None)

    # Resolve total and paginated entities
    total = query.count()
    entities = query.order_by(UBIDEntity.created_at.desc()).offset(offset).limit(page_size).all()

    # Build results with all required fields
    results = []
    for entity in entities:
        activity = db.query(ActivityScore).filter(
            ActivityScore.ubid == entity.ubid,
            ActivityScore.is_current == True
        ).first()

        link = db.query(UBIDSourceLink).filter(
            UBIDSourceLink.ubid == entity.ubid,
            UBIDSourceLink.is_active == True
        ).first()

        display_name = "Unknown Business"
        if link:
            display_name = _resolve_display_name(db, link.source_system, link.source_record_id)

        results.append({
            "ubid": entity.ubid,
            "display_name": display_name,
            "pan_anchor": entity.pan_anchor,
            "gstin_anchors": entity.gstin_anchors,
            "activity_status": activity.activity_status if activity else "UNKNOWN",
            "anchor_status": entity.anchor_status,  # NEW: Added anchor_status field
            "source_record_count": db.query(UBIDSourceLink).filter(
                UBIDSourceLink.ubid == entity.ubid,
                UBIDSourceLink.is_active == True
            ).count()
        })

    payload = {"total": total, "page": page, "page_size": page_size, "results": results}
    
    # Cache results (skip if name search is used)
    if not name:
        cache_set(cache_key, payload, ttl=UBID_LIST_TTL)
    
    return payload

@router.get("/lookup")
def lookup_ubid(
    pan: Optional[str] = Query(None),
    gstin: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    pincode: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Lookup a UBID by PAN, GSTIN, or name+pincode.
    Returns the UBID with all linked source records and current activity status.
    """
    entity = None

    if pan:
        entity = db.query(UBIDEntity).filter(
            UBIDEntity.pan_anchor == pan.upper()).first()

    elif gstin:
        # Search in gstin_anchors array
        entity = db.query(UBIDEntity).filter(
            UBIDEntity.gstin_anchors.contains([gstin.upper()])
        ).first()

    elif name and pincode:
        raise HTTPException(
            status_code=501,
            detail="Name search via full-text index — use /search endpoint")

    if not entity:
        raise HTTPException(status_code=404,
                            detail="No UBID found for the given identifiers")

    return _build_ubid_detail(entity, db)


@router.get("/{ubid}/full-details")
def get_ubid_full_details(ubid: str, db: Session = Depends(get_db)):
    """
    Return complete company information including all source record details,
    feature vectors, SHAP values, confidence statistics, and department coverage.
    
    This endpoint provides comprehensive data for the enhanced company detail view.
    Results are cached for 300 seconds.
    """
    cache_key = f"ubid:full-details:{ubid}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    # 1. Query ubid_entities for identity information
    entity = db.query(UBIDEntity).filter(UBIDEntity.ubid == ubid).first()
    if not entity:
        raise HTTPException(status_code=404, detail=f"UBID {ubid} not found")

    # 2. Query ubid_source_links for all active links
    links = db.query(UBIDSourceLink).filter(
        UBIDSourceLink.ubid == entity.ubid,
        UBIDSourceLink.is_active == True
    ).all()

    # 3. Get current activity score
    activity = db.query(ActivityScore).filter(
        ActivityScore.ubid == entity.ubid,
        ActivityScore.is_current == True
    ).first()

    # 4. For each link, fetch evidence and source record details
    source_records = []
    confidence_scores = []
    source_systems = []
    
    # Get display name from first link
    display_name = "Unknown Business"
    if links:
        first_link = links[0]
        display_name = _resolve_display_name(db, first_link.source_system, first_link.source_record_id)
    
    for link in links:
        # Query ubid_link_evidence for feature vector and SHAP values
        evidence = db.query(UBIDLinkEvidence).filter(
            UBIDLinkEvidence.link_id == link.link_id
        ).first()
        
        # Call _fetch_source_record_details() to get full source record
        source_record_details = _fetch_source_record_details(
            db, 
            link.source_system, 
            link.source_record_id
        )
        
        # Build complete source record with evidence
        source_record = {
            "link_id": link.link_id,
            "source_system": link.source_system,
            "source_record_id": link.source_record_id,
            "confidence": link.confidence,
            "link_type": link.link_type,
            "linked_at": str(link.linked_at),
            # Source record fields from helper function
            "business_name": source_record_details["business_name"],
            "address": source_record_details["address"],
            "pan": source_record_details["pan"],
            "gstin": source_record_details["gstin"],
            "phone": source_record_details["phone"],
            "pin_code": source_record_details["pin_code"],
            "owner_name": source_record_details["owner_name"],
            "registration_date": source_record_details["registration_date"],
            # Evidence data
            "feature_vector": evidence.feature_vector if evidence else {},
            "shap_values": evidence.shap_values if evidence else {},
            "calibrated_score": evidence.calibrated_score if evidence else 0.0
        }
        
        source_records.append(source_record)
        
        # Collect confidence scores for statistics
        if link.confidence is not None:
            confidence_scores.append(link.confidence)
        
        # Collect source systems for department coverage
        source_systems.append(link.source_system)
    
    # 5. Calculate confidence statistics using _calculate_confidence_stats()
    link_confidence_stats = _calculate_confidence_stats(confidence_scores)
    
    # 6. Calculate department coverage using _calculate_department_coverage()
    department_coverage = _calculate_department_coverage(source_systems)
    
    # 7. Build CompanyFullDetail response
    result = {
        "ubid": entity.ubid,
        "display_name": display_name,
        "pan_anchor": entity.pan_anchor,
        "gstin_anchors": entity.gstin_anchors or [],
        "anchor_status": entity.anchor_status,
        "activity_status": activity.activity_status if activity else "UNKNOWN",
        "activity_score": activity.raw_score if activity else None,
        "source_records": source_records,
        "link_confidence_stats": link_confidence_stats,
        "department_coverage": department_coverage,
        "created_at": str(entity.created_at)
    }
    
    cache_set(cache_key, result, ttl=UBID_DETAIL_TTL)
    
    return result


@router.get("/{ubid}/export")
def export_ubid(
    ubid: str,
    format: Optional[str] = Query("csv", description="Export format: json or csv"),
    db: Session = Depends(get_db)
):
    """
    Export UBID data as JSON or CSV.
    Returns a downloadable file with all UBID details and linked source records.
    """
    import csv
    import io
    import json
    from fastapi.responses import Response

    entity = db.query(UBIDEntity).filter(UBIDEntity.ubid == ubid).first()
    if not entity:
        raise HTTPException(status_code=404, detail=f"UBID {ubid} not found")

    detail = _build_ubid_detail(entity, db)

    if format == "json":
        content = json.dumps(detail, indent=2, default=str)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={ubid}_export.json"}
        )
    else:
        # CSV: flatten source records
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ubid", "pan_anchor", "anchor_status", "activity_status", "activity_score",
                         "source_system", "source_record_id", "link_type", "confidence", "linked_at"])
        for rec in detail.get("source_records", []):
            writer.writerow([
                detail["ubid"],
                detail.get("pan_anchor", ""),
                detail.get("anchor_status", ""),
                detail.get("activity_status", ""),
                detail.get("activity_score", ""),
                rec.get("source_system", ""),
                rec.get("source_record_id", ""),
                rec.get("link_type", ""),
                rec.get("confidence", ""),
                rec.get("linked_at", ""),
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={ubid}_export.csv"}
        )


@router.get("/{ubid}")
def get_ubid_detail(ubid: str, db: Session = Depends(get_db)):
    cache_key = f"ubid:detail:{ubid}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    entity = db.query(UBIDEntity).filter(UBIDEntity.ubid == ubid).first()
    if not entity:
        raise HTTPException(status_code=404, detail=f"UBID {ubid} not found")

    result = _build_ubid_detail(entity, db)
    cache_set(cache_key, result, ttl=UBID_DETAIL_TTL)
    return result


def _build_ubid_detail(entity: UBIDEntity, db: Session) -> dict:
    """Build the full UBID detail response with all linked records and evidence."""
    # Get all source links
    links = db.query(UBIDSourceLink).filter(
        UBIDSourceLink.ubid == entity.ubid,
        UBIDSourceLink.is_active
    ).all()

    # Get current activity score
    activity = db.query(ActivityScore).filter(
        ActivityScore.ubid == entity.ubid,
        ActivityScore.is_current
    ).first()

    # Get link evidence for each link
    source_records_with_evidence = []
    for link in links:
        evidence = db.query(UBIDLinkEvidence).filter(
            UBIDLinkEvidence.link_id == link.link_id
        ).first()

        source_records_with_evidence.append({
            "source_system": link.source_system,
            "source_record_id": link.source_record_id,
            "confidence": link.confidence,
            "link_type": link.link_type,
            "linked_at": str(link.linked_at),
            "evidence": {
                "feature_vector": evidence.feature_vector if evidence else None,
                "shap_values": evidence.shap_values if evidence else None,
                "calibrated_score": evidence.calibrated_score if evidence else None
            } if evidence else None
        })

    # Generate ai_explanation if there are linked records (MOVED TO /intelligence ENDPOINT)
    ai_explanation = None

    return {
        "ubid": entity.ubid,
        "pan_anchor": entity.pan_anchor,
        "gstin_anchors": entity.gstin_anchors,
        "anchor_status": entity.anchor_status,
        "activity_status": activity.activity_status if activity else "UNKNOWN",
        "activity_score": activity.raw_score if activity else None,
        "source_records": source_records_with_evidence,
        "source_record_count": len(source_records_with_evidence),
        "created_at": str(entity.created_at),
        "ai_explanation": ai_explanation
    }


@router.get("/{ubid}/intelligence")
def get_ubid_intelligence(ubid: str, db: Session = Depends(get_db)):
    """
    Returns enriched analytics intelligence for a UBID:
    - KPI metrics (dormancy ETA, anomaly count, er_confidence)
    - Signal anomaly detection (cross-dept conflicts)
    - Active signal weights with decay
    - Activity score history (reconstructed from events)
    - Sector peer benchmark
    - LLM compliance narrative (Gemini -> Groq -> fallback)
    """
    import math
    from datetime import datetime, timezone, timedelta
    from src.database.models import UBIDActivityEvent

    entity = db.query(UBIDEntity).filter(UBIDEntity.ubid == ubid).first()
    if not entity:
        raise HTTPException(status_code=404, detail="UBID not found")

    activity = db.query(ActivityScore).filter(
        ActivityScore.ubid == ubid, ActivityScore.is_current == True
    ).first()

    links = db.query(UBIDSourceLink).filter(
        UBIDSourceLink.ubid == ubid, UBIDSourceLink.is_active == True
    ).all()

    events = db.query(UBIDActivityEvent).filter(
        UBIDActivityEvent.ubid == ubid
    ).order_by(UBIDActivityEvent.event_timestamp.desc()).all()

    now = datetime.now(timezone.utc)

    # ── 1. Signal weights with decay ──────────────────────────────────────────
    SIGNAL_WEIGHTS = {
        "electricity_consumption_high": +0.90,
        "water_consumption_high": +0.70,
        "licence_renewal": +0.80,
        "inspection_visit": +0.70,
        "compliance_filing": +0.75,
        "administrative_update": +0.40,
        "electricity_consumption_low": -0.50,
        "renewal_overdue": -0.40,
        "closure_declaration": -1.00,
        "licence_cancellation": -0.90,
        "safety_inspection": +0.70,
        "environmental_inspection": +0.65,
    }
    SIGNAL_HALF_LIVES = {
        "electricity_consumption_high": 45, "water_consumption_high": 45,
        "licence_renewal": 365, "inspection_visit": 180,
        "compliance_filing": 270, "administrative_update": 90,
        "electricity_consumption_low": 30, "renewal_overdue": 180,
        "closure_declaration": None, "licence_cancellation": None,
        "safety_inspection": 180, "environmental_inspection": 180,
    }

    # Collect the most recent event of each type
    seen_types: dict = {}
    for ev in events:
        if ev.event_type not in seen_types:
            ts = ev.event_timestamp
            if ts and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            days_since = (now - ts).days if ts else 9999
            seen_types[ev.event_type] = {
                "event_type": ev.event_type,
                "days_since": days_since,
                "source_system": ev.source_system,
                "timestamp": str(ev.event_timestamp)[:10] if ev.event_timestamp else None,
            }

    active_signals = []
    for etype, info in seen_types.items():
        base_weight = SIGNAL_WEIGHTS.get(etype, ev.signal_weight or 0.0)
        half_life = SIGNAL_HALF_LIVES.get(etype)
        days_since = info["days_since"]
        if half_life is None:
            decay = 1.0
        else:
            lam = math.log(2) / half_life
            decay = math.exp(-lam * days_since)
        effective = round(base_weight * decay, 3)
        active_signals.append({
            "event_type": etype,
            "base_weight": base_weight,
            "half_life_days": half_life,
            "days_since": days_since,
            "effective_weight": effective,
            "source_system": info["source_system"],
            "last_seen": info["timestamp"],
        })
    active_signals.sort(key=lambda x: abs(x["effective_weight"]), reverse=True)

    # ── 2. Dormancy ETA ───────────────────────────────────────────────────────
    THRESHOLD_DORMANT_LOW = -0.2
    current_score = activity.raw_score if activity else 0.0
    dormancy_eta_days = None
    if current_score > THRESHOLD_DORMANT_LOW:
        # Estimate days until net positive signals decay to threshold
        positive_effective = sum(s["effective_weight"] for s in active_signals if s["effective_weight"] > 0)
        negative_effective = sum(s["effective_weight"] for s in active_signals if s["effective_weight"] < 0)
        net = positive_effective + negative_effective
        if net > THRESHOLD_DORMANT_LOW:
            # Find dominant decaying positive signal
            dominant = next((s for s in active_signals if s["effective_weight"] > 0 and s["half_life_days"]), None)
            if dominant and dominant["half_life_days"]:
                lam = math.log(2) / dominant["half_life_days"]
                # solve: effective * e^(-lam*t) + negative = threshold
                target_positive = THRESHOLD_DORMANT_LOW - negative_effective
                if target_positive < dominant["effective_weight"] and dominant["effective_weight"] > 0:
                    dormancy_eta_days = max(0, int(math.log(dominant["effective_weight"] / max(0.01, abs(target_positive))) / lam))

    # ── 3. Anomaly detection ──────────────────────────────────────────────────
    anomalies = []
    event_types_seen = {s["event_type"] for s in active_signals}
    source_systems_present = {lnk.source_system for lnk in links}

    # Critical: Closure signal + active environmental consent
    if "closure_declaration" in event_types_seen and "kspcb" in source_systems_present:
        closure_date = seen_types.get("closure_declaration", {}).get("timestamp", "Unknown date")
        anomalies.append({
            "severity": "CRITICAL",
            "title": "Closure declaration vs active KSPCB consent",
            "description": "Closure filed with Factories Dept conflicts with active environmental consent. Signal conflict: −1.00 permanent vs +0.65 KSPCB.",
            "date": closure_date,
        })

    # Warning: High electricity + no inspection > 12 months
    if "electricity_consumption_high" in event_types_seen:
        insp = seen_types.get("inspection_visit") or seen_types.get("safety_inspection")
        if insp and insp["days_since"] > 365:
            anomalies.append({
                "severity": "WARNING",
                "title": f"High electricity draw with no inspection in {insp['days_since']}d",
                "description": f"Power consumption signals active operations (+0.90) but last inspection was {insp['days_since']} days ago (half-life: 180d — nearly fully decayed).",
                "date": insp.get("timestamp", "Unknown"),
            })

    # Warning: Renewal overdue
    if "renewal_overdue" in event_types_seen:
        overdue = seen_types["renewal_overdue"]
        anomalies.append({
            "severity": "WARNING",
            "title": "Licence renewal overdue",
            "description": f"Licence renewal is overdue as of {overdue.get('timestamp', 'unknown date')}. This reduces activity score by −0.40.",
            "date": overdue.get("timestamp", ""),
        })

    # OK: Recent licence renewal
    if "licence_renewal" in event_types_seen:
        renewal = seen_types["licence_renewal"]
        if renewal["days_since"] < 180:
            anomalies.append({
                "severity": "OK",
                "title": "Licence renewal aligns with business cycle",
                "description": f"Renewed {renewal['days_since']} days ago — within expected annual cycle.",
                "date": renewal.get("timestamp", ""),
            })

    # ── 4. Activity score history (from events) ───────────────────────────────
    # Reconstruct monthly score snapshots using running sum of decayed weights
    score_history = []
    if events:
        oldest_event = events[-1].event_timestamp
        if oldest_event and oldest_event.tzinfo is None:
            oldest_event = oldest_event.replace(tzinfo=timezone.utc)
        months_back = min(18, max(6, (now - oldest_event).days // 30 + 1)) if oldest_event else 12

        for m in range(months_back - 1, -1, -1):
            month_date = now - timedelta(days=m * 30)
            month_label = month_date.strftime("%b %y")
            # Compute score as of that month using events before it
            running = 0.0
            for ev in events:
                ts = ev.event_timestamp
                if ts and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if not ts or ts > month_date:
                    continue
                base_w = SIGNAL_WEIGHTS.get(ev.event_type, ev.signal_weight or 0.0)
                hl = SIGNAL_HALF_LIVES.get(ev.event_type)
                days_ago = (month_date - ts).days
                decay = 1.0 if hl is None else math.exp(-math.log(2) / hl * days_ago)
                running += base_w * decay
            score_history.append({"month": month_label, "score": round(max(-1.0, min(1.0, running)), 3)})

    # ── 5. Peer benchmark ─────────────────────────────────────────────────────
    peer_benchmark = None
    try:
        # Find pincode + NIC code from source records
        pin_code = None
        nic_code = None
        for lnk in links:
            if lnk.source_system == "factories":
                row = db.query(DeptFactories).filter(
                    DeptFactories.factory_licence_no == lnk.source_record_id).first()
                if row:
                    pin_code = pin_code or row.pin_code
                    nic_code = nic_code or row.nic_code
            elif lnk.source_system == "shop_establishment":
                row = db.query(DeptShopEstablishment).filter(
                    DeptShopEstablishment.se_reg_no == lnk.source_record_id).first()
                if row:
                    pin_code = pin_code or row.pin_code
                    nic_code = nic_code or getattr(row, "nic_code", None)

        if pin_code:
            # Find peer UBIDs in same pincode via source links
            from sqlalchemy import text as sql_text
            peer_ubids_q = db.query(UBIDSourceLink.ubid).join(
                DeptShopEstablishment,
                (UBIDSourceLink.source_system == "shop_establishment") &
                (UBIDSourceLink.source_record_id == DeptShopEstablishment.se_reg_no)
            ).filter(DeptShopEstablishment.pin_code == pin_code, UBIDSourceLink.ubid != ubid)

            peer_ubids = [r[0] for r in peer_ubids_q.limit(500).all()]

            if peer_ubids:
                peer_scores = db.query(ActivityScore.raw_score).filter(
                    ActivityScore.ubid.in_(peer_ubids),
                    ActivityScore.is_current == True,
                ).all()
                peer_score_vals = [r[0] for r in peer_scores if r[0] is not None]

                if peer_score_vals:
                    avg_peer = sum(peer_score_vals) / len(peer_score_vals)
                    # Find inspection age for this entity
                    insp_ev = seen_types.get("inspection_visit") or seen_types.get("safety_inspection")
                    insp_days = insp_ev["days_since"] if insp_ev else None
                    renewal_ev = seen_types.get("licence_renewal")
                    renewal_days = renewal_ev["days_since"] if renewal_ev else None

                    peer_benchmark = {
                        "peer_count": len(peer_ubids),
                        "peer_avg_score": round(avg_peer, 3),
                        "this_score": current_score,
                        "score_percentile": round(
                            sum(1 for s in peer_score_vals if s < current_score) / len(peer_score_vals) * 100, 1),
                        "inspection_age_days": insp_days,
                        "licence_days_ago": renewal_days,
                        "dept_coverage": len(links),
                        "max_dept_coverage": 4,
                        "pincode": pin_code,
                        "nic_code": nic_code,
                    }
    except Exception:
        peer_benchmark = None

    # ── 6. LLM narrative ─────────────────────────────────────────────────────
    llm_narrative = None
    try:
        from src.llm_router import route, TaskType
        display_name = _resolve_display_name(
            db, links[0].source_system, links[0].source_record_id) if links else ubid
        status_str = activity.activity_status if activity else "UNKNOWN"
        score_str = f"{current_score:.3f}" if current_score else "N/A"

        signals_summary = "; ".join(
            f"{s['event_type'].replace('_', ' ')} (effective: {s['effective_weight']:+.2f}, {s['days_since']}d ago)"
            for s in active_signals[:5]
        )
        anomaly_summary = "; ".join(
            f"[{a['severity']}] {a['title']}" for a in anomalies
        ) if anomalies else "No significant anomalies detected"

        prompt = (
            f"Business: {display_name}\n"
            f"UBID: {ubid}\n"
            f"Activity Status: {status_str} (score: {score_str})\n"
            f"Linked Departments: {', '.join(lnk.source_system.replace('_', ' ').title() for lnk in links)}\n"
            f"Active Signals: {signals_summary}\n"
            f"Anomalies: {anomaly_summary}\n"
            f"Dormancy ETA: {'~' + str(dormancy_eta_days) + ' days at current decay rate' if dormancy_eta_days else 'Stable'}\n\n"
            "Write a 3-sentence compliance intelligence narrative for a government officer. "
            "Sentence 1: summarize the current operational status with key signals. "
            "Sentence 2: highlight the most critical anomaly or concern. "
            "Sentence 3: recommend the most important action (inspection, reconciliation, or closure confirmation). "
            "Be specific, factual, and professional. Do NOT use markdown."
        )
        llm_narrative = route(TaskType.ACTIVITY_EXPLANATION, prompt, max_tokens=200)
    except Exception:
        # Fallback rule-based narrative
        status_str = activity.activity_status if activity else "UNKNOWN"
        if anomalies:
            top = anomalies[0]
            llm_narrative = (
                f"This business is classified as {status_str} based on {len(active_signals)} active signals. "
                f"A {top['severity'].lower()} anomaly was detected: {top['title']}. "
                f"{'Recommend scheduling a cross-department reconciliation inspection.' if top['severity'] == 'CRITICAL' else 'Recommend a follow-up inspection to verify operational status.'}"
            )
        else:
            llm_narrative = (
                f"This business is classified as {status_str} with {len(active_signals)} active signals from {len(links)} linked departments. "
                f"No critical anomalies detected. "
                f"{'Routine monitoring recommended.' if status_str == 'ACTIVE' else 'Consider scheduling an inspection to verify current operational status.'}"
            )

    return {
        "kpi": {
            "activity_score": current_score,
            "er_confidence": max((lnk.confidence for lnk in links if hasattr(lnk, 'confidence') and lnk.confidence), default=None),
            "dept_count": len(links),
            "dormancy_eta_days": dormancy_eta_days,
            "anomaly_count": len(anomalies),
        },
        "anomalies": anomalies,
        "active_signals": active_signals,
        "score_history": score_history,
        "peer_benchmark": peer_benchmark,
        "llm_narrative": llm_narrative,
    }
