# UBID Platform — AI Bharat Hackathon 2025
## Karnataka Commerce & Industry | Theme 1
### Concise Slide Content — Presentation Ready

---

## SLIDE 1 — Title

**Title:** UBID Platform: Unified Business Identifier & Active Business Intelligence for Karnataka

**Subtitle:** Linking 40+ Regulatory Silos into One Source of Truth

**Three stat callouts (bottom row):**
- `40+` State Regulatory Departments
- `0` Existing Cross-System Join Keys
- `KA-UBID` Our Solution

**Supporting labels:** AI Bharat Hackathon 2025 | Theme 1 | Round 1 Solution Submission

**Visual note:** Abstract network of nodes converging into a Karnataka map silhouette. Government blue + teal accent. Footer: "Round 1 — Written Solution Submission."

**Problem framing (one line per bullet — shown beneath stat callouts):**
- Same business. Six department records. Six different names. Six different IDs. Zero join keys.
- Karnataka C&I cannot answer basic questions about its own industrial base today.
- UBID is the bridge that makes the connection — without touching a single source system.

**Evaluation dimension coverage (shown as footer tag row):**
- Problem Understanding 20% → Slides 2–3
- Technical Implementation 25% → Slides 4–9
- Government Feasibility 25% → Slides 3, 8, 10
- Demo Quality 15% → Slide 13
- Scalability & Impact 15% → Slide 12

---

## SLIDE 2 — The Problem

**Headline:** Karnataka's Business Data Silos — 40+ Departments, Zero Cross-System Linkage

**The Core Failure:**
- Karnataka's 40+ departments — Shop Establishment, Factories, Labour, KSPCB, BESCOM, BWSSB, Fire, LSGs — each built isolated IT systems with their own schemas and record identifiers
- The same business (e.g., a garment factory in Peenya) exists as a *different record* in every department's database with a different name, address format, and internal ID
- Business names stored as free text with no cross-system normalisation
- PAN/GSTIN exist as Central Government anchors but are absent in 60%+ of records in departments like BESCOM and BWSSB
- No single field reliably joins even two systems together

**Two Cascading Failures:**
- **Failure 1 — No Join Key:** Cannot build a single view of any business. No master data linkage.
- **Failure 2 — Trapped Activity Data:** Inspections, renewals, consumption data sit locked in dept silos. Cannot be aggregated per business. Part B is unsolvable without Part A.

**Name Variation Reality (same business, different records):**
- "Sharma Textiles Pvt Ltd" vs "Sharma Textiles P Ltd" vs "Sharma Textiles" vs "S. Textiles Pvt."
- "Peenya Garments" vs "Peenya Garmts" vs "Penya Garments Industries"
- "Bengaluru Steel Works" vs "Bangalore Steel Works" vs "B'lore Steel Wks"

**Source System Data Quality Asymmetry:**

| Department | PAN/GSTIN Present | Address Format | Primary Data Quality Issue |
|---|---|---|---|
| Shop Establishment | Rarely (~15%) | Free text | Nicknames, DBA names, no standardisation |
| Factories | Sometimes (~45%) | Survey no. + village | Multiple units under one owner |
| Labour | Sometimes (~40%) | Mixed EN/KN | Same employer across multiple registrations |
| KSPCB | Often (~65%) | Survey no. | Industry classification varies from Factories |
| BESCOM / ESCOMs | Rarely (~10%) | Service address | Multiple connections per business |
| BWSSB | Rarely (~10%) | Property address | Address not linked to trade name |

**Queries Impossible Today:**
- *"Active factories in pin code 560058 with no inspection in the last 18 months?"*
- *"Businesses with active electricity consumption but no valid trade licence?"*
- *"How many businesses are actually operating, in what sectors, and where?"*
- *"Cross-department compliance picture for any single business?"*

**Callout:** *"The raw data exists — it is simply trapped in departmental silos with no bridge."*

---

## SLIDE 3 — Constraints & Non-Negotiables

**Headline:** Five Hard Constraints That Separate This From a Toy Problem

| Constraint | What It Means for Our Design |
|---|---|
| No source system changes | All linking done in a read-only shadow layer. Zero writes to any dept database. No schema changes, no stored procedures, no new columns. |
| No real PII in dev/test | Deterministic scrambling at the ingest boundary. Architecture enforces PII safety — not just policy. |
| No hosted LLM on raw PII | LLMs only see synthetic/scrambled inputs. All data-touching NLP runs on local on-prem models inside the government network. |
| Wrong merge > missed link | False positive merges silently corrupt registry integrity. System defaults to "keep separate." Precision is architecturally enforced. |
| Every decision must be explainable | SHAP values on every linkage decision. Evidence timeline on every activity classification. No black-box probability scores anywhere. |

