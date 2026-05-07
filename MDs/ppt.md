# UBID Platform — AI Bharat Hackathon 2026
## Karnataka Commerce & Industry | Theme 1
### Slide-by-Slide PPT Structure

---

## SLIDE 1 — Title Slide

**Purpose:** Make a strong first impression. Establish identity, theme, and credibility instantly.

**Content Type:** Full-bleed visual with minimal text. Government branding with modern design.

**Key Points to Cover:**
- Title: **"UBID Platform: Unified Business Identifier & Active Business Intelligence for Karnataka"**
- Subtitle: *"Linking 40+ Regulatory Silos into One Source of Truth"*
- Hackathon: AI Bharat Hackathon 2025 | Theme 1
- Team name + institution
- Karnataka emblem / Commerce & Industry ministry logo

**Visual Suggestion:**
- Background: abstract network graph of nodes connecting, fading into Karnataka map silhouette
- Accent color: Karnataka government blue + gold
- Footer: "Round 1 — Written Solution Submission"

---

## SLIDE 2 — The Problem in Real Terms: Karnataka's Invisible Industrial Base

**Purpose:** Hook the judges immediately with the scale and urgency of the problem. Score heavily on *Problem Relevance & Depth of Understanding (20%)*.

**Content Type:** Split layout — left: illustrative stat block; right: visual diagram of fragmentation.

**Key Points to Cover:**
- Karnataka has **40+ regulatory departments**, each with independent, siloed IT systems
- The **same business** — e.g., a garment factory in Peenya — exists as a **different record** in Shop Establishment, Factories, Labour, KSPCB, BESCOM, and BWSSB
- No common identifier ties these records together. Business names and addresses are free text with no cross-system normalisation
- PAN/GSTIN exist but are only **partially captured** in State systems
- **Result:** Karnataka Commerce & Industry cannot answer basic questions:
  - *"How many active factories are in pin code 560058?"*
  - *"Which businesses have had no safety inspection in 18 months?"*
  - *"Is this business actually operating today?"*

**Visual Suggestion:**
- Diagram showing 1 real business mapped to 6 different records in 6 different departmental systems, each with a different name/address format
- Red "NO JOIN KEY" banner overlaying the gap between systems
- Quote callout: *"The raw data exists — it is simply trapped in silos with no bridge."*

---

## SLIDE 3 — Why Current Systems Fail: Two Cascading Failures

**Purpose:** Deepen the problem framing. Show you understand the *structural* reason the problem exists, not just the surface symptom.

**Content Type:** Two-column layout with visual icons, concrete examples.

**Key Points to Cover:**

**Failure 1 — No Reliable Join Key**
- Business name stored as free text in each system: *"Sharma Textiles Pvt Ltd"* vs *"Sharma Textiles P Ltd"* vs *"S. Textiles"*
- Address formats incompatible: BBMP ward notation vs. survey number vs. landmark
- PAN/GSTIN only partially present — cannot be sole anchor
- No master data normalisation layer across departments

**Failure 2 — Activity Data Trapped in Silos**
- Inspections, renewals, consumption, compliance filings — all inside department systems
- Cannot aggregate per-business across departments
- Cannot compute a cross-system "is this business alive?" signal
- Stale, fragmented, unactionable data

**Visual Suggestion:**
- Two-panel graphic: Panel A shows a fragmented "explosion" of records; Panel B shows a black void where the analytics dashboard *should* be
- Callout box: *"A wrong merge is more costly than a missed one"* — establishing that precision > recall is a core design value

---

## SLIDE 4 — The Two-Part Problem (Part A + Part B)

**Purpose:** Precisely articulate the problem structure. Demonstrate that Part A must precede Part B — a key insight judges will look for.

**Content Type:** Two clearly separated panels with numbered sequence arrows. Table format for sub-problems.

**Key Points to Cover:**

**Part A — Unique Business Identifier (UBID) Assignment**
- Given master data from 3–4 State department systems, **automatically link** records referring to the same real-world business
- Assign each unique business a single **UBID**
- Where PAN/GSTIN exists → anchor UBID to it. Where absent → internal ID, anchorable later
- Every linkage must carry an **explainable confidence signal**
- High-confidence matches: auto-committed. Ambiguous: **routed to human reviewer**. Low-confidence: **kept separate**
- Reviewer decisions must feed back into model improvement

