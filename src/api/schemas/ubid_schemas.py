"""
API schemas for UBID Directory Enhancement endpoints.

This module defines Pydantic models for request/response validation
in the enhanced UBID Directory API endpoints.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class FilterState(BaseModel):
    """Filter state for directory listing."""
    activity_status: Optional[List[str]] = None
    anchor_status: Optional[List[str]] = None
    link_count: Optional[str] = None
    departments: Optional[List[str]] = None


class UBIDListItem(BaseModel):
    """Single UBID item in directory listing."""
    ubid: str
    display_name: str
    pan_anchor: Optional[str]
    gstin_anchors: List[str]
    activity_status: str
    anchor_status: str
    source_record_count: int

    class Config:
        from_attributes = True


class UBIDListResponse(BaseModel):
    """Paginated response for directory listing."""
    total: int
    page: int
    page_size: int
    results: List[UBIDListItem]


class SourceRecordDetail(BaseModel):
    """Complete source record with evidence."""
    link_id: str
    source_system: str
    source_record_id: str
    confidence: float
    link_type: str
    linked_at: str
    # Source record fields
    business_name: str
    address: str
    pan: Optional[str] = None
    gstin: Optional[str] = None
    phone: Optional[str] = None
    pin_code: Optional[str] = None
    owner_name: Optional[str] = None
    registration_date: Optional[str] = None
    # Evidence
    feature_vector: Dict[str, float]
    shap_values: Dict[str, float]
    calibrated_score: float

    class Config:
        from_attributes = True


class ConfidenceStats(BaseModel):
    """Link confidence statistics."""
    min: float
    max: float
    avg: float
    distribution: List[Dict[str, Any]]


class DepartmentCoverage(BaseModel):
    """Department record counts."""
    shop_establishment: int = 0
    factories: int = 0
    labour: int = 0
    kspcb: int = 0


class CompanyFullDetail(BaseModel):
    """Complete company information with all nested structures."""
    ubid: str
    display_name: str
    pan_anchor: Optional[str] = None
    gstin_anchors: List[str]
    anchor_status: str
    activity_status: str
    activity_score: Optional[float] = None
    source_records: List[SourceRecordDetail]
    link_confidence_stats: ConfidenceStats
    department_coverage: DepartmentCoverage
    created_at: str

    class Config:
        from_attributes = True


class RevertLinkRequest(BaseModel):
    """Request to revert a UBID link."""
    link_id: str
    reason: str = Field(..., min_length=10, max_length=500)


class RevertLinkResponse(BaseModel):
    """Response from revert link operation."""
    success: bool
    message: str
    affected_ubids: List[Dict[str, Any]]
    audit_event_id: str


class FilterOption(BaseModel):
    """Single filter option with count."""
    value: str
    label: str
    count: int


class FilterOptions(BaseModel):
    """Available filter options with counts."""
    activity_statuses: List[FilterOption]
    anchor_statuses: List[FilterOption]
    link_counts: List[FilterOption]
    departments: List[FilterOption]