**Additional legacy data challenges:**
- Typos, abbreviations, legal suffix variations, and transliteration differences in names
- Five distinct Karnataka address formats: BBMP ward, KIADB industrial estate, rural survey number, landmark-based, minimal (locality + pin only)
- Intra-department duplicates: same business registered twice in the same dept due to re-registration, fire damage, or officer error

**Why order matters:** Part A (UBID assignment) is a strict architectural prerequisite to Part B (activity inference). Without a stable UBID, activity events cannot be joined per business. This dependency is enforced in the pipeline — the activity engine reads only from the UBID registry.

**Six name variation categories our pipeline handles (all are first-class problems, not data cleaning afterthoughts):**
- Legal suffix variation: "Sharma Textiles Pvt Ltd" vs "Sharma Textiles P Ltd" vs "Sharma Textiles Private Limited"
- Transliteration variation: "Bengaluru Steel Works" vs "Bangalore Steel Works" vs "B'lore Steel Wks"
- DBA vs. legal name: "Nilgiris" vs "Food World Supermarkets Pvt Ltd"
- Abbreviation: "Karnataka Silk Industries Corp" vs "KSIC" vs "K.S.I.C."
- Ownership succession: "Murugan Granites" re-registered as "Sri Venkateshwara Stone Works" (same address, new PAN)
- Intra-department duplicate: same factory registered twice in Factories Dept due to re-registration after fire

---

## SLIDE 4 — Solution Overview

**Headline:** A Non-Invasive, Read-Only Shadow Layer — Two Sequenced Parts

**PART A — UBID Assignment Pipeline**
1. **Ingest & Standardise** — Read-only connectors per dept. Name canonicalisation: 47 legal suffix variants stripped, 180+ abbreviations expanded, ISO 15919 Kannada transliteration. Karnataka-specific address parser (10 structured fields). PAN/GSTIN validation. PII scrambled here — before any ML stage sees the data.
2. **Multi-Key Blocking** — 6 independent keys reduce O(n2) to under 5% of pairs while targeting 99.5% pair recall. A candidate pair is generated if any single key matches.
3. **Feature Extraction** — 13-feature vector per candidate pair covering name similarity, identifier signals, geo-location, address overlap, phone, industry code, owner name, same-source flag, and registration date proximity.
4. **LightGBM Scoring + SHAP** — Calibrated confidence score via Platt Scaling. SHAP TreeExplainer values computed for every decision. Threshold routing: Auto-Link (>= 0.95) / Review Queue (0.75–0.94) / Keep Separate (< 0.75). PAN mismatch hard rule overrides model.
5. **UBID Assignment** — Union-Find transitive closure clustering over all auto-linked pairs. Format: KA-UBID-{6-char base36} e.g. KA-UBID-7X4Q2R. Anchored to PAN (one) and GSTINs (one or more) if present in the cluster. UNANCHORED flag if no PAN confirmed — eligible for future enrichment. Every UBID carries an append-only provenance record: which source records it aggregates, when links were established, by what mechanism (auto vs reviewer), confidence score, SHAP values, and model version — all stored as JSONB. No link decision is ever deleted; only superseded.

**One-way dependency enforced: Part A must complete before Part B begins.**

**PART B — Activity Intelligence Pipeline**
1. **Event Ingestion** — One-way read-only stream from 8 source systems. 6 event categories: Renewal/Registration, Inspection, Compliance Filing, Utility Consumption, Administrative, Negative Signals (closure/cancellation).
2. **UBID Join at Ingest** — Events joined to UBID at ingestion time (not query time) to keep the activity engine fast. Unmatched events routed to a structured triage queue — never silently dropped.
3. **Signal Decay Scoring** — Each signal has a base weight and exponential decay half-life. Score contribution = weight x e^(-lambda x days_since_event).
4. **Activity Classifier** — Activity Score normalised to [-1, +1]. Thresholds: Active (AS > +0.4) / Dormant (-0.2 to +0.4) / Closed Suspected (AS < -0.2) / Closed Confirmed (hard closure event present — overrides score).
5. **Explainable Verdict** — Structured evidence record per UBID: status, score, contributing signals with individual decay contributions, lookback window dates, next review date. Reviewer-overridable with reason code + audit log entry.

**Design principles:** Explainability-first · Reversibility by design · PII-safe by architecture · Government-native on NIC/KSDC infrastructure

**Key design choices visible in architecture:**
- Every automated decision is logged before it is committed — if a commit fails, the log already exists
- Auto-links are reversible: a System Admin or Dept Admin can override any auto-link; the override is recorded in the audit log but does not delete the original decision
- Unmatched events are never dropped: they accumulate in a triage queue and are retroactively joined when a UBID is later assigned to the source record
- The UBID registry is the single authoritative source of truth — all downstream systems read from it; none write to it except the ER engine