**Part B — Active / Dormant / Closed Inference**
- Only solvable *after* Part A. Without a stable UBID, events cannot be aggregated per business.
- Given a **one-way event stream** (inspections, renewals, consumption data, compliance filings)
- Infer per-UBID status: **Active / Dormant / Closed**
- Every verdict must be explainable: which signals, over what time window
- Events that can't be joined to a UBID must be **surfaced for review, not silently dropped**

**Visual Suggestion:**
- Sequential pipeline arrow: Part A (Entity Resolution) → UBID Registry → Part B (Activity Engine)
- Emphasise that the arrow is one-way and enforced by architecture

---

## SLIDE 5 — Constraints & Non-Negotiables: What Makes This Hard

**Purpose:** Show deep understanding of real-world government constraints. This is what separates serious proposals from toy solutions. Scores on *Government Feasibility (25%)*.

**Content Type:** Constraint table with "What It Means for Our Design" column — mirrors the actual problem statement framing.

**Key Points to Cover:**

| Constraint | Real Design Impact |
|---|---|
| **No source system changes** | All linking done in a shadow layer via read-only connectors. Zero writes to any department DB. |
| **No real PII in dev/test** | PII scrambler is the architectural boundary. All ML training and demo runs on deterministically scrambled data. |
| **No hosted-LLM on raw PII** | LLMs only see synthetic/scrambled inputs. All data-touching NLP runs on local on-prem models (Llama 3.1 / Mistral 7B). |
| **Wrong merge > missed merge** | Default is "keep separate." False positives silently destroy registry integrity. Precision is architecturally enforced. |
| **Every decision must be explainable** | SHAP values on every linkage. Evidence timeline on every activity classification. No black boxes. |
| **Legacy data quality** | Typos, abbreviations, Kannada/English transliterations, missing fields — all treated as first-class engineering problems. |
| **Partial PAN/GSTIN coverage** | Cannot be sole matching key. Used as a hard anchor when present; absent in ~60% of records. |

**Visual Suggestion:**
- Red "Hard Wall" visual on the left side representing the constraints
- Each constraint shown as a constraint block with a corresponding "Our Architecture Handles This By..." response on the right

---

## SLIDE 6 — Proposed Solution Overview: The UBID Platform

**Purpose:** One-slide executive summary of the entire solution. Give judges a mental model before diving into technical detail.

**Content Type:** High-level pipeline diagram with 5 numbered stages and a brief label for each.

**Key Points to Cover:**

The UBID Platform is a **non-invasive, read-only shadow layer** that:
1. **Ingests** data from department systems via read-only connectors (no source system changes)
2. **Normalises** names, addresses, PAN/GSTIN, and scrambles PII at the boundary
3. **Resolves entities** using a blocking + ML scoring + human review pipeline → assigns UBIDs
4. **Classifies activity** using a time-decayed signal scoring engine on live event streams
5. **Serves** a lookup API, reviewer UI, analytics dashboard, and audit log

**Key design philosophies:**
- **Explainability-first:** Every automated decision carries a structured evidence record
- **Reversibility:** No decision is permanent; every auto-link can be overridden by an admin
- **PII safety by architecture:** Scrambling happens before any ML stage
- **Government-native:** Deployable on NIC/KSDC infrastructure; fully open-source stack; no external cloud

**Visual Suggestion:**
- Clean horizontal pipeline: [Dept Systems] → [Connectors] → [Normalisation + PII Scramble] → [Entity Resolution Engine] → [UBID Registry] → [Activity Engine] → [Application Layer]
- Color code each stage distinctly. Add icons: shield for PII, magnifying glass for ER, chart for activity, dashboard for application.

---

## SLIDE 7 — Entity Resolution Architecture: How We Link Records (Part A)

**Purpose:** Technical deep-dive on UBID assignment. Scores heavily on *Technical Implementation & Innovation (25%)*.

**Content Type:** 5-stage pipeline table + callout boxes for key innovations.

**Key Points to Cover:**

**5-Stage Entity Resolution Pipeline:**

