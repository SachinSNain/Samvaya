"""
database/models.py
Complete SQLAlchemy ORM definitions for all 11 tables.

Tables:
  Source system (read-only simulation):
    dept_shop_establishment
    dept_factories
    dept_labour
    dept_kspcb
    activity_events_raw

  UBID Registry (platform-owned):
    ubid_entities
    ubid_source_links
    ubid_link_evidence
    review_tasks
    ubid_activity_events
    activity_scores
    unmatched_events
"""
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text,
    ForeignKey, Index, BigInteger,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, TSVECTOR
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


# ═══════════════════════════════════════════════════════════
#  SOURCE SYSTEM TABLES  (simulate dept databases, read-only)
# ═══════════════════════════════════════════════════════════

class DeptShopEstablishment(Base):
    """Simulated Shop & Establishment department export."""
    __tablename__ = "dept_shop_establishment"

    se_reg_no = Column(String(30), primary_key=True)
    business_name = Column(String(255), nullable=False)
    owner_name = Column(String(100))
    address = Column(Text)
    pin_code = Column(String(6), index=True)
    pan = Column(String(10), index=True)
    gstin = Column(String(15), index=True)
    phone = Column(String(15))
    trade_category = Column(String(100))
    registration_date = Column(DateTime)
    status = Column(String(20))
    # ground truth link — NEVER exposed to the pipeline logic
    entity_id = Column(String(15))


class DeptFactories(Base):
    """Simulated Factories department export."""
    __tablename__ = "dept_factories"

    factory_licence_no = Column(String(30), primary_key=True)
    factory_name = Column(String(255), nullable=False)
    owner_name = Column(String(100))
    address = Column(Text)
    pin_code = Column(String(6), index=True)
    pan = Column(String(10), index=True)
    gstin = Column(String(15), index=True)
    phone = Column(String(15))
    product_description = Column(Text)
    nic_code = Column(String(6))
    num_workers = Column(Integer)
    licence_valid_until = Column(DateTime)
    registration_date = Column(DateTime)
    status = Column(String(20))
    entity_id = Column(String(15))


class DeptLabour(Base):
    """Simulated Labour department export."""
    __tablename__ = "dept_labour"

    employer_code = Column(String(30), primary_key=True)
    employer_name = Column(String(255), nullable=False)
    owner_name = Column(String(100))
    address = Column(Text)
    pin_code = Column(String(6), index=True)
    pan = Column(String(10), index=True)
    gstin = Column(String(15), index=True)
    phone = Column(String(15))
    industry_type = Column(String(100))
    num_employees = Column(Integer)
    registration_date = Column(DateTime)
    status = Column(String(20))
    entity_id = Column(String(15))


class DeptKSPCB(Base):
    """Simulated Karnataka State Pollution Control Board export."""
    __tablename__ = "dept_kspcb"

    consent_order_no = Column(String(30), primary_key=True)
    unit_name = Column(String(255), nullable=False)
    owner_name = Column(String(100))
    address = Column(Text)
    pin_code = Column(String(6), index=True)
    pan = Column(String(10), index=True)
    gstin = Column(String(15), index=True)
    phone = Column(String(15))
    nic_code = Column(String(6))
    consent_type = Column(String(20))   # 'establish' or 'operate'
    consent_valid_until = Column(DateTime)
    registration_date = Column(DateTime)
    status = Column(String(20))
    entity_id = Column(String(15))


class ActivityEventRaw(Base):
    """
    Raw inbound activity events from all source systems.
    processed=False rows are picked up by event_router.py.
    """
    __tablename__ = "activity_events_raw"

    event_id = Column(String(40), primary_key=True)
    source_system = Column(String(50), nullable=False)
    source_record_id = Column(String(50), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_timestamp = Column(DateTime, nullable=False)
    payload = Column(JSONB)
    entity_id = Column(String(15))   # ground truth — never used by pipeline
    processed = Column(Boolean, default=False, index=True)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index(
            "idx_activity_events_source",
            "source_system",
            "source_record_id"),
        Index(
            "idx_activity_events_ts",
            "event_timestamp"),
    )