---

## SLIDE 5 — Entity Resolution: Blocking + Features + Scoring

**Headline:** From Two Raw Records to a UBID Decision — ML Pipeline With Explainability at Every Step

**Blocking — 6 Independent Keys:**

| Key | Construction | What It Catches |
|---|---|---|
| PAN Exact | Normalised 10-char PAN | ~40% of cross-dept duplicates — the cleanest signal |
| GSTIN Prefix | Full 15-char GSTIN | ~30% of records (overlaps with PAN) |
| Pin + Soundex | 6-digit pin + Soundex of first meaningful name word | Same-locality businesses with name spelling variants |
| Pin + Double-Metaphone | Pin + Metaphone phonetic key | Phonetic variants Soundex misses (Shree vs Sri) |
| H3 Geo-cell + Name Token | ~1.2km2 hex cell + most distinctive name token | Address-first records where name is truncated |
| NIC Code + Pin + Name | 2-digit NIC + pin + first token | Prevents cross-sector false comparisons |

Blocking reduces ~800 crore naïve comparisons to 2–4 crore candidate pairs while maintaining >= 99.5% pair recall.

**13-Feature Vector per Candidate Pair:**

| Group | Features | What It Answers |
|---|---|---|
| Name Similarity | F01 Jaro-Winkler, F02 Token Set Ratio, F03 Abbreviation Match | Same business by name? |
| Identifiers | F04 PAN Match, F05 GSTIN Match (-1 for confirmed mismatch, not just absent) | Official IDs confirm or contradict? |
| Address & Location | F06 Pin Code Match, F07 Haversine Geo Distance, F08 Address Token Jaccard | Same physical location? |
| Supplementary | F09 Phone, F10 Industry Code Compat, F11 Owner Name, F12 Same-Source Flag, F13 Reg Date | Additional corroborating signals? |

**Scoring Architecture:**
- LightGBM gradient-boosted classifier on 13-feature vector
- Platt Scaling calibration: score of 0.85 means 85% of such pairs are true matches in validation data (not just a relative rank)
- SHAP TreeExplainer: exact per-feature contributions for every single decision (example: "PAN match: +0.41 | Name similarity: +0.32 | Address distance: -0.08")
- PAN hard rule: both records have PAN and they mismatch = Force Separate regardless of model score + compliance alert generated
- Auto-link threshold 0.95 (~60-75% of pairs) | Review 0.75-0.94 (~20-25%) | Keep Separate below 0.75 (~5-15%)
- Thresholds are tunable by Karnataka C&I operations team; recalibrated monthly based on reviewer override patterns

**Why LightGBM over BERT:** CPU-native (no GPU needed on NIC VMs), handles null features natively (F07/F11/F13 frequently absent), retrains in 4 minutes, produces exact SHAP values. BERT rejected: opaque, GPU-dependent, slow to retrain, incompatible with explainability requirement.

**Entity Resolution Edge Cases (handled explicitly, not ignored):**
- **Multi-site business group** — 3 factories under one PAN = 3 separate UBIDs + 1 parent UBID linked to PAN. Relationship type: PARENT_SUBSIDIARY, not DUPLICATE. Factories distinct for inspection; queryable as group.
- **Business name change after ownership transfer** — "Murugan Granites" → "Sri Venkateshwara Stone Works" (new PAN, same address). Two separate UBIDs (different PANs). Address overlap flagged. Reviewer can establish SUCCESSOR_TO link without merging.
- **Intra-department duplicate** — F12 (Same-Source Flag) = 1 raises suspicion threshold. Pair routed to review; departmental officer confirms. Higher confidence required for intra-dept auto-link than cross-dept.
- **Missing PAN across all systems** — Internally generated UBID assigned with UNANCHORED flag. Flagged for enrichment. Anchorable later via direct business contact or supplementary source.

---

## SLIDE 6 — Activity Intelligence: Signal Scoring + Classification

**Headline:** From Event Stream to Active / Dormant / Closed — Time-Decayed, Evidence-Backed Verdicts

**Signal Taxonomy (weight and half-life per event type):**