| Stage | Name | What Happens |
|---|---|---|
| 1 | Ingest & Standardise | Canonical name (strip legal suffixes, expand abbreviations, ISO 15919 transliteration), address parsing, PAN/GSTIN validation |
| 2 | Blocking | Multi-key blocking: PAN exact, GSTIN prefix, Pin+Soundex, Pin+Metaphone, Geo-cell+Name token, NIC code. Target: ≥99.5% pair recall |
| 3 | Feature Extraction | 13 features per candidate pair: Jaro-Winkler name similarity, token set ratio, abbreviation match, PAN/GSTIN exact match (with hard negative), geo-distance, address token overlap, phone match, industry code compatibility, owner name similarity, registration date proximity |
| 4 | Scoring & Classification | LightGBM classifier + Platt Scaling calibration → calibrated confidence score. Threshold routing: Auto-Link (≥0.95) / Review Queue (0.75–0.94) / Keep Separate (<0.75). SHAP explainability for every decision. |
| 5 | UBID Assignment | Union-Find transitive closure over auto-links → entity clusters → UBID assigned. PAN/GSTIN anchoring. Full provenance stored. |

**Key Technical Callouts:**
- **Name Normalisation:** 47-variant legal suffix dictionary, 180+ abbreviation dictionary, Soundex + Double-Metaphone phonetic keys
- **Address Parsing:** Rule-based Karnataka-specific parser (BBMP ward, KIADB industrial estate, rural survey number, landmark-based)
- **PAN Mismatch Hard Rule:** If PAN present in both records and mismatches → forced "Keep Separate" regardless of model score
- **UBID Format:** `KA-UBID-{6-char-base36}` anchored to PAN/GSTIN if present

**Visual Suggestion:**
- Flowing pipeline diagram with stage boxes
- Zoom-in callout on Stage 4 showing SHAP waterfall chart concept
- Small table showing the threshold zones: green (Auto-Link) / amber (Review) / red (Keep Separate)

---

## SLIDE 8 — Confidence Scoring & Activity Intelligence (Part B)

**Purpose:** Show the two intelligence layers — confidence calibration for entity resolution, and time-decayed signal scoring for activity inference.

**Content Type:** Split slide. Top half: confidence scoring system. Bottom half: activity signal formula.

**Key Points to Cover:**

**Confidence Calibration (Entity Resolution):**
- Raw LightGBM probability → **Platt Scaling** → calibrated confidence (0.85 means 85% of such matches are truly correct)
- SHAP TreeExplainer produces per-feature contribution values for every decision
- Example reviewer-facing display: *"Name similarity: +0.32 | PAN match: +0.41 | Address distance: −0.08"*
- Thresholds are **tunable** by Karnataka C&I operations team; recalibrated monthly based on override rates

**Activity Score Computation:**

Formula: **AS = Σ [ w_i × e^(−λ_i × days_since_event_i) ]**

Where:
- `w_i` = base weight of signal type (e.g., electricity consumption = +0.90, closure declaration = −1.00)
- `λ_i` = decay constant = ln(2) / half-life

Classification thresholds:
- AS > +0.4 → **Active**
- −0.2 ≤ AS ≤ +0.4 → **Dormant**
- AS < −0.2 → **Closed (Suspected)**
- Hard closure event → **Closed (Confirmed)** — overrides all positive signals permanently

**Signal Examples:**

| Signal | Weight | Half-Life |
|---|---|---|
| Electricity consumption ≥ 50% baseline | +0.90 | 45 days |
| Licence / consent renewal | +0.80 | 365 days |
| Inspection visit | +0.70 | 180 days |
| Closure declared (any system) | −1.00 | Permanent |

**Visual Suggestion:**
- Left panel: SHAP waterfall chart showing feature contributions to a match score
- Right panel: Timeline bar showing activity events with decaying weight visualised over 12 months
- Three status badges shown clearly: 🟢 ACTIVE / 🟡 DORMANT / 🔴 CLOSED

---

## SLIDE 9 — Human-in-the-Loop Review System

**Purpose:** Show that the system doesn't treat ambiguity as an edge case — it's designed around it. Demonstrates sophistication in workflow design and scores on *Government Feasibility*.

**Content Type:** Review card mockup + feedback loop diagram.

**Key Points to Cover:**

**Review Card (Side-by-Side Comparison UI):**
- Both records' raw field values vs. normalised canonical values
- Feature scores F01–F13 with visual indicators (green / amber / red per feature)
- SHAP waterfall chart: which features drove the match score
- Historical reviewer decisions for overlapping pairs
- Suggested decision with confidence level
- Deep links to source system records (read-only)

**Reviewer Decision Taxonomy:**

