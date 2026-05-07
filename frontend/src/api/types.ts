export interface FilterState {
  activity_status: string[];
  departments: string[];
  pincode: string;
}

export interface FilterOption {
  label: string;
  value: string;
  count: number;
}

export interface FilterOptions {
  activity_status: FilterOption[];
  departments: FilterOption[];
}

export interface UBIDListItem {
  ubid: string;
  display_name: string;
  activity_status: string;
  anchor_status: string;
  pan_anchor?: string;
  source_record_count: number;
}

export interface UBIDListResponse {
  results: UBIDListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface SourceRecordDetail {
  source_system: string;
  source_record_id: string;
  link_type: string;
  confidence: number;
  evidence: {
    shap_values?: Record<string, number>;
    feature_vector?: Record<string, any>;
  };
  record_details: {
    business_name?: string;
    address?: string;
    PAN?: string;
    GSTIN?: string;
    phone?: string;
    pin_code?: string;
    owner_name?: string;
    registration_date?: string;
    [key: string]: any;
  };
}

export interface ConfidenceStats {
  min: number;
  max: number;
  avg: number;
  high_confidence_count: number;
  medium_confidence_count: number;
  low_confidence_count: number;
}

export interface DepartmentCoverage {
  shop_establishment: number;
  factories: number;
  labour: number;
  kspcb: number;
}

export interface CompanyFullDetail {
  ubid: string;
  display_name: string;
  activity_status: string;
  activity_score: number;
  anchor_status: string;
  pan_anchor?: string;
  gstin_anchors?: string[];
  source_record_count: number;
  confidence_stats: ConfidenceStats;
  department_coverage: DepartmentCoverage;
  source_records: SourceRecordDetail[];
  ai_explanation?: string;
}

export interface RevertLinkRequest {
  link_id: string;
  reason?: string;
}

export interface RevertLinkResponse {
  success: boolean;
  message: string;
  new_ubid?: string;
  audit_event_id: string;
}