| Signal | Weight | Half-Life | Rationale |
|---|---|---|---|
| Electricity >= 50% of baseline | +0.90 | 45 days | Strongest operational evidence; must recur to remain valid |
| Licence / consent renewal | +0.80 | 365 days | Annual event; half-life matches the renewal cycle |
| Inspection visit (any outcome) | +0.70 | 180 days | Inspector physically visited — business exists at location |
| Compliance filing submitted | +0.75 | 270 days | Active intentional engagement with regulators |
| Water consumption >= 30% baseline | +0.70 | 45 days | Strong operational evidence for water-using industries |
| Administrative update filed | +0.40 | 90 days | Business actively monitoring its own registrations |
| Electricity < 10% of baseline | -0.50 | 30 days | Near-zero consumption strongly suggests suspension |
| Renewal overdue > 180 days | -0.40 | 180 days | Weak negative — many businesses lag, but it is a signal |
| Closure declaration (any system) | -1.00 | Permanent | Hard override: Closed Confirmed regardless of any other score |
| Licence cancellation by dept | -0.90 | Permanent | Administrative closure; may not mean operational closure |

**Score Formula:** AS = sum of [w_i x e^(-lambda_i x days_since_event_i)] where lambda_i = ln(2) / half_life_i
Normalised to [-1, +1] via sigmoid. Lookback window: 12 months (configurable).

**Classification Thresholds:**
- AS > +0.4 = **ACTIVE**
- -0.2 to +0.4 = **DORMANT**
- AS < -0.2 = **CLOSED (Suspected)**
- Hard closure event present = **CLOSED (Confirmed)** — overrides score entirely

**Sample Evidence Record (shown to every reviewer and analyst):**
- Status: ACTIVE | Score: +0.73 | Computed: 2025-06-15 | Lookback: 12 months
- BESCOM Apr 2025 (4,230 kWh) = +0.90 x decay(0.91) = +0.82 contribution
- Factories licence renewed Jan 2025 = +0.80 x decay(0.96) = +0.77 contribution
- Labour inspection completed Mar 2025 = +0.70 x decay(0.93) = +0.65 contribution
- Shop Establishment renewal overdue 95 days = -0.40 x decay(0.73) = -0.29 contribution
- Next review: 2025-09-15 (auto-scheduled, 90-day cycle)

**Edge Cases Handled Explicitly:**
- **Seasonal businesses** — NIC-specific seasonality profiles (garments active Jun–Nov for export season; fireworks Oct–Mar); baseline computed on active-season months only
- **Residential utility connections** — downweighted for home-based businesses; upweight licence renewal signals instead
- **Closure then re-registration** — original UBID = Closed Confirmed; new registration = new UBID; SUCCESSOR_TO link proposed for reviewer confirmation; never auto-merged

---

## SLIDE 7 — Human-in-the-Loop Review System

**Headline:** Ambiguous Matches Surface to Reviewers — Every Decision Feeds Back Into the Model

**Review Card Contents (shown for every task):**
- Both records' raw field values exactly as stored in the source dept system
- Both records' canonical/normalised values as processed by the pipeline (side-by-side)
- Feature scores F01–F13 with visual indicators: green (strong positive) / amber (neutral) / red (negative)
- SHAP waterfall chart — which features drove the score up or down and by exactly how much
- Historical review decisions for any overlapping record pairs (context from past decisions)
- Suggested decision with calibrated confidence level ("System suggests: MATCH, confidence 0.88")

**Reviewer Decision Taxonomy:**

| Decision | System Action |
|---|---|
| CONFIRM MATCH | UBID committed to registry; full feature vector added to training pool with label = MATCH |
| CONFIRM NON-MATCH | Pair permanently blacklisted; never re-proposed; feature vector added to training pool with label = NON-MATCH |
| CONFIRM PARTIAL | SUBSIDIARY link created; separate UBIDs retained with parent-child relationship stored |
| REQUEST MORE INFO | Physical inspection request generated and assigned to relevant dept; pair held pending resolution |
| DEFER | Returned to queue with priority boost; re-assigned to Senior Reviewer on next cycle |

**Active Learning Feedback Loop:**
- Every MATCH/NON-MATCH decision appended to labelled dataset with full F01–F13 feature vector at decision time
- Retrain trigger: 500 new labelled decisions OR 30 calendar days — whichever comes first
- New model version promoted only if it outperforms current production model on ALL of: F1 score, precision, and recall on a static held-out evaluation set
- Platt Scaling recalibrated after every model promotion
- Override rate > 3% on auto-links in any 30-day window = urgent retraining triggered + drift report to System Admin

**Reviewer Role Hierarchy:**

| Role | Capabilities |
|---|---|
| Junior Reviewer | Confirm/defer/request info on assigned pairs only |
| Senior Reviewer | All junior actions + override auto-links + assign tasks to juniors |
| Department Admin | Senior actions + activity status overrides + merge/split UBIDs + full audit log |
| System Admin | All above + threshold tuning + model promotion + bulk operations |

**Workload Estimate:** 50,000 records across 4 departments = ~2,400–3,600 review queue items. Trained reviewer at 80–100 decisions/hour = 24–45 reviewer-hours for initial corpus. Ongoing maintenance is significantly lower.