| Decision | Outcome |
|---|---|
| CONFIRM MATCH | UBID committed; added to training pool |
| CONFIRM NON-MATCH | Pair blacklisted; added to training pool |
| CONFIRM PARTIAL (branch/unit) | SUBSIDIARY link established; separate UBIDs retained |
| REQUEST MORE INFO | Physical inspection triggered; pair held |
| DEFER | Returned to queue with priority boost for senior reviewer |

**Feedback Learning Loop:**
- Every confirmed decision → labelled dataset with full feature vector
- 500+ new decisions OR monthly (whichever sooner) → new model version trained
- New model evaluated on held-out set → if F1 improves, promoted to production
- **Override rate monitoring:** If reviewer overrides auto-links exceed **3%** → urgent retraining triggered

**Reviewer Role Hierarchy:** Junior → Senior → Department Admin → System Admin (each with escalating permissions)

**Workload Estimate:** 50,000 records across 4 departments → ~2,400–3,600 pairs in review queue → **24–45 reviewer-hours** for initial processing

**Visual Suggestion:**
- Mockup of reviewer UI card (side-by-side layout with feature score bars)
- Active learning loop diagram: Reviewer Decision → Labelled Dataset → Retrain → Better Model → Fewer Review Queue Items

---

## SLIDE 10 — PII Safety, Data Scrambling & Synthetic Data Strategy

**Purpose:** Directly address the non-negotiable PII and LLM constraints. Show that the architecture *enforces* safety, not just policy compliance.

**Content Type:** Two-column layout. Left: scrambling method table. Right: LLM deployment policy diagram.

**Key Points to Cover:**

**Deterministic Scrambling (not random anonymisation):**
- Same real record → same scrambled record every time (reproducible test runs)
- Scrambling happens in Stage 1 Normalisation — **before any ML stage sees the data**

| Field | Scrambling Method | Property Preserved |
|---|---|---|
| Business Name | HMAC-SHA256 → synthetic name dictionary | Consistency; collision pattern |
| PAN | Structure-preserving encryption | PAN format; cross-system match/mismatch pattern |
| GSTIN | State code (29) preserved; rest encrypted | State validity; match pattern |
| Address | Synthetic street names + fixed pin offset per district | Address similarity structure; pin adjacency |
| Phone | Digit-by-digit substitution cipher | Format; match pattern |
| Dates | Fixed per-dataset offset (e.g., +385 days) | Temporal ordering and gaps |

**LLM Policy — Three-Zone Model:**
- **Raw PII zone:** No LLM. Deterministic rule-based processing only.
- **Scrambled data zone:** Local on-prem LLMs (Llama 3.1 8B / Mistral 7B) deployed within Karnataka government network. Used for NER on addresses and reviewer card summaries.
- **Aggregate analytics zone:** Hosted LLMs permitted for non-PII reports (aggregate statistics, policy dashboards).

**Synthetic Data for Round 2:**
- 5,000 ground-truth business entities with realistic Karnataka-style names + addresses
- 2–5 department records per entity with injected variations (typos, abbreviations, format variation)
- Injected challenges: 8% intra-dept duplicates, 12% partial PAN/GSTIN, 5% address-only records, 3% multi-site businesses
- 24 months of synthetic activity events with realistic seasonality (garment export season, festive inspection spikes)

**Visual Suggestion:**
- Three-zone diagram (red / amber / green) showing which data zone permits which LLM usage
- "Scrambling Boundary" wall visual showing PII cannot cross into ML stages
- Shield icon emphasising "PII-safe by architecture, not just by policy"

---

## SLIDE 11 — Complete System Architecture

**Purpose:** Full technical architecture for judges to evaluate *Technical Implementation* and *Scalability*. The single most information-dense slide.

**Content Type:** Layered architecture diagram (5 layers) + technology stack table.

**Key Points to Cover:**

**5-Layer Architecture:**

