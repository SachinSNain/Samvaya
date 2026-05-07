# Samvaya — Future Scope & Improvements

> This document outlines planned enhancements for the Samvaya entity-resolution and business-intelligence platform. Each section builds on the current working prototype and is independent — teams can prioritise them in any order.

---

## Table of Contents

1. [ML Pipeline Enhancements](#1-ml-pipeline-enhancements)
2. [Activity Intelligence Upgrades](#2-activity-intelligence-upgrades)
3. [Data Integration & Ingestion](#3-data-integration--ingestion)
4. [Review Workflow Improvements](#4-review-workflow-improvements)
5. [Analytics & Reporting](#5-analytics--reporting)
6. [Natural Language Interface](#6-natural-language-interface)
7. [Scalability & Infrastructure](#7-scalability--infrastructure)
8. [User Experience & Frontend](#8-user-experience--frontend)
9. [Compliance & Governance](#9-compliance--governance)
10. [API & Ecosystem](#10-api--ecosystem)

---

## 1. ML Pipeline Enhancements

### 1.1 Incremental / Online Retraining
The current model is trained once on a fixed synthetic dataset. As reviewers make decisions (CONFIRM_MATCH / CONFIRM_NON_MATCH), those labelled pairs accumulate in the database. A scheduled Celery task could periodically fine-tune the LightGBM model on the new labels using warm-start training, so accuracy improves continuously without a full retrain.

### 1.2 Active Learning for Review Queue Prioritisation
Instead of routing all pairs with confidence [0.75, 0.95) to reviewers, implement an uncertainty sampling loop: rank queued items by the model's entropy, then surface the ones where a label would most reduce model uncertainty. This shrinks human review burden while maximising each label's informational value.

### 1.3 Confidence Intervals & Calibration Drift Detection
Track calibration metrics (Expected Calibration Error, reliability diagrams) over rolling time windows. Alert admins when calibration drift is detected, suggesting a recalibration run. This is important when new departments onboard and the feature distribution shifts.

### 1.4 Graph-Based Clustering
The current UBID assigner uses threshold-based connected components. Replace it with a learned graph embedding (e.g., GraphSAGE or Node2Vec) so that transitive relationships — *A matches B*, *B matches C*, but *A-C score* is just below threshold — are captured more reliably, especially for large business groups with subsidiaries.

### 1.5 Cross-Feature Interaction Discovery
Add automated feature engineering: compute pairwise interaction terms (e.g., PAN_match × geo_distance) and run permutation importance to identify which interactions the current 14 features miss. This can close recall gaps without bloating the feature vector.

### 1.6 Embedding Model Fine-Tuning (F14)
The multilingual semantic embedding (feature F14) currently uses a pretrained sentence-transformer. Fine-tune the model on domain-specific Indian business name pairs using contrastive learning, which should substantially improve recall for abbreviated names, transliterated names, and regional language variants.

---

## 2. Activity Intelligence Upgrades

### 2.1 Temporal Activity Forecasting
Use the historical event timeline per UBID to train a simple time-series classifier (LSTM or Prophet) that predicts whether a business will transition from ACTIVE → DORMANT within the next 90 days. This enables proactive outreach instead of reactive detection.

### 2.2 Custom Signal Profiles Per Industry
Different NIC sectors have naturally different filing cadences (a seasonal factory vs. a retail shop). Allow admins to define per-NIC-code signal weights and half-lives, so the thresholds for ACTIVE/DORMANT are industry-aware rather than global.

### 2.3 Anomaly Detection on Event Streams
Flag unusual event patterns — e.g., a flood of compliance filings submitted in one day after years of silence, or a licence renewal with a backdated effective date — as potential data quality anomalies or fraud signals for further investigation.

### 2.4 Composite Business Group Activity Scores
When several UBIDs share an owner or PAN prefix, roll up their individual activity scores into a group-level aggregate. This gives regulators a single view of a conglomerate's overall operational health.

---

## 3. Data Integration & Ingestion

### 3.1 Pluggable Department Connectors
Define a standard connector interface (schema + auth + incremental pull) so new departments can be onboarded by writing a single adapter class rather than modifying core ingestion code. Include connectors for GST portal, MCA21, Income Tax PAN directory, and municipal trade licences as first candidates.

### 3.2 Real-Time Webhook Ingestion
The current pipeline is batch-only (triggered from the admin console). Add a webhook endpoint (`POST /ingest/event`) that departments can call when a new event occurs (licence issued, inspection recorded, closure filed). The event router already exists — this wires it to live data.

### 3.3 Incremental Blocking & Scoring
When a single new record arrives, running the full O(candidates) blocking pass is wasteful. Implement an incremental blocking path: only generate new candidate pairs involving the arriving record, score them, and merge or queue for review — leaving all existing UBID assignments untouched.

### 3.4 Data Quality Scorecards
For each source system, compute completeness, consistency, and uniqueness metrics automatically after each ingestion run. Surface a per-department quality dashboard so that data stewards can track and improve upstream data entry over time.

---

## 4. Review Workflow Improvements

### 4.1 Collaborative Review & Supervisor Escalation
Add a two-tier review model: junior reviewers handle medium-confidence pairs, but cases with confidence near the boundary or flagged as complex are escalated to senior reviewers. Include inter-annotator agreement tracking (Cohen's kappa) to surface systematic disagreements.

### 4.2 Batch Decision Support
Allow reviewers to select a group of similar pairs (e.g., all pairs sharing the same PAN block) and apply one decision to all, with individual overrides. This dramatically speeds up resolution when many pairs share a common root cause.

### 4.3 Contextual Evidence Panel
In the review task detail view, add a timeline of all raw events linked to both candidate UBIDs. Reviewers can see whether the two records have coinciding inspection visits or filings, providing direct evidence beyond string features alone.

### 4.4 Review Performance Metrics Per Reviewer
Track decision throughput, reversal rate (decisions later overturned by a supervisor), and time-per-task per reviewer. Surface these in the admin console to help with workload balancing and quality monitoring.

### 4.5 Reviewer Disagreement Loop
When a supervisor overturns a junior decision, automatically add the reversed pair back to the model's retraining set with the corrected label, and flag similar pairs already decided by the same reviewer for spot-checking.

---

## 5. Analytics & Reporting

### 5.1 Scheduled Report Generation
Allow admins to configure a weekly or monthly report (PDF / Excel) auto-generated and emailed to stakeholders. Report contents: new UBIDs created, activity status transitions, review queue throughput, model calibration metrics, and department coverage summary.

### 5.2 Geographic Cluster Visualisation
Upgrade the current Leaflet map to show UBID clusters as heat maps or choropleth layers at taluk/district level, with drill-down from state → district → PIN code. Overlay activity status to identify geographic concentrations of dormant businesses.

### 5.3 Cross-Department Coverage Matrix
Show, per business sector (NIC 2-digit), how many UBIDs appear in 1, 2, 3, or all 4 departments. This reveals which industry segments are under-registered in specific databases and guides compliance efforts.

### 5.4 Trend Comparison Dashboard
Allow analysts to compare two time periods (e.g., Q1 vs. Q2) across key metrics: ACTIVE count, DORMANT count, new UBIDs, review throughput, model precision/recall. Useful for quarterly regulatory reporting.

### 5.5 Custom KPI Builder
Give power users a drag-and-drop interface to define their own KPIs from the available metrics (event counts, activity scores, department coverage) and pin them to the analytics dashboard.

---

## 6. Natural Language Interface

### 6.1 Full NL Query Engine
Expand the existing `nlquery` router from a teaser to a full structured-query translator: accept a freeform English question, parse it through an LLM into a validated SQL/filter object, execute it, and return results with an auto-generated plain-English summary. Support follow-up questions with conversation context.

### 6.2 Voice Input Support
Add browser-based speech-to-text (Web Speech API) so field officers can dictate queries without typing. Particularly useful for mobile access in low-bandwidth settings.

### 6.3 Multilingual Query Support (Kannada / Hindi)
Leverage the existing `indic-transliteration` dependency and the multilingual sentence-transformer to accept queries in Kannada or Hindi, translate to internal canonical form, and return results with labels in the user's preferred language.

### 6.4 Explainability Narration
For each review task, use the LLM router to generate a 2–3 sentence natural language explanation of *why* the model scored this pair as a likely match, citing the top SHAP features in plain language rather than raw SHAP values.

---

## 7. Scalability & Infrastructure

### 7.1 Horizontal Worker Scaling
The Celery worker is currently a single container. Add auto-scaling rules (e.g., via Kubernetes HPA or Docker Swarm) so that large ingestion jobs spin up additional workers automatically and scale back down when idle.

### 7.2 Read Replica for Analytics Queries
Heavy analytics queries (score distributions, activity breakdowns) currently run against the primary PostgreSQL instance. Add a read replica and route all read-only analytics and reporting queries there, keeping write latency unaffected.

### 7.3 Materialized Views for Common Aggregations
Pre-compute frequently needed aggregations (department coverage per UBID, sector activity counts, review queue depth) as PostgreSQL materialized views refreshed on a schedule, eliminating repeated full-table scans.

### 7.4 Object Storage for LLM Summaries
Currently LLM-generated review summaries are stored as text in the database. Move them to an object store (S3-compatible, e.g., MinIO) with database rows storing only the key, reducing DB bloat for large deployments.

### 7.5 Distributed Tracing & Observability
Integrate OpenTelemetry across the FastAPI backend, Celery workers, and the LLM router. Export traces to Jaeger or Grafana Tempo so that end-to-end latency for any pipeline stage can be profiled and bottlenecks identified.

---

## 8. User Experience & Frontend

### 8.1 Mobile-Responsive Design
The current UI is desktop-first. Reflow key views (UBID lookup, review queue, activity timeline) into a responsive layout that works on tablets, enabling field inspectors to look up business status on site.

### 8.2 Saved Searches & Alerts
Let users save a filter combination (e.g., "active factories in PIN 560001 with no inspection in 12 months") and subscribe to email or in-app notifications when new businesses match that filter.

### 8.3 UBID Relationship Graph Visualisation
Add an interactive force-directed graph (D3.js or Sigma.js) showing how source records from different departments link into a single UBID, with edge weights proportional to match confidence. Helps reviewers understand complex multi-record clusters at a glance.

### 8.4 Keyboard Navigation & Accessibility
Ensure the review queue and lookup views are fully navigable by keyboard and comply with WCAG 2.1 AA standards. Add ARIA labels to charts and SHAP visualisations for screen-reader support.

### 8.5 Offline Mode for Field Use
Use a service worker to cache the last-fetched UBID list and activity data. Field officers in areas with intermittent connectivity can still look up businesses and queue review decisions that sync when connectivity is restored.

### 8.6 Onboarding Tour & Contextual Help
Add a first-run guided walkthrough (using Shepherd.js or a similar library) for each major view, plus inline help tooltips on technical terms (SHAP values, calibrated confidence, blocking keys) to reduce the learning curve for new reviewers.

---

## 9. Compliance & Governance

### 9.1 Role-Based Access Control (RBAC)
Extend the current login system to support multiple roles: Viewer (read-only), Reviewer, Supervisor, Admin, and Department Data Steward. Gate API endpoints by role using FastAPI dependency injection and surface role management in the admin console.

### 9.2 Data Retention & Purge Policies
Add configurable retention policies per data class (raw source records, SHAP scores, LLM summaries, audit events). Run a nightly Celery task to purge or archive records older than the configured window, with a deletion audit entry for every purged row.

### 9.3 Consent & Data Sharing Agreements
For PII fields (owner name, phone, PAN), record which department consented to share the field and with whom. Gate PII display based on the viewer's department affiliation, ensuring inter-department data sharing complies with defined agreements.

### 9.4 Export Controls & Watermarking
When a user exports data (CSV/JSON), embed a hidden watermark (user ID + timestamp) in the file and log the export in the audit trail. This enables traceability if exported data is later found in unauthorised locations.

### 9.5 SOC 2 / ISO 27001 Readiness
Document the control objectives already met by the platform (immutable audit log, encrypted transport, access control) and identify gaps toward SOC 2 Type II or ISO 27001 certification. This is particularly relevant for a platform handling government business data.

---

## 10. API & Ecosystem

### 10.1 Public REST API with Versioning
Expose a documented, versioned public API (`/v1/`) for approved third-party consumers (banks for KYC, insurance companies, industry associations) to query UBID status and activity scores. Include rate limiting and API key management.

### 10.2 Webhook Outbound Notifications
Allow subscribers to register webhook URLs for events: UBID created, activity status changed, review decided. The event router already fires internal events — this adds an outbound fan-out layer.

### 10.3 OpenAPI SDK Generation
Auto-generate typed client SDKs (Python, TypeScript, Java) from the FastAPI OpenAPI spec using `openapi-generator`. Publish them to internal registries so consuming teams do not maintain their own HTTP boilerplate.

### 10.4 GraphQL Layer
Expose a GraphQL endpoint alongside the REST API. This is especially useful for the analytics and detail views where the frontend currently over-fetches by calling multiple REST endpoints and merging the results client-side.

### 10.5 Integration with National Registries
Plan integration with MCA21 (company master data), GSTN (GST registration), and EPFO (employee provident fund) to enrich UBIDs with additional signals — employee count, turnover band, compliance filing history — without requiring departmental data sharing agreements.

---

*Last updated: May 2026 — reflects prototype state as of initial submission.*