---

## SLIDE 8 — PII Safety & Data Scrambling

**Headline:** PII Safety Is Enforced by Architecture — The Scrambler Is the Structural Boundary Before All ML

**Why deterministic (not random)?** HMAC-SHA256 ensures same real record = same scrambled record every time across all runs and all source systems. Entity resolution results are reproducible, and cross-system match/mismatch patterns are preserved — the ML model trains on structurally realistic data.

**Scrambling Method per Field:**

| Field | Method | Property Preserved |
|---|---|---|
| Business Name | HMAC-SHA256 mapped to synthetic Karnataka name dictionary | Consistency across systems; collision patterns |
| PAN | Structure-preserving encryption (5-alpha + 4-numeric + 1-alpha format enforced) | Format validity; cross-system match/mismatch pattern |
| GSTIN | State code 29 preserved; remaining 12 chars encrypted structure-preservingly | State validity; match patterns across systems |
| Address | Synthetic street names from Karnataka-specific dict + fixed per-district pin offset | Address similarity structure; pin adjacency preserved |
| Phone | Digit-by-digit substitution cipher with fixed deployment key | Format; match/mismatch pattern |
| Owner Name | HMAC mapped to census-derived Karnataka name dictionary | Name plausibility; gender/community distribution |
| Dates | Fixed per-dataset day offset (+385 days consistently applied) | Temporal ordering; gaps; seasonal patterns |

**LLM Policy — Three Zones:**
- **Raw PII zone:** No LLM at all. Deterministic rule-based processing only. No exceptions.
- **Scrambled data zone:** Local on-prem only — Llama 3.1 8B or Mistral 7B deployed within Karnataka government network. Used for: NER on free-text address fields, reviewer card natural-language summaries.
- **Aggregate analytics zone:** Hosted LLMs permitted — no individual business records involved.

**Synthetic Data Specification for Round 2:**
- 5,000 ground-truth entities with realistic Karnataka names, addresses, NIC code distribution
- 2–5 department records per entity with injected field-level variations
- Error model: 8% intra-dept duplicates, 12% partial PAN/GSTIN, 15% abbreviation variation, 8% typos
- 24 months of activity events per entity with realistic seasonality (garment export season, festive inspection spikes)
- 5% entities with clear closure signals; 10% entities flagged as Dormant with sparse recent activity

**Implementation note:** The scrambler is a stateless Python service — receives a raw record, returns a scrambled record using HMAC-SHA256 with a per-deployment secret key stored in the .env file (never committed to source control). It runs as the very first processing step after source connectors. All downstream stages — normalisation, blocking, ML, SHAP, reviewer UI — receive only scrambled or synthetic data. This is the architectural guarantee, not a policy promise.

**Demo reset capability:** The demo environment uses a fixed known secret key so that the same synthetic records always produce the same scrambled output. Any evaluator can reset the environment to initial state using a single script and get identical, reproducible results. This demonstrates that the system is structurally correct, not just coincidentally working.

---

## SLIDE 9 — Complete System Architecture

**Headline:** Five-Layer Architecture — Single Responsibility Per Layer, Zero Source System Changes

| Layer | Components | Technology Stack | Key Design Decision |
|---|---|---|---|
| 1. Source Connectors | Read-only adapters; CDC listeners; batch export processors | Python, Apache Kafka, custom SOAP/REST adapters | One adapter per dept; idempotent retry; schema version detection; fallback to last-known-good snapshot |
| 2. Normalisation Engine | Name canonicaliser; address parser; PAN/GSTIN validator; PII scrambler; geocoder (OSM Nominatim) | Python, spaCy, RapidFuzz, pyindian, self-hosted Nominatim | Stateless; fully reproducible; scrambling runs first, before any downstream processing |
| 3. ER Engine | Blocker; feature extractor; LightGBM scorer; SHAP explainer; threshold router; Union-Find clusterer; UBID assigner | Python, LightGBM, SHAP, networkx, MLflow, PostgreSQL | All decisions logged before commitment; all decisions reversible; model versioned in MLflow |
| 4. Activity Engine | Event router; UBID joiner; signal scorer; activity classifier; evidence builder; unmatched-event handler | Python, PostgreSQL (partitioned timeseries), Apache Kafka | Event-sourced; append-only log; UBID join at ingest time; unmatched events never dropped |
| 5. Application Layer | Reviewer UI; UBID lookup API; analytics dashboard; admin console; audit log viewer | FastAPI, React + Ant Design, PostgreSQL, Redis cache | API-first design; role-based access via LDAP/AD; sub-200ms p99 lookup via Redis; full RTI audit trail |