| Layer | Components | Technology Stack |
|---|---|---|
| 1. Source Connectors | Read-only adapters; CDC listeners; batch export processors | Python, Apache Kafka, custom SOAP/REST adapters |
| 2. Normalisation Engine | Name canonicaliser, address parser, PAN/GSTIN validator, geocoder, PII scrambler | Python (spaCy, RapidFuzz, pyindian), OSM Nominatim (self-hosted), custom transliterator |
| 3. Entity Resolution Engine | Blocker, feature extractor, LightGBM scorer, SHAP explainer, threshold router, Union-Find clusterer, UBID assigner | Python (LightGBM, SHAP, networkx), PostgreSQL (UBID registry), MLflow |
| 4. Activity Engine | Event router, UBID joiner, signal scorer, activity classifier, evidence builder, unmatched-event handler | Python, PostgreSQL (timeseries), Apache Kafka |
| 5. Application Layer | Reviewer UI, UBID lookup API, analytics dashboard, admin console, audit log viewer | FastAPI, React + Ant Design, PostgreSQL, Redis |

**Data Flow (textual arc for diagram):**
> Dept Systems → [Read-only Connectors] → Raw Event Queue (Kafka) → [Normalisation + PII Scramble] → Normalised Records → [Blocker] → Candidate Pairs → [Feature Engine + Scorer] → {Auto-link → UBID Registry | Review Queue → Reviewer UI → UBID Registry | Keep Separate → Unlinked Pool} → Activity Engine → Activity Status Store → Application API → Dashboard / Lookup / Reviewer UI

**Technology Justifications (key ones):**
- **LightGBM** over deep learning: interpretable via SHAP; CPU-efficient; no GPU needed; handles missing features natively
- **PostgreSQL** over NoSQL: ACID compliance; JSONB for evidence payloads; NIC-trusted; excellent audit table support
- **Kafka** over REST polling: persistent replay; exactly-once delivery; on-prem deployment on NIC infra
- **OSM Nominatim (self-hosted):** No external API calls; no PII leaves network; Karnataka-adequate geocoding quality

**Visual Suggestion:**
- Full architecture diagram with 5 swim lanes (one per layer)
- Colour-coded data flows: blue for master data ingestion, orange for entity resolution, green for activity events, purple for application queries
- Callout box: "Zero writes to source systems — architecturally enforced"

---

## SLIDE 12 — Real-World Deployability & Government Feasibility

**Purpose:** Prove this can actually be deployed in Karnataka's government IT environment. Scores the full *Government Feasibility (25%)* dimension.

**Content Type:** Infrastructure table + compliance checklist + integration model diagram.

**Key Points to Cover:**

**Deployment on NIC/KSDC Infrastructure (No External Cloud):**
- 4–5 modest VMs within NIC standard provisioning capacity
- All traffic within **KSWAN** (Karnataka State Wide Area Network); no internet egress required
- PostgreSQL: 2 TB SSD for 10M records + 5 years of events
- Kafka: 500 GB for 30-day event replay window
- RPO: 1 hour | RTO: 4 hours (daily backup + WAL archiving)

**The Non-Modification Guarantee — 3 Integration Patterns:**
1. **Read-only DB replica:** Connect to read replica via standard SQL. No writes, no schema changes.
2. **Existing API consumption:** Register as consumer of APIs already exposed to e-Governance portal. No new endpoints.
3. **Scheduled batch export:** Daily CSV/fixed-width export to shared SFTP. Format defined by source; our connector adapts.

**Government IT Policy Compliance:**
- ✅ MEITY data localisation — all data on KSDC/NIC infrastructure
- ✅ DPDP Act 2023 — business data as public record; personal data handled per provisions
- ✅ GFR 2017 procurement — 100% open-source stack (Python, PostgreSQL, Kafka, React); zero licence costs
- ✅ NIC Security Standards — OAuth 2.0 with Karnataka government IdP; inter-service mTLS
- ✅ RTI compatibility — full audit log is RTI-disclosable; decision evidence supports accountability

**Change Management Plan:**
- 2-day reviewer training programme (decision criteria + UI + escalation)
- One designated technical liaison per source department
- SOPs in **English and Kannada**
- Quarterly calibration workshops for threshold and matching rule updates

**Visual Suggestion:**
- Karnataka state map with KSWAN overlay showing department connectivity
- Compliance checklist graphic with green tick marks
- "Shadow Layer" diagram showing UBID platform sitting alongside (not modifying) source systems

---

## SLIDE 13 — Risk Analysis & Key Trade-offs

**Purpose:** Show intellectual honesty and engineering maturity. Judges penalise solutions that don't acknowledge failure modes.

**Content Type:** Risk table + trade-off comparison table.

**Key Points to Cover:**