# ═══════════════════════════════════════════════════════════
#  UBID REGISTRY TABLES  (platform's own storage)
# ═══════════════════════════════════════════════════════════

class UBIDEntity(Base):
    """
    One row per unique real-world business entity.
    The UBID is the single canonical identifier (KA-UBID-XXXXXX).
    """
    __tablename__ = "ubid_entities"

    ubid = Column(String(20), primary_key=True)        # KA-UBID-XXXXXX
    pan_anchor = Column(String(10), index=True)
    gstin_anchors = Column(ARRAY(String))
    # ACTIVE / DORMANT / CLOSED_SUSPECTED / CLOSED_CONFIRMED
    activity_status = Column(String(20), default="UNKNOWN")
    anchor_status = Column(
        String(20),
        default="UNANCHORED")    # ANCHORED / UNANCHORED
    # STANDALONE / SUBSIDIARY / PARENT
    relationship_type = Column(String(20), default="STANDALONE")
    parent_ubid = Column(
        String(20),
        ForeignKey("ubid_entities.ubid"),
        nullable=True)
    # Full-text search vector — populated by DB trigger (see migration)
    name_tsv = Column(TSVECTOR, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    __table_args__ = (
        Index("idx_ubid_pan", "pan_anchor"),
        Index("idx_ubid_status", "activity_status"),
        Index("idx_ubid_name_tsv", "name_tsv", postgresql_using="gin"),
    )


class UBIDSourceLink(Base):
    """
    Maps each department record (source_system + source_record_id)
    to its UBID. A UBID can have many source links.
    """
    __tablename__ = "ubid_source_links"

    link_id = Column(String(40), primary_key=True)
    ubid = Column(
        String(20),
        ForeignKey("ubid_entities.ubid"),
        nullable=False,
        index=True)
    source_system = Column(String(50), nullable=False)
    source_record_id = Column(String(50), nullable=False)
    confidence = Column(Float)
    link_type = Column(String(10))       # 'auto' or 'manual'
    linked_by = Column(String(50))       # 'system' or reviewer user ID
    linked_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_source_link_source", "source_system", "source_record_id"),
        Index("idx_source_link_ubid", "ubid"),
    )


class UBIDLinkEvidence(Base):
    """
    Stores the feature vector and SHAP values for each auto-link decision.
    Allows explainability — why were two records linked?
    """
    __tablename__ = "ubid_link_evidence"

    evidence_id = Column(String(40), primary_key=True)
    link_id = Column(
        String(40),
        ForeignKey("ubid_source_links.link_id"),
        nullable=True,
        index=True)
    pair_record_a = Column(String(80))      # "source_system:source_record_id"
    pair_record_b = Column(String(80))
    feature_vector = Column(JSONB)           # {F01: 0.92, F02: 87.3, ...}
    shap_values = Column(JSONB)           # {F01: +0.32, F02: +0.18, ...}
    raw_score = Column(Float)
    calibrated_score = Column(Float)
    # 'AUTO_LINK' / 'REVIEW' / 'KEEP_SEPARATE'
    decision = Column(String(20))
    model_version = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())