**Three Integration Patterns (none require source system modification):**
- **Read-only DB replica** — standard SQL on read replica; no writes, no schema changes, no stored procedures required
- **Existing API consumer** — register against e-Governance APIs already published; no new endpoints, no new dept IT work
- **Scheduled batch export** — daily CSV to SFTP; format defined by source dept; our connector adapts to their format

**UBID Registry Schema (7 PostgreSQL tables):**
ubid_entities · ubid_source_links · ubid_link_evidence (JSONB feature vectors + SHAP values) · review_tasks · ubid_activity_events (append-only) · activity_scores (JSONB evidence snapshots) · unmatched_events

**Full Data Flow:**
Dept Systems → [Connectors] → Kafka → [Normalise + Scramble] → [Blocker] → [Feature Extractor] → [LightGBM + SHAP] → {Auto-link → UBID Registry | Review Queue → Reviewer UI → UBID Registry | Keep Separate → Unlinked Pool} → [Activity Engine: Event Router + UBID Join] → [Signal Scorer + Classifier] → Activity Scores → [FastAPI] → Dashboard + Lookup API + Reviewer UI + Admin Console

**Technology Justifications (key decisions):**
- **PostgreSQL over NoSQL** — ACID compliance; JSONB for flexible evidence payloads; excellent audit/temporal table support; NIC-trusted and already in use across Karnataka govt systems
- **Kafka over REST polling** — Persistent 30-day replay window; exactly-once delivery; decouples 40 source connectors from normalisation engine; on-prem deployment on NIC infra
- **Self-hosted Nominatim (OSM)** — No external geocoding API calls; no PII leaves the network; Karnataka-specific OSM data quality adequate for locality-level matching
- **FastAPI over Django/Flask** — Async request handling; auto-generated OpenAPI spec for future portal integration; minimal runtime footprint on NIC VMs
- **Redis cache** — 15-minute TTL on frequent UBID lookups; sub-millisecond cache hits keep dashboard queries fast under concurrent officer load

---

## SLIDE 10 — Government Feasibility & Deployment

**Headline:** Deployed on Infrastructure Karnataka Already Owns — No Cloud, No New Procurement

**Infrastructure Requirements (within NIC/KSDC standard provisioning):**

| Component | What Is Needed | Available Today? |
|---|---|---|
| Compute | 4–5 VMs (16–32 vCPU, 64–128 GB RAM each) | Within existing NIC provisioning capacity |
| Network | All inter-service traffic via KSWAN | KSWAN already connects all state departments |
| Storage | ~2.5 TB SSD total (PostgreSQL + Kafka logs) | Available at KSDC shared storage |
| Identity & Access | OAuth 2.0 via Karnataka Govt IdP; LDAP/AD for role assignment | Karnataka SSO/IdP already operational |
| Licence Cost | Zero — 100% open-source stack | Python, PostgreSQL, Kafka, React, LightGBM, MLflow, Redis |

**Compliance Checklist:**
- MEITY Data Localisation: all data on KSDC/NIC; zero external cloud egress ever
- DPDP Act 2023: PII scrambled at ingest boundary; no personal data in any dev/test environment
- GFR 2017: 100% open-source; no proprietary licence fees; no vendor lock-in
- NIC Security Standards: OAuth 2.0 + Karnataka IdP; mTLS between all internal services; no hardcoded secrets
- RTI Compatibility: full append-only audit log of every automated and manual decision; disclosable

**Phased Rollout Plan:**
- **Phase 1 — Pilot (Weeks 1–8):** Deploy on 2–3 NIC VMs. Connect Shop Establishment + Factories via read-only DB replica on KSWAN. 2–3 reviewer officers. Zero disruption to any department.
- **Phase 2 — Core Expansion (Months 3–6):** Add KSPCB, Labour, BESCOM, BWSSB. Each = one new connector, zero changes to the core platform. ~60–70% of registered Karnataka businesses covered by UBID.
- **Phase 3 — Full State (Months 7–18):** All 40+ regulatory departments. UBID becomes the standard cross-system join key embedded in Single Window Clearance, inspection planning, and policy dashboards.

**Change Management:** 2-day reviewer training programme (materials in English and Kannada) · One designated technical liaison per source department (existing IT staff, no new hires) · SOPs in both languages · Quarterly calibration workshops for threshold and matching rule updates

**Why this is genuinely feasible (not aspirational):**
- Departments do not need to change their existing systems, schemas, or workflows at any point
- Onboarding a new department = providing one read-only DB credential or scheduling one SFTP export. That is the full extent of dept IT involvement.
- The UBID platform is a consumer of what departments already produce — it adds value to them, not burden
- Once UBID is stable, it exposes a standard REST lookup API that any existing Karnataka government portal (Single Window Clearance, Sakala, KSWAN business portals) can call with zero redevelopment on their side