**Top Technical Risks:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Blocking misses true pairs (recall < 99.5%) | Medium | High | ≥6 independent blocking keys; regular recall audits on labelled subsets; manual sampling of "Keep Separate" pool |
| Model drift (reviewer overrides show systematic pattern) | High (expected) | Medium | Monthly retraining; override rate monitoring; **3% override rate threshold** triggers urgent retraining |
| Source schema change breaks connector | Medium | Medium | Schema version detection; alert on first mismatch; fallback to last-known-good snapshot |
| PAN collision (two businesses share one PAN — fraud/data error) | Low | High | PAN mismatch hard rule → Forced Separate + compliance team alert |
| Reviewer inconsistency | High | Medium | Inter-rater reliability score tracked; high-disagreement pairs escalated to senior reviewer |

**Top Organisational Risks:**
- **Department reluctance to share data:** Mitigated by read-only integration (data never leaves dept DB; platform only reads)
- **Review queue backlog:** Auto-link rate targets ≥70%; batch review mode for bulk similar cases
- **Staff turnover:** Decisions in structured format, not in reviewers' heads; SOPs in Kannada and English

**Key Trade-off Decisions:**

| Trade-off | Our Choice | Rejected Alternative | Why |
|---|---|---|---|
| Precision vs. Recall | High precision (0.95 threshold) | High recall (0.85 threshold) | Wrong merge corrupts registry integrity permanently |
| ML model | LightGBM (interpretable, CPU-efficient) | BERT-based deep learning | Explainability requirement; GPU dependency rejected |
| Activity inference | Rule-based weighted decay scoring | ML classifier on event sequences | No labelled activity data exists yet; rule-based is transparent and tunable |
| LLM usage | Local on-prem only for data-touching tasks | Hosted LLM API | Violates PII non-negotiable — rejected unconditionally |

**Visual Suggestion:**
- Risk matrix (2×2: likelihood vs. impact) with risks plotted
- Trade-off comparison as "road not taken" split-lane visual
- Callout: *"Our defaults are conservative. Precision over recall. Explainability over accuracy ceiling."*

---

## SLIDE 14 — Edge Cases & Failure Mode Analysis

**Purpose:** Demonstrate depth of thinking about corner cases — a strong differentiator that scores on problem understanding AND technical implementation.

**Content Type:** Case study cards (4–5 compact scenarios with how the system handles each).

**Key Points to Cover:**

**Entity Resolution Edge Cases:**

**Case 1 — Multi-Site Business Group**
- 3 factories under one PAN → 3 separate UBIDs + 1 parent UBID linked to PAN
- Relationship type: `PARENT_SUBSIDIARY`, not `DUPLICATE`
- Factories remain distinct for inspection; queryable as group

**Case 2 — Business Name Change After Ownership Transfer**
- "Murugan Granites" → "Sri Venkateshwara Stone Works" (new PAN, same address)
- Correctly creates two separate UBIDs (different PANs)
- Address overlap flagged → reviewer can establish `SUCCESSOR_TO` link
- Never auto-merged

**Case 3 — Intra-Department Duplicate (Re-registration After Fire)**
- F12 (Same-Source Flag) = 1 → raises suspicion threshold
- Pair routed to review for departmental officer to confirm duplication
- Higher confidence required for intra-department auto-link

**Case 4 — Missing PAN Across All Systems**
- Assigned internally generated UBID with `UNANCHORED` flag
- Flagged for enrichment; anchorable later via direct business contact

**Activity Inference Edge Cases:**

**Case 5 — Seasonal Business Misclassified as Dormant**
- Fireworks manufacturer: near-zero consumption April–September
- Industry-specific seasonality profiles (mapped to NIC codes) adjust Dormant threshold for seasonal industries
- Baseline computed only on active-season months

**Case 6 — Closure Followed Immediately by Re-registration**
- Original UBID → Closed (Confirmed)
- New registration → New UBID created
- `SUCCESSOR_TO` link proposed for reviewer confirmation
- Two UBIDs never automatically merged

**Visual Suggestion:**
- 6 compact "Case Card" boxes in a 2×3 grid
- Each card: scenario name → challenge → how system handles it
- Color coding: blue for ER edge cases, orange for activity edge cases

---

## SLIDE 15 — Impact, Government Queries Enabled & Scalability Roadmap

**Purpose:** Close with ambition. Show the transformative potential. Score the full *Scalability & Long-Term Impact (15%)* dimension.