class ReviewTask(Base):
    """
    Human review queue — pairs that scored between the review and auto-link thresholds.
    Reviewers confirm or reject proposed links.
    """
    __tablename__ = "review_tasks"

    task_id = Column(String(40), primary_key=True)
    pair_record_a = Column(String(80), nullable=False)
    pair_record_b = Column(String(80), nullable=False)
    evidence_id = Column(String(40), ForeignKey(
        "ubid_link_evidence.evidence_id"))
    calibrated_score = Column(Float)
    assigned_to = Column(String(50))
    status = Column(String(20), default="PENDING")
    # PENDING / IN_REVIEW / DECIDED / DEFERRED
    decision = Column(String(30))
    # CONFIRM_MATCH / CONFIRM_NON_MATCH / CONFIRM_PARTIAL / REQUEST_INFO / DEFER
    decision_reason = Column(Text)
    decided_by = Column(String(50))
    decided_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    priority = Column(Integer, default=5)   # 1 = highest, 10 = lowest
    reviewer_summary = Column(Text)   # Gemini 2.5 Flash pre-generated (scrambled inputs)
    reviewer_notes = Column(Text)   # Llama 3.1 8B on-demand (raw canonical fields)

    __table_args__ = (
        Index("idx_review_status", "status"),
        Index("idx_review_priority", "priority"),
        Index("idx_review_score", "calibrated_score"),
    )


class UBIDActivityEvent(Base):
    """
    Activity events that have been successfully routed to a UBID.
    Fed into signal_scorer.py to compute the Activity Score.
    """
    __tablename__ = "ubid_activity_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ubid = Column(
        String(20),
        ForeignKey("ubid_entities.ubid"),
        nullable=False,
        index=True)
    source_event_id = Column(String(40))
    event_type = Column(String(50), nullable=False)
    source_system = Column(String(50))
    event_timestamp = Column(DateTime, nullable=False)
    signal_weight = Column(Float)
    half_life_days = Column(Integer)
    payload = Column(JSONB)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_activity_ubid_ts", "ubid", "event_timestamp"),
        Index("idx_activity_type", "event_type"),
    )


class ActivityScore(Base):
    """
    Current and historical activity scores per UBID.
    Only one row per UBID has is_current=True at any time.
    """
    __tablename__ = "activity_scores"

    score_id = Column(String(40), primary_key=True)
    ubid = Column(
        String(20),
        ForeignKey("ubid_entities.ubid"),
        nullable=False,
        index=True)
    computed_at = Column(DateTime, server_default=func.now())
    raw_score = Column(Float)
    # ACTIVE / DORMANT / CLOSED_SUSPECTED / CLOSED_CONFIRMED
    activity_status = Column(String(30))
    lookback_days = Column(Integer, default=365)
    evidence_snapshot = Column(JSONB)       # Full list of contributing signals
    is_current = Column(Boolean, default=True, index=True)
    manually_overridden = Column(Boolean, default=False)
    override_by = Column(String(50))
    override_reason = Column(Text)

    __table_args__ = (
        Index("idx_score_ubid_current", "ubid", "is_current"),
        Index("idx_score_status", "activity_status"),
    )


class UnmatchedEvent(Base):
    """
    Activity events that could not be routed to any UBID.
    Stored here for triage rather than being silently dropped.
    """
    __tablename__ = "unmatched_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_event_id = Column(String(40))
    source_system = Column(String(50))
    source_record_id = Column(String(50))
    event_type = Column(String(50))
    event_timestamp = Column(DateTime)
    payload = Column(JSONB)
    # 'NO_SOURCE_LINK' / 'UNKNOWN_SOURCE'
    reason_unmatched = Column(String(100))
    triage_status = Column(String(20), default="PENDING")
    accumulated_count = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_unmatched_source", "source_system", "source_record_id"),
        Index("idx_unmatched_triage", "triage_status"),
    )


class AuditEvent(Base):
    """
    Immutable audit trail for all platform actions.
    Written by API middleware and helpers — never deleted.
    """
    __tablename__ = "audit_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type = Column(String(60), nullable=False)   # review_decision, pipeline_triggered, …
    actor = Column(String(100), nullable=False)        # reviewer ID or "system"
    target_id = Column(String(80))                     # ubid / task_id / etc.
    detail = Column(JSONB, default={})                 # arbitrary context
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_actor", "actor"),
        Index("idx_audit_created", "created_at"),
    )