---

## SLIDE 11 — Risk Analysis & Trade-offs

**Headline:** Risks Identified Upfront — Mitigations Built Into Architecture, Not Added After

**Technical Risk Register:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Blocking recall falls below 99.5% — true pairs missed at blocking stage | Medium | High | 6 independent keys; a pair must fail all 6 to be missed; monthly recall audits on labelled subsets; manual sampling of Keep Separate pool |
| Model drift — override rate rises as data distribution shifts | High (expected) | Medium | Monthly active learning retrain; override rate >3% triggers urgent retrain + System Admin drift alert |
| Source schema change breaks connector without notice | Medium | Medium | Schema version fingerprinting on every connector startup; fallback to last-known-good snapshot; alert on first mismatch |
| PAN collision — two different businesses share one PAN | Low | High | Hard Forced Separate flag; compliance alert generated; escalated to Dept Admin minimum; never auto-resolved |
| Reviewer inconsistency across staff | High | Medium | Inter-rater reliability score tracked per reviewer pair; high-disagreement pairs auto-escalated to Senior Reviewer |
| Seasonal business misclassified as Dormant in off-season | Medium | Medium | NIC-specific seasonality profiles; industry-specific decay rate and baseline adjustments |

**Organisational Risks & Mitigations:**
- **Dept reluctance to share data** — Read-only integration model: no dept data leaves the dept's own DB; UBID platform only reads, never writes back; departments retain full control of their own systems
- **Review queue backlog** — Auto-link target >= 70% keeps queue manageable; batch review mode for bulk similar cases (e.g., all records from a newly onboarded dept processed together); surge staffing plan documented in SOP
- **Reviewer staff turnover** — All decisions stored in structured machine-readable format in DB, not in reviewers' memory; full audit trail; SOP documentation in Kannada and English; <2 day onboarding time for new reviewer
- **Budget constraints** — Entire stack runs on 4-5 modest servers; 100% open-source with zero proprietary licence fees; phased deployment plan — start with 2 departments at minimal cost and expand as budget allows

**Key Trade-off Decisions:**

| Trade-off | Our Choice | Rejected | Reasoning |
|---|---|---|---|
| Precision vs. Recall | High precision (0.95 threshold) | High recall (0.85 threshold) | Wrong merge corrupts registry permanently; missed link is recoverable. Precision is architecturally non-negotiable. |
| ML Model | LightGBM | BERT-based deep learning | Explainability hard requirement; CPU-native (no GPU); 4-min retraining; exact SHAP values. BERT is opaque, GPU-dependent, slow. |
| Activity Inference | Rule-based weighted decay | ML classifier on event sequences | No labelled activity ground truth exists yet. Rule-based is immediately deployable, transparent, and tunable by domain experts. |
| LLM Usage | Local on-prem only | Hosted LLM API on raw data | Hosted LLM on raw PII violates non-negotiable. Rejected unconditionally — no performance justification overrides this. |

**Design Philosophy:** Precision over recall. Explainability over accuracy ceiling. Reversibility over automation. Every default was chosen with the most costly failure mode — the silent wrong merge — as the primary constraint.

---

## SLIDE 12 — Scalability & Long-Term Impact

**Headline:** Built to Scale from Pilot to All of Karnataka Without Redesigning Anything

**Scale Path — Pilot to Full State:**

| Dimension | Pilot Capacity | Full Karnataka | How It Scales |
|---|---|---|---|
| Business Records | ~50,000 | ~5M+ | PostgreSQL horizontal sharding by district; read replicas for query load |
| Source Departments | 4 | 40+ | Each new dept = one new connector; zero changes to ER engine, activity engine, or UI |
| Event Volume | ~100K/month | ~50M/month | Kafka partitioning per dept topic; multiple parallel activity engine worker instances |
| Candidate Pairs | ~50K | ~2–4 crore | Blocking computation parallelised via Apache Spark or Dask on NIC cluster |
| Reviewer Workload | 1–3 reviewers | 20–50 across districts | Hierarchical queue; district-specific and dept-specific review pool assignments |

**Bottleneck-to-Technology Mapping (what makes the numbers work):**

| Bottleneck | Solution | Performance at Full Scale |
|---|---|---|
| O(n2) comparison at 4M records (~800 crore pairs naive) | 6-key multi-key blocking | Reduces to 2–4 crore pairs; >=99.5% pair recall maintained |
| Scoring 3 crore candidate pairs with ML | LightGBM CPU-native inference (~16 lakh pairs/sec/core) | Full batch scored in under 2 minutes on 32 vCPUs |
| Transitive cluster formation at 4M records | Union-Find DSU with path compression — O(alpha(n)) constant time | ~15 seconds wall-clock for 4M records |
| 50M monthly events joining to UBID | Kafka per-dept partitioned topics + ingest-time UBID join + partition-by-month timeseries | ~19 events/sec average; well within single-broker Kafka capacity |
| Sub-200ms UBID lookup under concurrent load | Redis in-memory cache (15-min TTL) + indexed PostgreSQL read replicas | Sub-50ms for cache hits; under 200ms p99 at 100 concurrent lookups |