**Content Type:** Three-part layout: enabled queries | scalability table | long-term vision bullets.

**Key Points to Cover:**

**Government Queries Now Possible (Previously Impossible):**
- *"Active factories in pin code 560058 with no inspection in the last 18 months"*
- *"All businesses with KSPCB consent due for renewal in the next 30 days, cross-referenced with their Shop Establishment status"*
- *"Sector composition of active businesses across Bengaluru Urban by 2-digit NIC code"*
- *"Businesses with active electricity consumption but no valid trade licence in any system"*
- *"Historical activity trend for any UBID: show every event across all departments for the last 3 years"*

**Scalability Path (Pilot → Full Karnataka):**

| Dimension | Pilot Capacity | Full Karnataka |
|---|---|---|
| Business Records | ~50,000 | ~5M+ (PostgreSQL sharding by district) |
| Source Departments | 4 | 40+ (each new dept = one new connector) |
| Event Volume | ~100K events/month | ~50M events/month (Kafka partitioning) |
| Reviewer Workload | 1–3 reviewers | 20–50 reviewers across districts |
| Blocking Computation | Minutes (single node) | Hours (parallelised via Spark/Dask on NIC cluster) |

**Long-Term Impact Vision:**
- **Single Window Clearance:** UBID enables pre-filled licence applications — business identified on arrival, profile pulled from all departments
- **Risk-Based Inspection Targeting:** Data-driven selection of inspection targets — maximise regulatory impact per officer-hour
- **Industrial Policy Intelligence:** Near-real-time sector composition, geographic distribution, growth trends
- **Central System Convergence:** UBID anchored to PAN/GSTIN → cross-reference with MCA21, EPFO, GST for comprehensive national business intelligence
- **Replicable Template:** Architecture is state-agnostic — other states can adopt with only source connectors replaced

**Success Metrics for Round 2:**

| Metric | Target |
|---|---|
| Entity Resolution F1 Score | ≥ 0.92 |
| Blocking Pair Recall | ≥ 99.5% |
| Auto-link Rate | 60–75% |
| Activity Classification Accuracy | ≥ 88% |
| UBID Lookup Response Time (p99) | < 200ms |
| Unmatched Event Rate | < 5% |

**Visual Suggestion:**
- Karnataka district map with colour-coded "active business density" heatmap (synthetic data)
- Timeline showing phased rollout: Pilot (4 depts, 2 pin codes) → Phase 2 (all Bengaluru Urban) → Phase 3 (all Karnataka)
- Bold closing statement: *"UBID becomes the foundational business intelligence layer for Karnataka's entire regulatory ecosystem"*

---

## APPENDIX NOTES — Optional Bonus Slides

If time/slide count permits, consider adding:

**Bonus Slide A — Demo Storyboard**
Scene-by-scene outline of the 15-minute demo flow (matches §9 of the implementation document):
- Scene 1: Raw records of same business in 4 systems (the problem made visual)
- Scene 2: Normalisation engine live run
- Scene 3: Blocking + scoring + SHAP waterfall
- Scene 4: Review UI — confirm a 0.93-confidence match
- Scene 5: Activity classification with evidence timeline
- Scene 6: THE QUERY — "Active factories in 560058 with no inspection in 18 months"
- Scene 7: Analytics dashboard overview

**Bonus Slide B — 8-Week Round 2 Implementation Plan**

| Week | Phase | Key Deliverables |
|---|---|---|
| 1–2 | Foundation | Source connectors (4 systems); normalisation engine; PII scrambler; 5,000-entity synthetic dataset |
| 3 | Blocking & Features | Multi-key blocking engine; all 13 features; recall validation |
| 4 | ML Scoring | LightGBM training; Platt calibration; SHAP integration; MLflow versioning |
| 5 | UBID Registry | Union-Find; UBID assignment; PAN/GSTIN anchoring; provenance storage |
| 6 | Activity Engine | Event stream; UBID join; signal scoring; Active/Dormant/Closed; evidence builder |
| 7 | Application Layer | Reviewer UI; Lookup API; analytics dashboard; audit log |
| 8 | Integration & Demo | End-to-end test; demo scripted; documentation; performance benchmarks |

---

*End of PPT Outline — AI Bharat Hackathon 2025 | UBID Platform | Karnataka Commerce & Industry*