**Long-Term Impact Enabled by UBID:**
- **Single Window Clearance** — UBID enables pre-filled licence applications; business identified on arrival, profile pulled automatically from all departments
- **Risk-Based Inspection Targeting** — data-driven selection of inspection targets combining UBID + activity score + compliance history; maximise regulatory impact per officer-hour
- **Industrial Policy Intelligence** — near-real-time sector composition, geographic distribution, and active business count trends for Karnataka C&I policy decisions
- **National System Convergence** — UBID anchored to PAN/GSTIN enables cross-reference with MCA21, EPFO, and GST national databases for comprehensive business intelligence
- **Replicable State Template** — architecture is state-agnostic; any state with similar regulatory fragmentation adopts by replacing only the source connectors

**Round 2 Success Metrics:**

| Metric | Target | Measurement |
|---|---|---|
| Entity Resolution F1 Score | >= 0.92 | Against 500-pair labelled held-out evaluation set |
| Blocking Pair Recall | >= 99.5% | Fraction of labelled true pairs present in candidate pair set |
| Auto-link Rate | 60–75% | Fraction of candidate pairs resolved without human review |
| Activity Classification Accuracy | >= 88% | Against manually labelled ground truth in synthetic dataset |
| UBID Lookup Response Time (p99) | < 200ms | Load test: 100 concurrent lookups |
| Unmatched Event Rate | < 5% | Fraction of events not joinable to any UBID or source record |
| Reviewer Task Throughput | >= 80 decisions/hour | Measured in demo with trained reviewer on representative queue |

**Scalability is consequence, not claim:** Every scale dimension has a dedicated technology. Kafka absorbs ingest volume. Blocking absorbs comparison complexity. Spark absorbs compute time. Union-Find absorbs clustering cost. Redis absorbs lookup load. Adding more data does not require redesigning anything — only adding more of the same components (more Kafka partitions, more read replicas, more Spark workers, more connectors).

---

## SLIDE 13 — Demo & Closing

**Headline:** The Query That Was Impossible Yesterday

**Demo Flow (7 Scenes — 15 minutes total):**
1. **The Problem (2 min)** — Show the same business as 4 different records across 4 department systems. Different names, different addresses, no common field. Ask: which are the same business? Answer: impossible from raw data.
2. **Normalisation Live (2 min)** — Run records through normalisation engine. Show canonical names, parsed addresses, validated PAN. Records now look comparable.
3. **Blocking + Scoring (2 min)** — Show a pair at 0.97 (auto-linked), 0.93 (review zone with SHAP waterfall), and 0.61 (rejected). Explain what drove each decision.
4. **Review Interface (3 min)** — Open reviewer queue. Process the 0.93 pair: side-by-side card, feature scores, SHAP chart. Reviewer confirms match. UBID committed. Audit log entry created with reviewer attribution.
5. **Activity Classification (2 min)** — Three UBIDs: Active (strong consumption + recent inspection), Dormant (low consumption + missed renewal), Closed (explicit closure declaration). Click through evidence records.
6. **The Query (2 min)** — Execute: "Active factories in pin codes 560058 and 560073 with no inspection in the last 18 months." Return results table. Click one result — see all linked dept records + full activity evidence.
7. **Analytics Dashboard (2 min)** — Active count by sector and district, status distribution, review queue health metrics, auto-link rate over time.

**Demo Environment Properties:**
- 5,000 synthetic businesses across 4 departments and 2 Bengaluru Urban pin codes
- 12 months of synthetic activity events with realistic seasonality and variation
- Full range of matching challenges: high-confidence matches, ambiguous pairs, intra-dept duplicates, edge cases
- Fully reproducible — any evaluator can reset to initial state and re-run with one command
- Zero real data: demo cannot accidentally expose or corrupt anything

**Closing Statement:**

*"Karnataka Commerce & Industry can now ask: which active factories have had no safety inspection in 18 months? The answer takes seconds. That query was impossible before UBID.*

*We built this without modifying a single source system, without exposing a single piece of real PII, and with every automated decision explainable to any reviewer.*

*UBID is not a new database. It is the bridge that was always missing."*

---

*UBID Platform | AI Bharat Hackathon 2025 | Karnataka Commerce & Industry | Theme 1*