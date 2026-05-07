# UBID Platform — Comprehensive Prototype Build Plan
### AI Bharat Hackathon 2025 | Karnataka Commerce & Industry | Theme 1
### Full Technical Specification for Working Prototype

---

## Table of Contents

1. [Project Structure & Repository Layout](#1-project-structure--repository-layout)
2. [Environment Setup & Dependencies](#2-environment-setup--dependencies)
3. [Phase 1 — Synthetic Data Generation](#3-phase-1--synthetic-data-generation)
4. [Phase 2 — Database Schema & Setup](#4-phase-2--database-schema--setup)
5. [Phase 3 — Normalisation Engine](#5-phase-3--normalisation-engine)
6. [Phase 4 — Entity Resolution ML Pipeline](#6-phase-4--entity-resolution-ml-pipeline)
7. [Phase 5 — Activity Intelligence Engine](#7-phase-5--activity-intelligence-engine)
8. [Phase 6 — FastAPI Backend](#8-phase-6--fastapi-backend)
9. [Phase 7 — React Frontend](#9-phase-7--react-frontend)
10. [Phase 8 — Docker Compose & Integration](#10-phase-8--docker-compose--integration)
11. [Phase 9 — Demo Preparation & Pre-computation](#11-phase-9--demo-preparation--pre-computation)
12. [Testing Strategy](#12-testing-strategy)
13. [Success Metrics Validation](#13-success-metrics-validation)
14. [Day-by-Day Build Schedule](#14-day-by-day-build-schedule)

---

## 1. Project Structure & Repository Layout

Create this exact folder structure before writing a single line of code. Every developer on the team needs to know where everything lives.

```
ubid-platform/
│
├── docker-compose.yml                  # Spins up entire stack
├── .env                                # Environment variables (never commit real secrets)
├── .env.example                        # Template for .env
├── README.md
│
├── data/                               # Generated synthetic data (git-ignored)
│   ├── raw/                            # Simulated dept system exports (CSVs)
│   │   ├── shop_establishment.csv
│   │   ├── factories.csv
│   │   ├── labour.csv
│   │   ├── kspcb.csv
│   │   └── activity_events.csv
│   ├── processed/                      # Normalised records after Stage 1
│   └── ground_truth/                   # Known entity clusters for training/eval
│       ├── labelled_pairs.csv          # (pair_id, record_a_id, record_b_id, label)
│       └── entity_clusters.csv         # (entity_id, source_system, source_record_id)
│
├── scripts/                            # One-shot execution scripts
│   ├── generate_synthetic_data.py      # Phase 1 — run once to populate data/
│   ├── run_pipeline.py                 # Phase 4+5 — runs full ER + activity pipeline
│   ├── train_model.py                  # Standalone model training
│   └── reset_demo.py                   # Wipes UBID registry, re-runs pipeline fresh
│
├── src/
│   ├── data_generation/
│   │   ├── __init__.py
│   │   ├── entity_generator.py         # Ground-truth business entity generator
│   │   ├── department_record_generator.py  # Per-dept record variants
│   │   ├── variation_injector.py       # Typos, abbreviations, address formats
│   │   ├── activity_event_generator.py # 12-month event stream per entity
│   │   └── dictionaries/
│   │       ├── karnataka_business_names.py
│   │       ├── karnataka_street_names.py
│   │       ├── nic_codes.py
│   │       └── pin_codes.py
│   │
│   ├── normalisation/
│   │   ├── __init__.py
│   │   ├── name_normaliser.py
│   │   ├── address_parser.py
│   │   ├── identifier_validator.py
│   │   ├── pii_scrambler.py
│   │   ├── geocoder.py
│   │   └── standardiser.py             # Orchestrator
│   │
│   ├── entity_resolution/
│   │   ├── __init__.py
│   │   ├── blocker.py
│   │   ├── feature_extractor.py
│   │   ├── scorer.py
│   │   ├── ubid_assigner.py
│   │   └── models/                     # Saved LightGBM model artefacts
│   │       ├── lgbm_model.pkl
│   │       └── calibrated_model.pkl
│   │
│   ├── activity_engine/
│   │   ├── __init__.py
│   │   ├── event_router.py
│   │   ├── signal_scorer.py
│   │   ├── activity_classifier.py
│   │   └── signal_config.py            # Weights and half-lives per event type
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py               # SQLAlchemy engine + session factory
│   │   ├── models.py                   # ORM table definitions
│   │   └── migrations/                 # Alembic migration scripts
│   │
│   └── api/
│       ├── __init__.py
│       ├── main.py                     # FastAPI app entrypoint
│       ├── routers/
│       │   ├── ubid.py
│       │   ├── activity.py
│       │   ├── review.py
│       │   └── admin.py
│       ├── schemas/                    # Pydantic request/response models
│       │   ├── ubid_schemas.py
│       │   ├── activity_schemas.py
│       │   ├── review_schemas.py
│       │   └── admin_schemas.py
│       └── dependencies.py             # DB session injection, auth stubs
│
├── frontend/
│   ├── package.json
│   ├── public/
│   └── src/
│       ├── App.jsx
│       ├── index.jsx
│       ├── api/
│       │   └── client.js               # axios wrapper with base URL
│       ├── components/
│       │   ├── UBIDLookup/
│       │   ├── ActivityDashboard/
│       │   ├── ReviewerQueue/
│       │   └── AnalyticsDashboard/
│       └── pages/
│           ├── LookupPage.jsx
│           ├── ActivityPage.jsx
│           ├── ReviewPage.jsx
│           └── DashboardPage.jsx
│
└── tests/
    ├── test_normalisation.py
    ├── test_blocker.py
    ├── test_features.py
    ├── test_scorer.py
    ├── test_activity_engine.py
    └── test_api.py
```

---

## 2. Environment Setup & Dependencies

### 2.1 Python Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

**`requirements.txt` — complete list with pinned versions:**

```
# Database
sqlalchemy==2.0.23
alembic==1.13.0
psycopg2-binary==2.9.9

# Data generation
faker==21.0.0
numpy==1.26.2
pandas==2.1.4

# Normalisation
rapidfuzz==3.5.2
indic-transliteration==2.3.57
metaphone==0.6
jellyfish==1.0.3
geopy==2.4.1
requests==2.31.0          # For Nominatim geocoding calls

# Entity resolution / ML
lightgbm==4.1.0
scikit-learn==1.3.2
shap==0.44.0
networkx==3.2.1
h3==3.7.6                 # Hex grid for geo-blocking
mlflow==2.9.2

# Activity engine
python-dateutil==2.8.2

# API
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.2
python-dotenv==1.0.0
python-jose[cryptography]==3.3.0   # JWT auth stubs
passlib[bcrypt]==1.7.4

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2

# Utilities
tqdm==4.66.1
loguru==0.7.2
```

### 2.2 Node / Frontend Environment

```bash
cd frontend
npx create-react-app . --template typescript  # or plain JS
npm install antd axios recharts react-leaflet @ant-design/icons
npm install react-router-dom
```

### 2.3 `.env` File Template

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ubid_platform
POSTGRES_USER=ubid_user
POSTGRES_PASSWORD=your_password_here

# PII Scrambler secret (never use a real key here)
SCRAMBLER_SECRET_KEY=dev_secret_key_replace_in_prod

# Nominatim (geocoding) - points to local Docker container
NOMINATIM_URL=http://localhost:8080

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Demo mode flag - skips real-time pipeline, serves pre-computed data
DEMO_MODE=true
```

---

## 3. Phase 1 — Synthetic Data Generation

**Target duration: Days 1–2**
**Goal:** 5,000 ground-truth business entities → ~15,000–20,000 department records → ~120,000 activity events

This is the most important phase. If your synthetic data is poor, every downstream component will be untestable.

### 3.1 `entity_generator.py` — Ground Truth Business Entities

This generates the "true" entities before any variation is injected. Think of this as the master registry of what reality looks like.

**What each entity record contains:**

```python
{
    "entity_id": "ENT_000001",           # Internal ground truth ID
    "true_name": "Peenya Garments Pvt Ltd",
    "true_pan": "AABCP1234Q",            # Valid format; ~40% of entities have PAN
    "true_gstin": "29AABCP1234Q1Z5",     # Present only if PAN present; ~60% of PAN holders
    "true_address": {
        "building": "Plot No. 14-A",
        "street": "3rd Main Road",
        "locality": "Peenya Industrial Area Phase 2",
        "ward": None,
        "taluk": "Bengaluru North",
        "district": "Bengaluru Urban",
        "pin_code": "560058",
        "industrial_area": "KIADB Peenya Phase 2"
    },
    "true_lat": 13.0287,
    "true_lng": 77.5201,
    "nic_code_2digit": "14",             # NIC 2-digit: 14 = Wearing apparel
    "nic_code_4digit": "1410",
    "owner_name": "Ramesh Kumar",
    "phone": "9845012345",
    "registration_year": 2008,
    "entity_type": "factory",            # factory / shop / service / home_based
    "is_seasonal": False,
    "seasonal_months": [],               # [10,11,12,1,2,3] for seasonal businesses
    "ground_truth_status": "active",     # active / dormant / closed
    "closure_date": None                 # Set if status=closed
}
```

**Generation logic:**

```python
# Entity distribution to match real Karnataka industrial data
ENTITY_TYPE_DISTRIBUTION = {
    "factory": 0.35,
    "shop": 0.40,
    "service": 0.20,
    "home_based": 0.05
}

NIC_CODE_DISTRIBUTION = {
    "14": 0.15,   # Wearing apparel
    "25": 0.12,   # Fabricated metal products
    "47": 0.20,   # Retail trade
    "46": 0.15,   # Wholesale trade
    "10": 0.08,   # Food products
    "62": 0.10,   # IT/Software
    "43": 0.10,   # Specialised construction
    "32": 0.10,   # Other manufacturing
}

# PAN/GSTIN presence rates per department
PAN_PRESENCE_RATE = {
    "shop_establishment": 0.15,
    "factories": 0.45,
    "labour": 0.40,
    "kspcb": 0.65
}

# Ground truth status distribution
STATUS_DISTRIBUTION = {
    "active": 0.75,
    "dormant": 0.15,
    "closed": 0.05,
    "seasonal_active": 0.05
}
```

**Pin codes to use (2 Bengaluru Urban pin codes as per problem statement):**
- `560058` — Peenya Industrial Area (factories, manufacturing heavy)
- `560073` — Rajajinagar / Basaveshwara Nagar (mixed commercial + service)

Generate ~2,500 entities per pin code.

### 3.2 `department_record_generator.py` — Per-Department Records

For each ground truth entity, generate 2–5 department records with controlled variations. Each business appears in a subset of departments (not all businesses appear in all 4).

**Department presence probability per entity type:**

```python
DEPT_PRESENCE = {
    "shop_establishment": {"factory": 0.9, "shop": 0.99, "service": 0.95, "home_based": 0.7},
    "factories": {"factory": 0.95, "shop": 0.05, "service": 0.1, "home_based": 0.0},
    "labour": {"factory": 0.85, "shop": 0.4, "service": 0.5, "home_based": 0.1},
    "kspcb": {"factory": 0.8, "shop": 0.05, "service": 0.05, "home_based": 0.0}
}
```

**Schema for each department record:**

```python
# shop_establishment table
{
    "se_reg_no": "SE/BNG/2008/047823",   # Auto-generated sequential
    "business_name": "...",               # VARIED version of true_name
    "owner_name": "...",                  # VARIED version of true owner
    "address": "...",                     # VARIED version of true address (free text)
    "pin_code": "560058",
    "pan": "...",                         # May be absent, present, or slightly wrong
    "gstin": "...",
    "phone": "...",
    "trade_category": "...",              # Free text; maps loosely to NIC
    "registration_date": "2008-03-15",
    "status": "active",
    "entity_id": "ENT_000001"            # Ground truth link — NEVER exposed to pipeline
}

# factories table
{
    "factory_licence_no": "KA/FAC/2008/001234",
    "factory_name": "...",
    "owner_name": "...",
    "address": "...",                     # Survey number format common here
    "pin_code": "560058",
    "pan": "...",
    "gstin": "...",
    "phone": "...",
    "product_description": "...",
    "nic_code": "1410",
    "num_workers": 45,
    "licence_valid_until": "2025-12-31",
    "registration_date": "2008-04-01",
    "entity_id": "ENT_000001"
}

# Similar schemas for labour and kspcb tables
```

### 3.3 `variation_injector.py` — The Hard Part

This is what makes your synthetic data realistic. Every department record's name, address, and identifiers must be varied from the ground truth in controlled, realistic ways.

**Name variation rules (apply each with configured probability):**

```python
VARIATION_CONFIG = {
    # Legal suffix variations — apply to ~30% of records
    "legal_suffix": {
        "probability": 0.30,
        "mappings": {
            "Private Limited": ["Pvt Ltd", "P Ltd", "Pvt. Ltd.", "Private Ltd", "Pvt.Ltd"],
            "Limited Liability Partnership": ["LLP", "L.L.P"],
            "Proprietorship": ["Prop.", "Propr.", "(Prop)"],
            "": ["& Co.", "& Sons", "Enterprises", "Industries"]  # Sometimes added
        }
    },
    # Abbreviation variations — apply to ~25% of records
    "abbreviation": {
        "probability": 0.25,
        "word_mappings": {
            "Industries": ["Inds", "Inds.", "INDS", "Indus"],
            "Manufacturing": ["Mfg", "Mfg.", "MFG"],
            "Engineering": ["Engg", "Engg.", "Eng"],
            "Bengaluru": ["Bangalore", "B'lore", "BLR", "Blore"],
            "Karnataka": ["KA", "Karn."],
            "International": ["Intl", "Int'l"],
            "Exports": ["Expts", "Exp"],
            "Granites": ["Granits", "Grantz"]   # Common typo
        }
    },
    # Typo injection — apply to ~15% of records
    "typos": {
        "probability": 0.15,
        "operations": ["swap_chars", "delete_char", "double_char", "adjacent_key"]
    },
    # Transliteration variation — apply to ~10% of Kannada-origin names
    "transliteration": {
        "probability": 0.10,
        "examples": {
            "Srinivasa": ["Shrinivasa", "Sreenivasa", "Sriniwasa"],
            "Venkatesh": ["Venkatesh", "Venkataish", "Venkatesa"],
            "Manjunath": ["Manjunatha", "Munjunath", "Manjunath"]
        }
    }
}
```

**Address variation rules:**

```python
ADDRESS_VARIATION_FORMATS = [
    # Format 1: BBMP-style (used in Shop Establishment mostly)
    lambda e: f"#{e['building']}, {e['street']}, {e['locality']}, Bengaluru - {e['pin_code']}",
    
    # Format 2: Industrial estate style (used in Factories, KSPCB)
    lambda e: f"Plot No. {e['building']}, KIADB Industrial Area, Peenya, Bengaluru {e['pin_code']}",
    
    # Format 3: Survey number style (used in rural/semi-urban)
    lambda e: f"Sy. No. {random.randint(100,300)}/{random.randint(1,10)}, {e['locality']}, {e['pin_code']}",
    
    # Format 4: Landmark-based (common in older records)
    lambda e: f"Near {random.choice(LANDMARKS)}, {e['locality']}, Bengaluru",
    
    # Format 5: Minimal (just locality + pin)
    lambda e: f"{e['locality']}, Bengaluru - {e['pin_code']}"
]
```

**PAN/GSTIN injection rules:**

```python
def inject_pan(true_pan, dept, presence_rate):
    rand = random.random()
    if rand > presence_rate:
        return None  # Absent in this dept record
    elif rand < 0.03:  # 3% chance of data entry error
        # Corrupt one character
        pos = random.randint(5, 8)
        return true_pan[:pos] + random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") + true_pan[pos+1:]
    else:
        return true_pan  # Correct PAN
```

**Intra-department duplicate injection (8% of entities per dept):**
- Select 8% of entities in each department
- Create a second record for that entity in the same department
- Apply heavier name variation (different suffix + different address format)
- This simulates re-registration after fire, address change, officer error

### 3.4 `activity_event_generator.py` — 12-Month Event Stream

Generate events for the period `2024-05-01` to `2025-04-30` (12 months leading up to demo date).

**Event type definitions with generation rules:**

```python
SIGNAL_CONFIG = {
    "electricity_consumption_high": {
        "weight": +0.90,
        "half_life_days": 45,
        "source_system": "bescom",
        "frequency": "monthly",              # Generate one per month for active businesses
        "payload_fields": ["kwh_consumed", "billing_month", "consumer_no", "account_type"]
    },
    "electricity_consumption_low": {
        "weight": -0.50,
        "half_life_days": 30,
        "source_system": "bescom",
        "frequency": "monthly",
        "payload_fields": ["kwh_consumed", "billing_month", "consumer_no", "account_type"]
    },
    "licence_renewal": {
        "weight": +0.80,
        "half_life_days": 365,
        "source_system": "shop_establishment",  # or factories, labour, kspcb
        "frequency": "annual",
        "payload_fields": ["licence_no", "valid_from", "valid_until", "fee_paid"]
    },
    "inspection_visit": {
        "weight": +0.70,
        "half_life_days": 180,
        "source_system": "factories",           # or labour, kspcb, fire
        "frequency": "irregular",              # 1–3 per year for active factories
        "payload_fields": ["inspector_id", "inspection_type", "outcome", "violations_noted"]
    },
    "compliance_filing": {
        "weight": +0.75,
        "half_life_days": 270,
        "source_system": "kspcb",
        "frequency": "quarterly",
        "payload_fields": ["filing_type", "period_covered", "submission_date"]
    },
    "administrative_update": {
        "weight": +0.40,
        "half_life_days": 90,
        "source_system": "any",
        "frequency": "rare",                   # ~20% of businesses per year
        "payload_fields": ["update_type", "old_value", "new_value"]
    },
    "renewal_overdue": {
        "weight": -0.40,
        "half_life_days": 180,
        "source_system": "shop_establishment",
        "frequency": "derived",               # Generated if renewal_date has passed with no renewal
        "payload_fields": ["licence_no", "days_overdue", "original_due_date"]
    },
    "closure_declaration": {
        "weight": -1.00,
        "half_life_days": None,               # Permanent
        "source_system": "any",
        "frequency": "once",                  # Only for entities with status=closed
        "payload_fields": ["closure_reason", "closure_date", "declared_by"]
    }
}
```

**Activity pattern per ground truth status:**

```python
EVENT_PATTERNS = {
    "active": {
        "electricity_monthly_kwh_range": (2000, 8000),    # Commercial range
        "high_consumption_threshold": 0.50,               # >50% of baseline = high signal
        "inspection_count_per_year": (1, 3),
        "licence_renewal_probability": 0.92,
        "compliance_filing_probability": 0.88,
        "closure_probability": 0.0
    },
    "dormant": {
        "electricity_monthly_kwh_range": (50, 400),       # Low but not zero
        "high_consumption_threshold": 0.50,
        "inspection_count_per_year": (0, 1),
        "licence_renewal_probability": 0.45,              # Often miss renewals
        "compliance_filing_probability": 0.30,
        "closure_probability": 0.0
    },
    "closed": {
        "electricity_monthly_kwh_range": (0, 30),         # Near zero
        "high_consumption_threshold": 0.50,
        "inspection_count_per_year": (0, 0),
        "licence_renewal_probability": 0.0,
        "closure_declaration": True,                      # Always has this event
        "closure_probability": 1.0
    },
    "seasonal_active": {
        "active_months": [10, 11, 12, 1, 2, 3],          # Oct–Mar
        "inactive_months": [4, 5, 6, 7, 8, 9],
        "active_kwh_range": (3000, 9000),
        "inactive_kwh_range": (0, 50)
    }
}
```

**Final CSV schemas after generation:**

`data/raw/activity_events.csv`:
```
event_id, source_system, source_record_id, event_type, event_timestamp,
entity_id (ground truth — strip before giving to pipeline),
payload_json, processed
```

---

## 4. Phase 2 — Database Schema & Setup

**Target duration: Day 2–3**

### 4.1 `database/models.py` — Complete SQLAlchemy ORM

```python
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# ─── SOURCE SYSTEM TABLES (simulates dept databases, read-only in production) ───

class DeptShopEstablishment(Base):
    __tablename__ = "dept_shop_establishment"
    se_reg_no = Column(String(30), primary_key=True)
    business_name = Column(String(255), nullable=False)
    owner_name = Column(String(100))
    address = Column(Text)
    pin_code = Column(String(6))
    pan = Column(String(10))
    gstin = Column(String(15))
    phone = Column(String(15))
    trade_category = Column(String(100))
    registration_date = Column(DateTime)
    status = Column(String(20))

class DeptFactories(Base):
    __tablename__ = "dept_factories"
    factory_licence_no = Column(String(30), primary_key=True)
    factory_name = Column(String(255), nullable=False)
    owner_name = Column(String(100))
    address = Column(Text)
    pin_code = Column(String(6))
    pan = Column(String(10))
    gstin = Column(String(15))
    phone = Column(String(15))
    nic_code = Column(String(6))
    num_workers = Column(Integer)
    licence_valid_until = Column(DateTime)
    registration_date = Column(DateTime)
    status = Column(String(20))

class DeptLabour(Base):
    __tablename__ = "dept_labour"
    employer_code = Column(String(30), primary_key=True)
    employer_name = Column(String(255), nullable=False)
    owner_name = Column(String(100))
    address = Column(Text)
    pin_code = Column(String(6))
    pan = Column(String(10))
    gstin = Column(String(15))
    phone = Column(String(15))
    industry_type = Column(String(100))
    num_employees = Column(Integer)
    registration_date = Column(DateTime)
    status = Column(String(20))

class DeptKSPCB(Base):
    __tablename__ = "dept_kspcb"
    consent_order_no = Column(String(30), primary_key=True)
    unit_name = Column(String(255), nullable=False)
    owner_name = Column(String(100))
    address = Column(Text)
    pin_code = Column(String(6))
    pan = Column(String(10))
    gstin = Column(String(15))
    phone = Column(String(15))
    nic_code = Column(String(6))
    consent_type = Column(String(20))    # 'establish' or 'operate'
    consent_valid_until = Column(DateTime)
    registration_date = Column(DateTime)
    status = Column(String(20))

class ActivityEventRaw(Base):
    __tablename__ = "activity_events_raw"
    event_id = Column(String(40), primary_key=True)
    source_system = Column(String(50), nullable=False)
    source_record_id = Column(String(50), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_timestamp = Column(DateTime, nullable=False)
    payload = Column(JSONB)
    processed = Column(Boolean, default=False)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_activity_events_processed", "processed"),
        Index("idx_activity_events_source", "source_system", "source_record_id"),
    )

# ─── UBID REGISTRY TABLES (platform's own storage) ───

class UBIDEntity(Base):
    __tablename__ = "ubid_entities"
    ubid = Column(String(20), primary_key=True)     # KA-UBID-XXXXXX
    pan_anchor = Column(String(10), index=True)
    gstin_anchors = Column(ARRAY(String))
    activity_status = Column(String(20), default="UNKNOWN")
    anchor_status = Column(String(20), default="UNANCHORED")  # ANCHORED / UNANCHORED
    relationship_type = Column(String(20), default="STANDALONE")  # STANDALONE / SUBSIDIARY / PARENT
    parent_ubid = Column(String(20), ForeignKey("ubid_entities.ubid"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    __table_args__ = (
        Index("idx_ubid_pan", "pan_anchor"),
        Index("idx_ubid_status", "activity_status"),
    )

class UBIDSourceLink(Base):
    __tablename__ = "ubid_source_links"
    link_id = Column(String(40), primary_key=True)
    ubid = Column(String(20), ForeignKey("ubid_entities.ubid"), nullable=False, index=True)
    source_system = Column(String(50), nullable=False)
    source_record_id = Column(String(50), nullable=False)
    confidence = Column(Float)
    link_type = Column(String(10))      # 'auto' or 'manual'
    linked_by = Column(String(50))      # 'system' or reviewer user ID
    linked_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_source_link_source", "source_system", "source_record_id"),
    )

class UBIDLinkEvidence(Base):
    __tablename__ = "ubid_link_evidence"
    evidence_id = Column(String(40), primary_key=True)
    link_id = Column(String(40), ForeignKey("ubid_source_links.link_id"), nullable=False)
    pair_record_a = Column(String(50))       # source_system:source_record_id
    pair_record_b = Column(String(50))
    feature_vector = Column(JSONB)           # {F01: 0.92, F02: 87.3, ...}
    shap_values = Column(JSONB)              # {F01: +0.32, F02: +0.18, ...}
    raw_score = Column(Float)
    calibrated_score = Column(Float)
    decision = Column(String(20))            # 'AUTO_LINK' / 'REVIEW' / 'KEEP_SEPARATE'
    model_version = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())

class ReviewTask(Base):
    __tablename__ = "review_tasks"
    task_id = Column(String(40), primary_key=True)
    pair_record_a = Column(String(50), nullable=False)
    pair_record_b = Column(String(50), nullable=False)
    evidence_id = Column(String(40), ForeignKey("ubid_link_evidence.evidence_id"))
    calibrated_score = Column(Float)
    assigned_to = Column(String(50))
    status = Column(String(20), default="PENDING")  # PENDING / IN_REVIEW / DECIDED / DEFERRED
    decision = Column(String(30))  # CONFIRM_MATCH / CONFIRM_NON_MATCH / CONFIRM_PARTIAL / REQUEST_INFO / DEFER
    decision_reason = Column(Text)
    decided_by = Column(String(50))
    decided_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    priority = Column(Integer, default=5)           # 1 = highest, 10 = lowest

    __table_args__ = (
        Index("idx_review_status", "status"),
        Index("idx_review_priority", "priority"),
    )

class UBIDActivityEvent(Base):
    __tablename__ = "ubid_activity_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ubid = Column(String(20), ForeignKey("ubid_entities.ubid"), nullable=False, index=True)
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
    )

class ActivityScore(Base):
    __tablename__ = "activity_scores"
    score_id = Column(String(40), primary_key=True)
    ubid = Column(String(20), ForeignKey("ubid_entities.ubid"), nullable=False, index=True)
    computed_at = Column(DateTime, server_default=func.now())
    raw_score = Column(Float)
    activity_status = Column(String(20))    # ACTIVE / DORMANT / CLOSED_SUSPECTED / CLOSED_CONFIRMED
    lookback_days = Column(Integer, default=365)
    evidence_snapshot = Column(JSONB)       # Full list of contributing signals with weights
    is_current = Column(Boolean, default=True, index=True)
    manually_overridden = Column(Boolean, default=False)
    override_by = Column(String(50))
    override_reason = Column(Text)

class UnmatchedEvent(Base):
    __tablename__ = "unmatched_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_event_id = Column(String(40))
    source_system = Column(String(50))
    source_record_id = Column(String(50))
    event_type = Column(String(50))
    event_timestamp = Column(DateTime)
    reason_unmatched = Column(String(100))  # 'NO_SOURCE_LINK' / 'KEEP_SEPARATE_POOL' / 'UNKNOWN_SOURCE'
    triage_status = Column(String(20), default="PENDING")
    accumulated_count = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
```

### 4.2 Alembic Setup

```bash
alembic init src/database/migrations
# Edit alembic.ini to point to your DB URL from .env
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

### 4.3 `database/connection.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)

engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI dependency — yields a DB session and closes it after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 5. Phase 3 — Normalisation Engine

**Target duration: Days 3–4**
**Critical rule: Write unit tests for every function here. This is where most bugs hide.**

### 5.1 `normalisation/name_normaliser.py` — Complete Implementation

```python
import re
import unicodedata
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from metaphone import doublemetaphone
import jellyfish

# ─── DICTIONARIES ───

LEGAL_SUFFIX_PATTERNS = [
    r'\bPRIVATE LIMITED\b', r'\bPVT\.?\s*LTD\.?\b', r'\bP\.?\s*LTD\.?\b',
    r'\bLIMITED\b', r'\bLTD\.?\b', r'\bLLP\b', r'\bL\.L\.P\b',
    r'\bPROPRIETORSHIP\b', r'\bPROP\.?\b', r'\bPROPR\.?\b',
    r'\bFIRM\b', r'\bCO-OP\b', r'\bSOCIETY\b', r'\bSOC\.?\b',
    r'\bENTERPRISES?\b', r'\bINDUSTRIES?\b(?!\s+\w)',  # only as suffix
    r'\b&\s*CO\.?\b', r'\b&\s*SONS?\b', r'\bAND\s+COMPANY\b',
    r'\bINC\.?\b', r'\bCORP\.?\b', r'\bCORPORATION\b',
    # Add all 47 variants — keep this comprehensive
]

ABBREVIATION_EXPANSIONS = {
    "INDS": "INDUSTRIES", "IND": "INDUSTRIES",
    "MFG": "MANUFACTURING", "MFRS": "MANUFACTURERS",
    "ENG": "ENGINEERING", "ENGG": "ENGINEERING",
    "TRD": "TRADING", "TRDG": "TRADING",
    "EXPTS": "EXPORTS", "EXP": "EXPORTS",
    "INTL": "INTERNATIONAL", "INT": "INTERNATIONAL",
    "BLR": "BENGALURU", "B'LORE": "BENGALURU", "BLORE": "BENGALURU",
    "BANGALORE": "BENGALURU",
    "KA": "KARNATAKA", "KARN": "KARNATAKA",
    "GOVT": "GOVERNMENT", "GOV": "GOVERNMENT",
    "CORP": "CORPORATION",
    "ASSOC": "ASSOCIATION", "ASSN": "ASSOCIATION",
    "MKTG": "MARKETING", "MKT": "MARKETING",
    "TECH": "TECHNOLOGIES", "TECHNO": "TECHNOLOGIES",
    # ... expand to 180+ terms from real Karnataka business registration data
}

CITY_NORMALISATION = {
    "BANGALORE": "BENGALURU",
    "B'LORE": "BENGALURU",
    "BLR": "BENGALURU",
    "BLORE": "BENGALURU",
    "MANGALORE": "MANGALURU",
    "MYSORE": "MYSURU",
    "BELGAUM": "BELAGAVI",
    "GULBARGA": "KALABURAGI",
    "HUBLI": "HUBBALLI",
}


def canonicalise_name(raw_name: str) -> dict:
    """
    Takes a raw business name and returns a dict with:
    - canonical: cleaned comparison string
    - soundex: Soundex key
    - metaphone: Double-metaphone key tuple
    - original: original input preserved unchanged
    """
    if not raw_name:
        return {"canonical": "", "soundex": "", "metaphone": ("", ""), "original": ""}

    # Step 1: Uppercase + strip
    name = raw_name.upper().strip()
    original = name

    # Step 2: Transliterate Kannada if present
    if any('\u0C80' <= c <= '\u0CFF' for c in name):
        name = transliterate(name, sanscript.KANNADA, sanscript.IAST)
        # Post-process IAST to simplified Latin
        name = _iast_to_simple_latin(name)

    # Step 3: Normalise city names
    for variant, canonical_city in CITY_NORMALISATION.items():
        name = re.sub(r'\b' + variant + r'\b', canonical_city, name)

    # Step 4: Strip legal suffixes
    for pattern in LEGAL_SUFFIX_PATTERNS:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    # Step 5: Expand abbreviations (word boundary match)
    words = name.split()
    expanded = []
    for word in words:
        clean_word = re.sub(r'[^A-Z0-9]', '', word)
        expanded.append(ABBREVIATION_EXPANSIONS.get(clean_word, word))
    name = ' '.join(expanded)

    # Step 6: Remove punctuation + extra spaces
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()

    # Step 7: Generate phonetic keys from the FIRST meaningful word
    first_word = name.split()[0] if name.split() else ""
    soundex_key = jellyfish.soundex(first_word) if first_word else ""
    metaphone_key = doublemetaphone(first_word) if first_word else ("", "")

    return {
        "canonical": name,
        "soundex": soundex_key,
        "metaphone": metaphone_key,
        "original": original
    }


def _iast_to_simple_latin(iast_text: str) -> str:
    """Strip diacritics from IAST transliteration to get plain ASCII."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', iast_text)
        if unicodedata.category(c) != 'Mn'
    )
```

### 5.2 `normalisation/address_parser.py` — Karnataka-Specific Parsing

```python
import re
from dataclasses import dataclass, field
from typing import Optional

KARNATAKA_PIN_CODES = {
    "560058": {"locality": "Peenya", "district": "Bengaluru Urban", "taluk": "Bengaluru North"},
    "560073": {"locality": "Rajajinagar", "district": "Bengaluru Urban", "taluk": "Bengaluru North"},
    # Add all Karnataka pin codes — at minimum, the two demo pin codes and neighbours
}

PIN_ADJACENCY = {
    "560058": ["560057", "560022", "560032", "560073"],
    "560073": ["560010", "560086", "560058", "560040"],
}

INDUSTRIAL_AREA_KEYWORDS = [
    "KIADB", "KSSIDC", "PEENYA", "BOMMASANDRA", "WHITEFIELD",
    "JIGANI", "ELECTRONICS CITY", "INDUSTRIAL AREA", "INDL AREA",
    "INDUSTRIAL ESTATE", "INDL ESTATE"
]

@dataclass
class ParsedAddress:
    building: Optional[str] = None
    street: Optional[str] = None
    locality: Optional[str] = None
    landmark: Optional[str] = None
    ward: Optional[str] = None
    industrial_area: Optional[str] = None
    survey_plot_no: Optional[str] = None
    taluk: Optional[str] = None
    district: Optional[str] = None
    pin_code: Optional[str] = None
    address_type: str = "unknown"  # 'bbmp' / 'industrial' / 'survey' / 'landmark' / 'minimal'
    address_tokens: list = field(default_factory=list)

def parse_address(raw_address: str) -> ParsedAddress:
    if not raw_address:
        return ParsedAddress()

    addr = raw_address.upper().strip()
    parsed = ParsedAddress()

    # Extract pin code (always 6 digits, often at end)
    pin_match = re.search(r'\b(\d{6})\b', addr)
    if pin_match:
        parsed.pin_code = pin_match.group(1)
        addr = addr.replace(pin_match.group(0), '').strip()

    # Detect address type and extract accordingly
    if re.search(r'\bSY\.?\s*NO\.?\b|\bSURVEY\s+NO\b', addr, re.IGNORECASE):
        parsed.address_type = "survey"
        survey_match = re.search(r'SY\.?\s*NO\.?\s*([\d/]+)', addr, re.IGNORECASE)
        if survey_match:
            parsed.survey_plot_no = survey_match.group(1)

    elif any(kw in addr for kw in INDUSTRIAL_AREA_KEYWORDS):
        parsed.address_type = "industrial"
        plot_match = re.search(r'PLOT\s*NO\.?\s*([\w\-/]+)', addr, re.IGNORECASE)
        if plot_match:
            parsed.building = "Plot " + plot_match.group(1)
        for kw in INDUSTRIAL_AREA_KEYWORDS:
            if kw in addr:
                parsed.industrial_area = kw
                break

    elif re.search(r'#\s*\d+|NO\.\s*\d+|\d+\s*,\s*\d+\s*(ST|ND|RD|TH)', addr):
        parsed.address_type = "bbmp"
        building_match = re.search(r'#\s*([\w\-/]+)', addr)
        if building_match:
            parsed.building = building_match.group(1)
        cross_match = re.search(r'(\d+)\s*(ST|ND|RD|TH)\s*(CROSS|MAIN|ROAD)', addr, re.IGNORECASE)
        if cross_match:
            parsed.street = f"{cross_match.group(1)}{cross_match.group(2)} {cross_match.group(3)}"

    elif re.search(r'\bNEAR\b|\bOPP\.?\b|\bOPPOSITE\b|\bBEHIND\b', addr, re.IGNORECASE):
        parsed.address_type = "landmark"
        landmark_match = re.search(r'(?:NEAR|OPP\.?|OPPOSITE|BEHIND)\s+(.+?)(?:,|$)', addr, re.IGNORECASE)
        if landmark_match:
            parsed.landmark = landmark_match.group(1).strip()

    # Extract ward number if present
    ward_match = re.search(r'WARD\s*(?:NO\.?)?\s*(\d+)', addr, re.IGNORECASE)
    if ward_match:
        parsed.ward = ward_match.group(1)

    # Extract taluk
    taluk_match = re.search(r'TALUK\s*:?\s*(\w+)', addr, re.IGNORECASE)
    if taluk_match:
        parsed.taluk = taluk_match.group(1)

    # Use pin code lookup to fill district/taluk if empty
    if parsed.pin_code and parsed.pin_code in KARNATAKA_PIN_CODES:
        pin_data = KARNATAKA_PIN_CODES[parsed.pin_code]
        parsed.district = parsed.district or pin_data["district"]
        parsed.taluk = parsed.taluk or pin_data["taluk"]
        parsed.locality = parsed.locality or pin_data["locality"]

    # Generate address tokens for Jaccard similarity
    tokens = re.sub(r'[^\w\s]', ' ', addr).split()
    # Remove stop words and very short tokens
    stop_words = {"THE", "AND", "OF", "IN", "AT", "NO", "ST", "TH", "RD", "ND"}
    parsed.address_tokens = [t for t in tokens if len(t) > 2 and t not in stop_words]

    return parsed
```

### 5.3 `normalisation/identifier_validator.py`

```python
import re

def validate_and_normalise_pan(raw_pan: str) -> dict:
    """Returns: {valid: bool, normalised: str or None, has_value: bool}"""
    if not raw_pan or str(raw_pan).strip() in ('', 'NA', 'N/A', 'NIL', 'NONE', 'NULL'):
        return {"valid": False, "normalised": None, "has_value": False}

    pan = str(raw_pan).strip().upper().replace(' ', '').replace('-', '')

    # PAN format: AAAAA9999A — 5 alpha + 4 numeric + 1 alpha
    pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    is_valid = bool(re.match(pattern, pan))

    return {
        "valid": is_valid,
        "normalised": pan if is_valid else None,
        "has_value": True,
        "raw": raw_pan
    }

def validate_and_normalise_gstin(raw_gstin: str) -> dict:
    """Returns: {valid: bool, normalised: str, state_code: str, pan_embedded: str}"""
    if not raw_gstin or str(raw_gstin).strip() in ('', 'NA', 'N/A', 'NIL', 'NONE', 'NULL'):
        return {"valid": False, "normalised": None, "has_value": False}

    gstin = str(raw_gstin).strip().upper().replace(' ', '')

    # GSTIN: 2-digit state + 10-char PAN + 1 entity + 1 Z + 1 checksum
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    is_valid = bool(re.match(pattern, gstin))

    state_code = gstin[:2] if len(gstin) >= 2 else None
    pan_embedded = gstin[2:12] if len(gstin) >= 12 else None
    is_karnataka = state_code == "29"

    return {
        "valid": is_valid,
        "normalised": gstin if is_valid else None,
        "state_code": state_code,
        "pan_embedded": pan_embedded,
        "is_karnataka": is_karnataka,
        "has_value": True
    }
```

### 5.4 `normalisation/pii_scrambler.py`

```python
import hmac
import hashlib
import os
from src.data_generation.dictionaries.karnataka_business_names import SYNTHETIC_NAME_POOL
from src.data_generation.dictionaries.karnataka_street_names import SYNTHETIC_STREET_POOL

SECRET_KEY = os.getenv("SCRAMBLER_SECRET_KEY", "dev_key").encode()

# Fixed per-district date offset in days
DATE_OFFSET_DAYS = 385

# Fixed per-district pin offset
PIN_OFFSET = {
    "Bengaluru Urban": 100,
    "Mysuru": 200,
    "Belagavi": 300,
}

def scramble_business_name(name: str) -> str:
    """Deterministic scramble: same name always → same synthetic name."""
    if not name:
        return ""
    digest = hmac.new(SECRET_KEY, name.upper().encode(), hashlib.sha256).hexdigest()
    index = int(digest[:8], 16) % len(SYNTHETIC_NAME_POOL)
    return SYNTHETIC_NAME_POOL[index]

def scramble_pan(pan: str) -> str:
    """Structure-preserving PAN scramble: output is still valid PAN format."""
    if not pan or len(pan) != 10:
        return pan
    # Scramble positions 5-8 (the 4 numeric digits) and position 9 (last alpha)
    digest = hmac.new(SECRET_KEY, pan.encode(), hashlib.sha256).hexdigest()
    new_digits = str(int(digest[:8], 16) % 10000).zfill(4)
    new_last = chr(ord('A') + (int(digest[8:10], 16) % 26))
    return pan[:5] + new_digits + new_last

def scramble_gstin(gstin: str) -> str:
    """State code (29) is preserved. Remaining 13 chars scrambled structure-preservingly."""
    if not gstin or len(gstin) != 15:
        return gstin
    state_code = gstin[:2]   # Always preserve "29" for Karnataka
    pan_part = scramble_pan(gstin[2:12])
    digest = hmac.new(SECRET_KEY, gstin.encode(), hashlib.sha256).hexdigest()
    entity_num = str((int(digest[:2], 16) % 9) + 1)
    checksum = digest[2].upper()
    return f"{state_code}{pan_part}{entity_num}Z{checksum}"

def scramble_phone(phone: str) -> str:
    """Digit-by-digit substitution cipher. Same number → same synthetic number."""
    if not phone:
        return phone
    digit_map = {}
    digest = hmac.new(SECRET_KEY, b"phone_cipher", hashlib.sha256).hexdigest()
    for i in range(10):
        digit_map[str(i)] = str(int(digest[i*2:i*2+2], 16) % 10)
    return ''.join(digit_map.get(c, c) for c in phone)

def scramble_date(date_str: str) -> str:
    """Shift date by fixed offset. Preserves temporal ordering."""
    from datetime import datetime, timedelta
    try:
        dt = datetime.fromisoformat(date_str)
        shifted = dt + timedelta(days=DATE_OFFSET_DAYS)
        return shifted.isoformat()
    except Exception:
        return date_str

def scramble_record(record: dict) -> dict:
    """Apply all scrambling transforms to a normalised record dict."""
    scrambled = record.copy()
    if scrambled.get("business_name"):
        scrambled["business_name_scrambled"] = scramble_business_name(record["business_name"])
    if scrambled.get("pan"):
        scrambled["pan"] = scramble_pan(record["pan"])
    if scrambled.get("gstin"):
        scrambled["gstin"] = scramble_gstin(record["gstin"])
    if scrambled.get("phone"):
        scrambled["phone"] = scramble_phone(record["phone"])
    if scrambled.get("registration_date"):
        scrambled["registration_date"] = scramble_date(str(record["registration_date"]))
    return scrambled
```

### 5.5 `normalisation/geocoder.py`

```python
import requests
import os
from typing import Optional, Tuple

NOMINATIM_URL = os.getenv("NOMINATIM_URL", "http://localhost:8080")

def geocode_address(parsed_address) -> dict:
    """
    Calls self-hosted Nominatim. Returns lat/lng + quality flag.
    Quality: HIGH (street-level), MEDIUM (locality), LOW (pin code only), FAILED.
    """
    if not parsed_address:
        return {"lat": None, "lng": None, "quality": "FAILED"}

    # Build query string from most specific to least specific
    query_parts = []
    if parsed_address.street:
        query_parts.append(parsed_address.street)
    if parsed_address.locality:
        query_parts.append(parsed_address.locality)
    if parsed_address.district:
        query_parts.append(parsed_address.district)
    if parsed_address.pin_code:
        query_parts.append(parsed_address.pin_code)
    query_parts.append("Karnataka, India")

    query = ", ".join(query_parts)

    try:
        response = requests.get(
            f"{NOMINATIM_URL}/search",
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "in"},
            timeout=3
        )
        results = response.json()
        if results:
            result = results[0]
            lat = float(result["lat"])
            lon = float(result["lon"])
            # Determine quality from OSM type/class
            osm_type = result.get("type", "")
            if osm_type in ["road", "house", "building"]:
                quality = "HIGH"
            elif osm_type in ["suburb", "neighbourhood", "quarter"]:
                quality = "MEDIUM"
            else:
                quality = "LOW"
            return {"lat": lat, "lng": lon, "quality": quality}
    except Exception:
        pass

    # Fallback: pin code centroid lookup
    PIN_CENTROIDS = {
        "560058": (13.0287, 77.5201),
        "560073": (12.9952, 77.5527),
        # Add all relevant pin codes
    }
    if parsed_address.pin_code and parsed_address.pin_code in PIN_CENTROIDS:
        lat, lng = PIN_CENTROIDS[parsed_address.pin_code]
        return {"lat": lat, "lng": lng, "quality": "LOW"}

    return {"lat": None, "lng": None, "quality": "FAILED"}
```

---

## 6. Phase 4 — Entity Resolution ML Pipeline

**Target duration: Days 4–6**

### 6.1 `entity_resolution/blocker.py` — Multi-Key Blocking

```python
from collections import defaultdict
from typing import List, Tuple, Set
import h3

def generate_candidate_pairs(normalised_records: List[dict]) -> List[Tuple[str, str]]:
    """
    Input: list of normalised records, each with:
        record_id, source_system, canonical_name, soundex, metaphone,
        pin_code, pan, gstin, lat, lng, geocode_quality, nic_code_2digit
    Output: deduplicated list of (record_id_a, record_id_b) candidate pairs
    """
    pairs: Set[Tuple[str, str]] = set()

    # Index structures for each blocking key
    pan_index = defaultdict(list)
    gstin_index = defaultdict(list)
    pin_soundex_index = defaultdict(list)
    pin_metaphone_index = defaultdict(list)
    geocell_token_index = defaultdict(list)
    nic_pin_token_index = defaultdict(list)

    for rec in normalised_records:
        rid = rec["record_id"]

        # Key 1: PAN Exact
        if rec.get("pan"):
            pan_index[rec["pan"]].append(rid)

        # Key 2: GSTIN Exact
        if rec.get("gstin"):
            gstin_index[rec["gstin"]].append(rid)

        # Key 3: Pin + Soundex
        if rec.get("pin_code") and rec.get("soundex"):
            key = f"{rec['pin_code']}_{rec['soundex']}"
            pin_soundex_index[key].append(rid)

        # Key 4: Pin + Metaphone (primary metaphone key only)
        if rec.get("pin_code") and rec.get("metaphone"):
            meta_key = rec["metaphone"][0] if isinstance(rec["metaphone"], tuple) else rec["metaphone"]
            if meta_key:
                key = f"{rec['pin_code']}_{meta_key}"
                pin_metaphone_index[key].append(rid)

        # Key 5: H3 Geo-cell + First name token
        if rec.get("lat") and rec.get("lng") and rec.get("geocode_quality") in ("HIGH", "MEDIUM"):
            h3_cell = h3.geo_to_h3(rec["lat"], rec["lng"], resolution=7)
            name_tokens = rec.get("canonical_name", "").split()
            if name_tokens:
                first_token = name_tokens[0]
                key = f"{h3_cell}_{first_token}"
                geocell_token_index[key].append(rid)

        # Key 6: NIC 2-digit + Pin + First name token
        if rec.get("nic_code_2digit") and rec.get("pin_code"):
            name_tokens = rec.get("canonical_name", "").split()
            if name_tokens:
                first_token = name_tokens[0]
                key = f"{rec['nic_code_2digit']}_{rec['pin_code']}_{first_token}"
                nic_pin_token_index[key].append(rid)

    # Generate pairs from each index
    def add_pairs_from_index(index):
        for key, record_ids in index.items():
            if len(record_ids) > 1:
                for i in range(len(record_ids)):
                    for j in range(i + 1, len(record_ids)):
                        a, b = record_ids[i], record_ids[j]
                        pair = (min(a, b), max(a, b))  # Canonical ordering
                        pairs.add(pair)

    for idx in [pan_index, gstin_index, pin_soundex_index, pin_metaphone_index,
                geocell_token_index, nic_pin_token_index]:
        add_pairs_from_index(idx)

    return list(pairs)
```

### 6.2 `entity_resolution/feature_extractor.py` — All 13 Features

```python
import math
from rapidfuzz import fuzz
import jellyfish
from geopy.distance import geodesic
from src.normalisation.address_parser import PIN_ADJACENCY

def extract_features(rec_a: dict, rec_b: dict) -> dict:
    """
    Computes all 13 features for a candidate pair.
    Returns dict with keys F01–F13 and None for missing features.
    """
    features = {}

    # F01 — Name Jaro-Winkler on canonical names
    name_a = rec_a.get("canonical_name", "")
    name_b = rec_b.get("canonical_name", "")
    features["F01"] = fuzz.jaro_winkler_similarity(name_a, name_b) / 100.0 if name_a and name_b else None

    # F02 — Token Set Ratio (handles reordered tokens well)
    features["F02"] = fuzz.token_set_ratio(name_a, name_b) / 100.0 if name_a and name_b else None

    # F03 — Abbreviation match (custom logic)
    features["F03"] = _abbreviation_match_score(name_a, name_b)

    # F04 — PAN match
    features["F04"] = _identifier_match_score(rec_a.get("pan"), rec_b.get("pan"))

    # F05 — GSTIN match
    features["F05"] = _identifier_match_score(rec_a.get("gstin"), rec_b.get("gstin"))

    # F06 — Pin code match
    pin_a, pin_b = rec_a.get("pin_code"), rec_b.get("pin_code")
    if pin_a and pin_b:
        if pin_a == pin_b:
            features["F06"] = 1.0
        elif pin_b in PIN_ADJACENCY.get(pin_a, []):
            features["F06"] = 0.7
        else:
            features["F06"] = 0.0
    else:
        features["F06"] = None

    # F07 — Haversine geo-distance (metres), only if both geocoded at >=MEDIUM
    lat_a, lng_a, qual_a = rec_a.get("lat"), rec_a.get("lng"), rec_a.get("geocode_quality")
    lat_b, lng_b, qual_b = rec_b.get("lat"), rec_b.get("lng"), rec_b.get("geocode_quality")
    if (lat_a and lng_a and lat_b and lng_b and
            qual_a in ("HIGH", "MEDIUM") and qual_b in ("HIGH", "MEDIUM")):
        features["F07"] = geodesic((lat_a, lng_a), (lat_b, lng_b)).meters
    else:
        features["F07"] = None

    # F08 — Address token Jaccard similarity
    tokens_a = set(rec_a.get("address_tokens", []))
    tokens_b = set(rec_b.get("address_tokens", []))
    if tokens_a and tokens_b:
        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        features["F08"] = intersection / union if union > 0 else 0.0
    else:
        features["F08"] = None

    # F09 — Phone match (normalised to digits only)
    phone_a = ''.join(filter(str.isdigit, str(rec_a.get("phone", "") or "")))[-10:]
    phone_b = ''.join(filter(str.isdigit, str(rec_b.get("phone", "") or "")))[-10:]
    if phone_a and phone_b:
        if phone_a == phone_b:
            features["F09"] = 1.0
        elif phone_a[-7:] == phone_b[-7:]:  # Last 7 digits match (local number)
            features["F09"] = 0.5
        else:
            features["F09"] = 0.0
    else:
        features["F09"] = None

    # F10 — NIC code compatibility
    nic_a = str(rec_a.get("nic_code", "") or "")
    nic_b = str(rec_b.get("nic_code", "") or "")
    if nic_a and nic_b:
        if nic_a == nic_b:
            features["F10"] = 1.0
        elif nic_a[:2] == nic_b[:2]:
            features["F10"] = 0.7
        elif nic_a[:1] == nic_b[:1]:
            features["F10"] = 0.4
        else:
            features["F10"] = 0.0
    else:
        features["F10"] = None

    # F11 — Owner/Director name similarity
    owner_a = rec_a.get("owner_name", "")
    owner_b = rec_b.get("owner_name", "")
    if owner_a and owner_b:
        features["F11"] = fuzz.jaro_winkler_similarity(
            owner_a.upper(), owner_b.upper()
        ) / 100.0
    else:
        features["F11"] = None

    # F12 — Same-source flag (intra-department duplicate check)
    features["F12"] = 1.0 if rec_a.get("source_system") == rec_b.get("source_system") else 0.0

    # F13 — Registration date proximity (year difference, capped at 10)
    year_a = rec_a.get("registration_year")
    year_b = rec_b.get("registration_year")
    if year_a and year_b:
        features["F13"] = min(abs(int(year_a) - int(year_b)), 10)
    else:
        features["F13"] = None

    return features


def _identifier_match_score(id_a, id_b) -> float:
    """
    Returns:
     +1.0  if both present and match
     +0.5  if one or both absent (cannot determine)
      0.0  if both present and DO NOT match (no PAN mismatch hard-rule here — that's in scorer)
     -1.0  if both present and MISMATCH (strong negative signal)
    """
    has_a = bool(id_a and str(id_a).strip())
    has_b = bool(id_b and str(id_b).strip())

    if has_a and has_b:
        return 1.0 if str(id_a).strip().upper() == str(id_b).strip().upper() else -1.0
    elif has_a or has_b:
        return 0.5
    else:
        return 0.0


def _abbreviation_match_score(name_a: str, name_b: str) -> float:
    """
    Checks if one name is a valid abbreviation of the other.
    Example: 'KSIC' vs 'KARNATAKA SILK INDUSTRIES CORPORATION' → 1.0
    """
    if not name_a or not name_b:
        return 0.0

    words_a = name_a.split()
    words_b = name_b.split()

    # Check if name_a could be acronym of name_b
    if len(name_a) <= 6 and len(words_b) >= 2:
        acronym = ''.join(w[0] for w in words_b if w)
        if name_a == acronym:
            return 1.0
        # Partial acronym match
        if name_a in acronym or acronym in name_a:
            return 0.5

    # Check vice versa
    if len(name_b) <= 6 and len(words_a) >= 2:
        acronym = ''.join(w[0] for w in words_a if w)
        if name_b == acronym:
            return 1.0
        if name_b in acronym or acronym in name_b:
            return 0.5

    return 0.0
```

### 6.3 `entity_resolution/scorer.py` — LightGBM + Platt Scaling + SHAP

```python
import numpy as np
import lightgbm as lgb
import shap
import pickle
import os
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split

FEATURE_ORDER = ["F01","F02","F03","F04","F05","F06","F07","F08","F09","F10","F11","F12","F13"]

# Thresholds — tunable via admin API
THRESHOLD_AUTO_LINK = float(os.getenv("THRESHOLD_AUTO_LINK", "0.95"))
THRESHOLD_REVIEW = float(os.getenv("THRESHOLD_REVIEW", "0.75"))


def features_to_array(feature_dict: dict) -> np.ndarray:
    """Converts feature dict to numpy array in consistent order. None → NaN."""
    return np.array([
        feature_dict.get(f, np.nan) if feature_dict.get(f) is not None else np.nan
        for f in FEATURE_ORDER
    ], dtype=np.float32)


def train_model(labelled_pairs_df):
    """
    Input df columns: F01..F13, label (1=match, 0=non-match)
    Saves model to src/entity_resolution/models/
    """
    X = labelled_pairs_df[FEATURE_ORDER].values
    y = labelled_pairs_df["label"].values

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    lgbm_params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.9,
        "min_data_in_leaf": 20,
        "n_estimators": 300,
        "verbose": -1,
        "random_state": 42
    }

    base_model = lgb.LGBMClassifier(**lgbm_params)

    # Wrap with Platt Scaling for calibration
    calibrated_model = CalibratedClassifierCV(base_model, method="sigmoid", cv=5)
    calibrated_model.fit(X_train, y_train)

    # Evaluate
    val_preds = calibrated_model.predict_proba(X_val)[:, 1]
    from sklearn.metrics import roc_auc_score, precision_recall_curve
    auc = roc_auc_score(y_val, val_preds)
    print(f"Validation AUC: {auc:.4f}")

    # Save
    os.makedirs("src/entity_resolution/models", exist_ok=True)
    with open("src/entity_resolution/models/calibrated_model.pkl", "wb") as f:
        pickle.dump(calibrated_model, f)

    # Also save the underlying LGBM model for SHAP
    base_lgbm = calibrated_model.calibrated_classifiers_[0].estimator
    with open("src/entity_resolution/models/lgbm_model.pkl", "wb") as f:
        pickle.dump(base_lgbm, f)

    print(f"Model saved. Validation AUC: {auc:.4f}")
    return calibrated_model


def load_models():
    with open("src/entity_resolution/models/calibrated_model.pkl", "rb") as f:
        calibrated_model = pickle.load(f)
    with open("src/entity_resolution/models/lgbm_model.pkl", "rb") as f:
        lgbm_model = pickle.load(f)
    return calibrated_model, lgbm_model


def score_pair(feature_dict: dict, calibrated_model, lgbm_model) -> dict:
    """
    Returns confidence score, decision, and SHAP values for a candidate pair.
    """
    feature_array = features_to_array(feature_dict).reshape(1, -1)

    # Confidence score from calibrated model
    calibrated_score = float(calibrated_model.predict_proba(feature_array)[0][1])

    # PAN hard rule: if both records have PAN and they MISMATCH → force Keep Separate
    pan_hard_rule = False
    if feature_dict.get("F04") == -1.0:
        calibrated_score = 0.0
        pan_hard_rule = True

    # Routing decision
    if calibrated_score >= THRESHOLD_AUTO_LINK:
        decision = "AUTO_LINK"
    elif calibrated_score >= THRESHOLD_REVIEW:
        decision = "REVIEW"
    else:
        decision = "KEEP_SEPARATE"

    # SHAP values — use the underlying LightGBM model
    explainer = shap.TreeExplainer(lgbm_model)
    shap_values = explainer.shap_values(feature_array)

    # shap_values is a list of two arrays (for binary classification); take index 1 (positive class)
    shap_for_match = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]

    shap_dict = {
        feat: round(float(shap_for_match[i]), 4)
        for i, feat in enumerate(FEATURE_ORDER)
    }

    return {
        "calibrated_score": calibrated_score,
        "decision": decision,
        "shap_values": shap_dict,
        "pan_hard_rule_applied": pan_hard_rule
    }
```

### 6.4 `entity_resolution/ubid_assigner.py` — Union-Find + UBID Minting

```python
import uuid
import string
from collections import defaultdict
from typing import List, Tuple

BASE36_CHARS = string.digits + string.ascii_uppercase

def to_base36(num: int, length: int = 6) -> str:
    """Convert integer to base-36 string of fixed length."""
    result = []
    while num > 0:
        result.append(BASE36_CHARS[num % 36])
        num //= 36
    while len(result) < length:
        result.append('0')
    return ''.join(reversed(result))


def mint_ubid() -> str:
    """Generate a new UBID: KA-UBID-XXXXXX"""
    uid = uuid.uuid4().int % (36 ** 6)
    return f"KA-UBID-{to_base36(uid)}"


class UnionFind:
    """Disjoint Set Union for entity clustering."""
    def __init__(self):
        self.parent = {}
        self.rank = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        # Union by rank
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1

    def get_clusters(self) -> dict:
        """Returns {cluster_root: [member_ids]}"""
        clusters = defaultdict(list)
        for node in self.parent:
            clusters[self.find(node)].append(node)
        return dict(clusters)


def assign_ubids(
    auto_link_pairs: List[Tuple[str, str]],
    all_records: List[dict]
) -> dict:
    """
    Input:
        auto_link_pairs: list of (record_id_a, record_id_b) that scored >= AUTO_LINK threshold
        all_records: all normalised records with pan, gstin fields

    Returns: {record_id: ubid} mapping
    """
    uf = UnionFind()

    # Add all records as individual nodes first
    record_lookup = {r["record_id"]: r for r in all_records}
    for rec in all_records:
        uf.find(rec["record_id"])  # Initialises node

    # Union auto-linked pairs
    for rec_a_id, rec_b_id in auto_link_pairs:
        uf.union(rec_a_id, rec_b_id)

    # Get clusters
    clusters = uf.get_clusters()

    record_to_ubid = {}
    ubid_to_anchor = {}

    for cluster_root, members in clusters.items():
        ubid = mint_ubid()

        # Determine PAN/GSTIN anchor for this cluster
        pan_anchor = None
        gstin_anchors = []
        for member_id in members:
            rec = record_lookup.get(member_id, {})
            if rec.get("pan") and not pan_anchor:
                pan_anchor = rec["pan"]
            if rec.get("gstin") and rec["gstin"] not in gstin_anchors:
                gstin_anchors.append(rec["gstin"])

        ubid_to_anchor[ubid] = {
            "pan_anchor": pan_anchor,
            "gstin_anchors": gstin_anchors,
            "anchor_status": "ANCHORED" if pan_anchor else "UNANCHORED",
            "member_count": len(members)
        }

        for member_id in members:
            record_to_ubid[member_id] = ubid

    return record_to_ubid, ubid_to_anchor
```

---

## 7. Phase 5 — Activity Intelligence Engine

**Target duration: Days 6–7**

### 7.1 `activity_engine/signal_config.py`

```python
"""
Central configuration for all signal types.
Modify weights and half-lives here to tune the activity classifier.
"""

import math

SIGNAL_WEIGHTS = {
    "electricity_consumption_high":  +0.90,
    "water_consumption_high":        +0.70,
    "licence_renewal":               +0.80,
    "inspection_visit":              +0.70,
    "compliance_filing":             +0.75,
    "administrative_update":         +0.40,
    "electricity_consumption_low":   -0.50,
    "renewal_overdue_180d":          -0.40,
    "closure_declaration":           -1.00,   # Permanent — no decay
    "licence_cancellation":          -0.90,   # Permanent — no decay
}

SIGNAL_HALF_LIVES = {
    "electricity_consumption_high":  45,
    "water_consumption_high":        45,
    "licence_renewal":               365,
    "inspection_visit":              180,
    "compliance_filing":             270,
    "administrative_update":         90,
    "electricity_consumption_low":   30,
    "renewal_overdue_180d":          180,
    "closure_declaration":           None,   # None = permanent, never decays
    "licence_cancellation":          None,
}

PERMANENT_SIGNALS = {"closure_declaration", "licence_cancellation"}

# Activity score thresholds
THRESHOLD_ACTIVE = +0.4
THRESHOLD_DORMANT_LOW = -0.2

# NIC codes with seasonal patterns — adjust active/dormant boundary
SEASONAL_NIC_CODES = {
    "24": {"active_months": [10,11,12,1,2,3]},  # Fireworks / basic chemicals
    "10": {"active_months": [10,11,12,9]},        # Food (festive season peak)
    "14": {"active_months": [6,7,8,9,10,11]},     # Apparel (export season)
}

def compute_decay(half_life_days: int, days_since: int) -> float:
    """Returns e^(-λ * days) where λ = ln(2) / half_life."""
    if half_life_days is None:
        return 1.0  # Permanent signal — no decay
    lambda_val = math.log(2) / half_life_days
    return math.exp(-lambda_val * days_since)
```

### 7.2 `activity_engine/signal_scorer.py`

```python
from datetime import datetime, timezone
from src.activity_engine.signal_config import (
    SIGNAL_WEIGHTS, SIGNAL_HALF_LIVES, PERMANENT_SIGNALS,
    compute_decay, THRESHOLD_ACTIVE, THRESHOLD_DORMANT_LOW
)

LOOKBACK_DAYS = 365

def compute_activity_score(ubid: str, events: list, reference_date: datetime = None) -> dict:
    """
    events: list of dicts {event_type, event_timestamp, source_system, payload}
    Returns: {score, status, evidence}
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)

    # Check for hard permanent signals first
    for event in events:
        if event["event_type"] in PERMANENT_SIGNALS:
            return {
                "raw_score": -1.0,
                "activity_status": "CLOSED_CONFIRMED",
                "evidence": [{
                    "event_type": event["event_type"],
                    "event_timestamp": str(event["event_timestamp"]),
                    "source_system": event["source_system"],
                    "weight": SIGNAL_WEIGHTS[event["event_type"]],
                    "decay": 1.0,
                    "contribution": SIGNAL_WEIGHTS[event["event_type"]],
                    "note": "PERMANENT_SIGNAL"
                }]
            }

    # Filter to lookback window
    cutoff = reference_date.timestamp() - (LOOKBACK_DAYS * 86400)
    recent_events = [
        e for e in events
        if datetime.fromisoformat(str(e["event_timestamp"])).timestamp() > cutoff
    ]

    total_score = 0.0
    evidence = []

    for event in recent_events:
        event_type = event["event_type"]
        if event_type not in SIGNAL_WEIGHTS:
            continue

        weight = SIGNAL_WEIGHTS[event_type]
        half_life = SIGNAL_HALF_LIVES.get(event_type)

        event_ts = datetime.fromisoformat(str(event["event_timestamp"]))
        days_since = (reference_date - event_ts.replace(tzinfo=timezone.utc)).days
        days_since = max(0, days_since)

        decay = compute_decay(half_life, days_since)
        contribution = weight * decay
        total_score += contribution

        evidence.append({
            "event_type": event_type,
            "event_timestamp": str(event["event_timestamp"]),
            "source_system": event.get("source_system", "unknown"),
            "weight": weight,
            "decay": round(decay, 4),
            "contribution": round(contribution, 4),
            "days_since": days_since
        })

    # Normalise to [-1, +1] using sigmoid-like transform
    import math
    normalised_score = 2 / (1 + math.exp(-total_score)) - 1

    # Classify
    if normalised_score > THRESHOLD_ACTIVE:
        status = "ACTIVE"
    elif normalised_score >= THRESHOLD_DORMANT_LOW:
        status = "DORMANT"
    else:
        status = "CLOSED_SUSPECTED"

    # Sort evidence by |contribution| descending for display
    evidence.sort(key=lambda x: abs(x["contribution"]), reverse=True)

    return {
        "raw_score": round(normalised_score, 4),
        "activity_status": status,
        "evidence": evidence,
        "event_count": len(recent_events),
        "lookback_days": LOOKBACK_DAYS,
        "computed_at": reference_date.isoformat()
    }
```

---

## 8. Phase 6 — FastAPI Backend

**Target duration: Days 7–9**

### 8.1 `api/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import ubid, activity, review, admin
import os

app = FastAPI(
    title="UBID Platform API",
    description="Unified Business Identifier & Active Business Intelligence Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ubid.router, prefix="/api/ubid", tags=["UBID"])
app.include_router(activity.router, prefix="/api/activity", tags=["Activity"])
app.include_router(review.router, prefix="/api/review", tags=["Review"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ubid-platform"}
```

### 8.2 `api/routers/ubid.py` — Complete Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.database.connection import get_db
from src.database.models import UBIDEntity, UBIDSourceLink, UBIDLinkEvidence, ActivityScore
from src.api.schemas.ubid_schemas import UBIDDetailResponse, UBIDLookupResult
from typing import Optional

router = APIRouter()

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
        entity = db.query(UBIDEntity).filter(UBIDEntity.pan_anchor == pan.upper()).first()

    elif gstin:
        # Search in gstin_anchors array
        entity = db.query(UBIDEntity).filter(
            UBIDEntity.gstin_anchors.contains([gstin.upper()])
        ).first()

    elif name and pincode:
        # Fuzzy name search — for demo, do a simple ilike; in production use pg_trgm
        links = db.query(UBIDSourceLink).all()
        # Simple approach: check all records in source tables for name match
        # In production: use a pre-built search index
        raise HTTPException(status_code=501, detail="Name search via full-text index — use /search endpoint")

    if not entity:
        raise HTTPException(status_code=404, detail="No UBID found for the given identifiers")

    return _build_ubid_detail(entity, db)


@router.get("/{ubid}")
def get_ubid_detail(ubid: str, db: Session = Depends(get_db)):
    entity = db.query(UBIDEntity).filter(UBIDEntity.ubid == ubid).first()
    if not entity:
        raise HTTPException(status_code=404, detail=f"UBID {ubid} not found")
    return _build_ubid_detail(entity, db)


def _build_ubid_detail(entity: UBIDEntity, db: Session) -> dict:
    """Build the full UBID detail response with all linked records and evidence."""
    # Get all source links
    links = db.query(UBIDSourceLink).filter(
        UBIDSourceLink.ubid == entity.ubid,
        UBIDSourceLink.is_active == True
    ).all()

    # Get current activity score
    activity = db.query(ActivityScore).filter(
        ActivityScore.ubid == entity.ubid,
        ActivityScore.is_current == True
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

    return {
        "ubid": entity.ubid,
        "pan_anchor": entity.pan_anchor,
        "gstin_anchors": entity.gstin_anchors,
        "anchor_status": entity.anchor_status,
        "activity_status": activity.activity_status if activity else "UNKNOWN",
        "activity_score": activity.raw_score if activity else None,
        "source_records": source_records_with_evidence,
        "source_record_count": len(source_records_with_evidence),
        "created_at": str(entity.created_at)
    }
```

### 8.3 `api/routers/activity.py` — The Demo Query

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from src.database.connection import get_db
from src.database.models import ActivityScore, UBIDEntity, UBIDActivityEvent, UBIDSourceLink
from typing import Optional, List
from datetime import datetime, timedelta, timezone

router = APIRouter()

@router.get("/query")
def query_businesses(
    status: Optional[str] = Query(None, description="ACTIVE / DORMANT / CLOSED_SUSPECTED / CLOSED_CONFIRMED"),
    pincode: Optional[str] = Query(None),
    sector_nic: Optional[str] = Query(None, description="2-digit NIC code"),
    no_inspection_days: Optional[int] = Query(None, description="No inspection event in last N days"),
    db: Session = Depends(get_db)
):
    """
    THE DEMO QUERY:
    'Show all Active factories in pin code 560058 with no inspection in the last 18 months'
    → /api/activity/query?status=ACTIVE&pincode=560058&no_inspection_days=540
    """
    # Base query on activity scores
    q = db.query(ActivityScore).filter(ActivityScore.is_current == True)

    if status:
        q = q.filter(ActivityScore.activity_status == status.upper())

    results = q.all()

    # Filter by pin code (need to join through source links to source records)
    # For prototype: store pin code on UBID entity directly for fast filtering
    if pincode:
        ubids_in_pin = _get_ubids_in_pincode(pincode, db)
        results = [r for r in results if r.ubid in ubids_in_pin]

    # Filter: no inspection in last N days
    if no_inspection_days:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=no_inspection_days)
        results = [
            r for r in results
            if not _has_recent_inspection(r.ubid, cutoff_date, db)
        ]

    return {
        "query": {
            "status": status,
            "pincode": pincode,
            "sector_nic": sector_nic,
            "no_inspection_days": no_inspection_days
        },
        "result_count": len(results),
        "results": [
            {
                "ubid": r.ubid,
                "activity_status": r.activity_status,
                "activity_score": r.raw_score,
                "computed_at": str(r.computed_at),
                "evidence_summary": _summarise_evidence(r.evidence_snapshot)
            }
            for r in results[:200]  # Cap at 200 for demo
        ]
    }


def _has_recent_inspection(ubid: str, cutoff: datetime, db: Session) -> bool:
    inspection_types = ["inspection_visit", "safety_inspection", "environmental_inspection"]
    recent = db.query(UBIDActivityEvent).filter(
        UBIDActivityEvent.ubid == ubid,
        UBIDActivityEvent.event_type.in_(inspection_types),
        UBIDActivityEvent.event_timestamp >= cutoff
    ).first()
    return recent is not None


def _get_ubids_in_pincode(pincode: str, db: Session) -> set:
    """Returns set of UBIDs that have at least one source record in the given pin code."""
    # This requires a pin_code column on ubid_source_links or a denormalised lookup table
    # For prototype: query source tables directly and join
    # Simplified: use a pre-computed lookup stored in ubid_entities
    entities = db.query(UBIDEntity.ubid).filter(
        UBIDEntity.ubid.in_(
            db.query(UBIDSourceLink.ubid).filter(
                UBIDSourceLink.source_record_id.like(f"%{pincode}%")
            )
        )
    ).all()
    return {e.ubid for e in entities}


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

    return {
        "ubid": ubid,
        "event_count": len(events),
        "events": [
            {
                "event_type": e.event_type,
                "source_system": e.source_system,
                "event_timestamp": str(e.event_timestamp),
                "signal_weight": e.signal_weight,
                "payload": e.payload
            }
            for e in events
        ]
    }
```

### 8.4 `api/routers/review.py` — Review Queue Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from src.database.connection import get_db
from src.database.models import ReviewTask, UBIDLinkEvidence, UBIDSourceLink, UBIDEntity
from typing import Optional
from datetime import datetime, timezone
import uuid

router = APIRouter()

@router.get("/queue")
def get_review_queue(
    status: str = "PENDING",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    offset = (page - 1) * page_size
    tasks = db.query(ReviewTask).filter(
        ReviewTask.status == status
    ).order_by(ReviewTask.priority, ReviewTask.calibrated_score.desc()).offset(offset).limit(page_size).all()

    total = db.query(ReviewTask).filter(ReviewTask.status == status).count()

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
                "priority": t.priority,
                "created_at": str(t.created_at)
            }
            for t in tasks
        ]
    }


@router.get("/task/{task_id}")
def get_review_task_detail(task_id: str, db: Session = Depends(get_db)):
    """
    Returns the full review card for a task:
    Both records (raw + canonical), all feature scores, SHAP values.
    """
    task = db.query(ReviewTask).filter(ReviewTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    evidence = db.query(UBIDLinkEvidence).filter(
        UBIDLinkEvidence.evidence_id == task.evidence_id
    ).first()

    # Fetch raw + normalised fields for both records
    # (In prototype: query source tables using source_system + source_record_id)
    record_a_data = _fetch_source_record(task.pair_record_a, db)
    record_b_data = _fetch_source_record(task.pair_record_b, db)

    return {
        "task_id": task_id,
        "status": task.status,
        "calibrated_score": task.calibrated_score,
        "record_a": record_a_data,
        "record_b": record_b_data,
        "feature_scores": evidence.feature_vector if evidence else {},
        "shap_values": evidence.shap_values if evidence else {},
        "suggested_decision": "CONFIRM_MATCH" if task.calibrated_score >= 0.85 else "REVIEW",
        "historical_decisions": []  # Populated from past decisions on overlapping pairs
    }


@router.post("/task/{task_id}/decision")
def submit_decision(
    task_id: str,
    decision: str = Body(..., embed=True),
    reason: Optional[str] = Body(None, embed=True),
    reviewer_id: str = Body("demo_reviewer", embed=True),
    db: Session = Depends(get_db)
):
    """
    decision must be one of:
    CONFIRM_MATCH / CONFIRM_NON_MATCH / CONFIRM_PARTIAL / REQUEST_MORE_INFO / DEFER
    """
    valid_decisions = {
        "CONFIRM_MATCH", "CONFIRM_NON_MATCH", "CONFIRM_PARTIAL",
        "REQUEST_MORE_INFO", "DEFER"
    }
    if decision not in valid_decisions:
        raise HTTPException(status_code=400, detail=f"Invalid decision. Must be one of: {valid_decisions}")

    task = db.query(ReviewTask).filter(ReviewTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.decision = decision
    task.decision_reason = reason
    task.decided_by = reviewer_id
    task.decided_at = datetime.now(timezone.utc)
    task.status = "DECIDED" if decision not in ("DEFER",) else "DEFERRED"

    # If CONFIRM_MATCH: commit the link to UBID registry
    if decision == "CONFIRM_MATCH":
        _commit_manual_link(task, reviewer_id, db)
    elif decision == "CONFIRM_NON_MATCH":
        _blacklist_pair(task, db)

    db.commit()

    return {
        "task_id": task_id,
        "decision": decision,
        "status": task.status,
        "message": f"Decision recorded. UBID link {'committed' if decision == 'CONFIRM_MATCH' else 'updated'}."
    }


@router.get("/stats")
def get_review_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func as sqlfunc
    total = db.query(ReviewTask).count()
    pending = db.query(ReviewTask).filter(ReviewTask.status == "PENDING").count()
    decided = db.query(ReviewTask).filter(ReviewTask.status == "DECIDED").count()
    auto_links = db.query(UBIDSourceLink).filter(UBIDSourceLink.link_type == "auto").count()
    manual_links = db.query(UBIDSourceLink).filter(UBIDSourceLink.link_type == "manual").count()

    auto_link_rate = auto_links / (auto_links + manual_links) * 100 if (auto_links + manual_links) > 0 else 0

    return {
        "queue_depth": pending,
        "total_tasks": total,
        "decided": decided,
        "auto_link_count": auto_links,
        "manual_link_count": manual_links,
        "auto_link_rate_pct": round(auto_link_rate, 1)
    }


def _fetch_source_record(source_ref: str, db: Session) -> dict:
    """source_ref format: 'shop_establishment:SE/BNG/2008/047823'"""
    try:
        source_system, record_id = source_ref.split(":", 1)
    except ValueError:
        return {"error": "Invalid source reference format"}

    # Query the appropriate dept table
    table_map = {
        "shop_establishment": "dept_shop_establishment",
        "factories": "dept_factories",
        "labour": "dept_labour",
        "kspcb": "dept_kspcb"
    }
    # For prototype: use raw SQL or a generic lookup function
    return {"source_system": source_system, "record_id": record_id, "note": "fetch from source table"}


def _commit_manual_link(task: ReviewTask, reviewer_id: str, db: Session):
    """Commit a manually confirmed link to the UBID registry."""
    # Create source link records for both parties
    # Simplified: look up existing UBIDs and merge or create new
    link_id = str(uuid.uuid4())
    link = UBIDSourceLink(
        link_id=link_id,
        ubid="TBD",  # Determine from existing UBIDs or create new
        source_system=task.pair_record_a.split(":")[0],
        source_record_id=task.pair_record_a.split(":")[1],
        confidence=task.calibrated_score,
        link_type="manual",
        linked_by=reviewer_id
    )
    db.add(link)


def _blacklist_pair(task: ReviewTask, db: Session):
    """Mark this pair as confirmed non-match — never re-propose."""
    # Store in a blacklist table or as a flag on the evidence record
    pass
```

---

## 9. Phase 7 — React Frontend

**Target duration: Days 9–12**

### 9.1 `frontend/src/api/client.js`

```javascript
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' }
});

// Response interceptor for error handling
client.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const ubidAPI = {
  lookup: (params) => client.get('/api/ubid/lookup', { params }),
  getDetail: (ubid) => client.get(`/api/ubid/${ubid}`),
};

export const activityAPI = {
  query: (params) => client.get('/api/activity/query', { params }),
  getStatus: (ubid) => client.get(`/api/activity/${ubid}/status`),
  getTimeline: (ubid) => client.get(`/api/activity/${ubid}/timeline`),
};

export const reviewAPI = {
  getQueue: (params) => client.get('/api/review/queue', { params }),
  getTask: (taskId) => client.get(`/api/review/task/${taskId}`),
  submitDecision: (taskId, data) => client.post(`/api/review/task/${taskId}/decision`, data),
  getStats: () => client.get('/api/review/stats'),
};

export const adminAPI = {
  getAuditLog: (params) => client.get('/api/admin/audit-log', { params }),
  getModelStats: () => client.get('/api/admin/model-stats'),
  updateThresholds: (data) => client.post('/api/admin/thresholds', data),
};
```

### 9.2 `App.jsx` — Routing Structure

```jsx
import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import { SearchOutlined, BarChartOutlined, AuditOutlined, DashboardOutlined } from '@ant-design/icons';
import LookupPage from './pages/LookupPage';
import ActivityPage from './pages/ActivityPage';
import ReviewPage from './pages/ReviewPage';
import DashboardPage from './pages/DashboardPage';

const { Header, Content, Sider } = Layout;

export default function App() {
  return (
    <BrowserRouter>
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ background: '#003580', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
          <div style={{ color: 'white', fontSize: 18, fontWeight: 700 }}>
            🏛️ UBID Platform — Karnataka Commerce & Industry
          </div>
        </Header>
        <Layout>
          <Sider width={220} style={{ background: '#f0f2f5' }}>
            <Menu mode="inline" style={{ height: '100%', borderRight: 0 }} defaultSelectedKeys={['lookup']}>
              <Menu.Item key="lookup" icon={<SearchOutlined />}>
                <Link to="/">UBID Lookup</Link>
              </Menu.Item>
              <Menu.Item key="activity" icon={<BarChartOutlined />}>
                <Link to="/activity">Activity Query</Link>
              </Menu.Item>
              <Menu.Item key="review" icon={<AuditOutlined />}>
                <Link to="/review">Review Queue</Link>
              </Menu.Item>
              <Menu.Item key="dashboard" icon={<DashboardOutlined />}>
                <Link to="/dashboard">Analytics</Link>
              </Menu.Item>
            </Menu>
          </Sider>
          <Layout style={{ padding: '24px' }}>
            <Content style={{ background: 'white', padding: 24, borderRadius: 8 }}>
              <Routes>
                <Route path="/" element={<LookupPage />} />
                <Route path="/activity" element={<ActivityPage />} />
                <Route path="/review" element={<ReviewPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
              </Routes>
            </Content>
          </Layout>
        </Layout>
      </Layout>
    </BrowserRouter>
  );
}
```

### 9.3 `pages/ReviewPage.jsx` — Reviewer Queue with Side-by-Side Card

```jsx
import React, { useState, useEffect } from 'react';
import { Table, Card, Row, Col, Tag, Button, Space, Typography, Progress, Divider } from 'antd';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer } from 'recharts';
import { reviewAPI } from '../api/client';

const { Title, Text } = Typography;

const DECISION_COLORS = {
  CONFIRM_MATCH: '#52c41a',
  CONFIRM_NON_MATCH: '#f5222d',
  CONFIRM_PARTIAL: '#faad14',
  REQUEST_MORE_INFO: '#1890ff',
  DEFER: '#d9d9d9',
};

const FEATURE_LABELS = {
  F01: 'Name Jaro-Winkler', F02: 'Token Set Ratio', F03: 'Abbreviation Match',
  F04: 'PAN Match', F05: 'GSTIN Match', F06: 'Pin Code Match',
  F07: 'Geo Distance', F08: 'Address Overlap', F09: 'Phone Match',
  F10: 'Industry Code', F11: 'Owner Name', F12: 'Same Source', F13: 'Reg Date'
};

export default function ReviewPage() {
  const [queue, setQueue] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [taskDetail, setTaskDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({});

  useEffect(() => {
    loadQueue();
    loadStats();
  }, []);

  const loadQueue = async () => {
    const data = await reviewAPI.getQueue({ status: 'PENDING', page: 1, page_size: 50 });
    setQueue(data.tasks || []);
  };

  const loadStats = async () => {
    const data = await reviewAPI.getStats();
    setStats(data);
  };

  const loadTaskDetail = async (taskId) => {
    setLoading(true);
    const data = await reviewAPI.getTask(taskId);
    setTaskDetail(data);
    setSelectedTask(taskId);
    setLoading(false);
  };

  const submitDecision = async (decision) => {
    await reviewAPI.submitDecision(selectedTask, { decision, reviewer_id: 'demo_reviewer' });
    setTaskDetail(null);
    setSelectedTask(null);
    loadQueue();
    loadStats();
  };

  // Build SHAP chart data
  const shapeChartData = taskDetail ? Object.entries(taskDetail.shap_values || {}).map(([feat, val]) => ({
    name: FEATURE_LABELS[feat] || feat,
    value: val,
    fill: val >= 0 ? '#52c41a' : '#f5222d'
  })).sort((a, b) => Math.abs(b.value) - Math.abs(a.value)).slice(0, 8) : [];

  const queueColumns = [
    { title: 'Confidence', dataIndex: 'calibrated_score', render: v => (
      <Tag color={v >= 0.90 ? 'orange' : v >= 0.80 ? 'gold' : 'default'}>{(v * 100).toFixed(0)}%</Tag>
    )},
    { title: 'Record A', dataIndex: 'pair_record_a', ellipsis: true },
    { title: 'Record B', dataIndex: 'pair_record_b', ellipsis: true },
    { title: 'Action', render: (_, row) => (
      <Button type="link" onClick={() => loadTaskDetail(row.task_id)}>Review →</Button>
    )}
  ];

  return (
    <div>
      {/* Stats bar */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {[
          { label: 'Queue Depth', value: stats.queue_depth },
          { label: 'Auto-Link Rate', value: `${stats.auto_link_rate_pct}%` },
          { label: 'Decided', value: stats.decided },
        ].map(s => (
          <Col span={8} key={s.label}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#003580' }}>{s.value}</div>
              <div style={{ color: '#888' }}>{s.label}</div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={16}>
        {/* Queue list */}
        <Col span={8}>
          <Title level={5}>Review Queue</Title>
          <Table
            dataSource={queue}
            columns={queueColumns}
            rowKey="task_id"
            size="small"
            pagination={{ pageSize: 15 }}
            rowClassName={row => row.task_id === selectedTask ? 'ant-table-row-selected' : ''}
          />
        </Col>

        {/* Review card */}
        <Col span={16}>
          {taskDetail ? (
            <div>
              <Title level={5}>
                Review Task — Confidence:{' '}
                <Tag color="orange">{(taskDetail.calibrated_score * 100).toFixed(0)}%</Tag>
              </Title>

              {/* Side-by-side record comparison */}
              <Row gutter={16}>
                <Col span={11}>
                  <Card title="Record A" size="small" headStyle={{ background: '#e6f7ff' }}>
                    <RecordFields record={taskDetail.record_a} />
                  </Card>
                </Col>
                <Col span={2} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <FeatureScoreBars features={taskDetail.feature_scores} />
                </Col>
                <Col span={11}>
                  <Card title="Record B" size="small" headStyle={{ background: '#f6ffed' }}>
                    <RecordFields record={taskDetail.record_b} />
                  </Card>
                </Col>
              </Row>

              {/* SHAP waterfall */}
              <Card title="Why this score? (SHAP Feature Contributions)" style={{ marginTop: 16 }} size="small">
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={shapeChartData} layout="vertical" margin={{ left: 120 }}>
                    <XAxis type="number" domain={[-0.5, 0.5]} tickFormatter={v => v.toFixed(2)} />
                    <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={v => v.toFixed(4)} />
                    <Bar dataKey="value">
                      {shapeChartData.map((entry, index) => (
                        <Cell key={index} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              {/* Decision buttons */}
              <Divider />
              <Space wrap>
                {Object.keys(DECISION_COLORS).map(d => (
                  <Button
                    key={d}
                    style={{ background: DECISION_COLORS[d], color: d === 'DEFER' ? '#333' : 'white', border: 'none' }}
                    onClick={() => submitDecision(d)}
                  >
                    {d.replace(/_/g, ' ')}
                  </Button>
                ))}
              </Space>
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: '#888', marginTop: 80 }}>
              ← Select a task from the queue to review
            </div>
          )}
        </Col>
      </Row>
    </div>
  );
}

function RecordFields({ record }) {
  if (!record) return <Text type="secondary">Loading...</Text>;
  return (
    <div style={{ fontSize: 12 }}>
      {Object.entries(record).filter(([k]) => k !== 'error').map(([k, v]) => (
        <div key={k} style={{ marginBottom: 4 }}>
          <Text strong style={{ textTransform: 'capitalize' }}>{k}: </Text>
          <Text>{String(v || '—')}</Text>
        </div>
      ))}
    </div>
  );
}

function FeatureScoreBars({ features }) {
  return (
    <div style={{ fontSize: 10 }}>
      {Object.entries(features || {}).slice(0, 8).map(([feat, val]) => (
        <div key={feat} style={{ marginBottom: 2 }}>
          <Progress
            percent={Math.min(100, Math.abs(Number(val)) * 100)}
            size="small"
            strokeColor={Number(val) >= 0 ? '#52c41a' : '#f5222d'}
            showInfo={false}
            style={{ width: 60 }}
          />
          <span style={{ marginLeft: 4 }}>{feat}</span>
        </div>
      ))}
    </div>
  );
}
```

### 9.4 `pages/ActivityPage.jsx` — The Demo Query Page

```jsx
import React, { useState } from 'react';
import { Form, Select, Input, Button, Table, Tag, Card, Modal, Descriptions, Timeline } from 'antd';
import { activityAPI } from '../api/client';

const STATUS_COLORS = {
  ACTIVE: 'green', DORMANT: 'orange',
  CLOSED_SUSPECTED: 'red', CLOSED_CONFIRMED: 'volcano'
};
const STATUS_ICONS = { ACTIVE: '🟢', DORMANT: '🟡', CLOSED_SUSPECTED: '🔴', CLOSED_CONFIRMED: '⛔' };

export default function ActivityPage() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedUBID, setSelectedUBID] = useState(null);
  const [timeline, setTimeline] = useState([]);

  const onQuery = async (values) => {
    setLoading(true);
    const params = {};
    if (values.status) params.status = values.status;
    if (values.pincode) params.pincode = values.pincode;
    if (values.no_inspection_days) params.no_inspection_days = values.no_inspection_days;
    const data = await activityAPI.query(params);
    setResults(data);
    setLoading(false);
  };

  const openTimeline = async (ubid) => {
    const data = await activityAPI.getTimeline(ubid);
    setTimeline(data.events || []);
    setSelectedUBID(ubid);
  };

  const columns = [
    { title: 'UBID', dataIndex: 'ubid', render: v => (
      <Button type="link" onClick={() => openTimeline(v)}>{v}</Button>
    )},
    { title: 'Status', dataIndex: 'activity_status', render: v => (
      <Tag color={STATUS_COLORS[v]}>{STATUS_ICONS[v]} {v}</Tag>
    )},
    { title: 'Score', dataIndex: 'activity_score', render: v => v?.toFixed(3) },
    { title: 'Top Signal', render: (_, row) => (
      row.evidence_summary?.top_positive_signals?.[0]?.event_type || '—'
    )},
  ];

  return (
    <div>
      <Card title="🔍 Business Activity Query" style={{ marginBottom: 16 }}>
        <Form layout="inline" onFinish={onQuery}>
          <Form.Item name="status" label="Status">
            <Select placeholder="Any" style={{ width: 180 }} allowClear>
              <Select.Option value="ACTIVE">🟢 Active</Select.Option>
              <Select.Option value="DORMANT">🟡 Dormant</Select.Option>
              <Select.Option value="CLOSED_SUSPECTED">🔴 Closed (Suspected)</Select.Option>
              <Select.Option value="CLOSED_CONFIRMED">⛔ Closed (Confirmed)</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="pincode" label="Pin Code">
            <Input placeholder="560058" style={{ width: 100 }} />
          </Form.Item>
          <Form.Item name="no_inspection_days" label="No Inspection for (days)">
            <Input placeholder="540" type="number" style={{ width: 100 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>Run Query</Button>
          </Form.Item>
        </Form>
      </Card>

      {results && (
        <div>
          <div style={{ marginBottom: 8, color: '#555' }}>
            Found <strong>{results.result_count}</strong> businesses matching query
          </div>
          <Table dataSource={results.results} columns={columns} rowKey="ubid" size="small" />
        </div>
      )}

      <Modal
        title={`Activity Timeline — ${selectedUBID}`}
        open={!!selectedUBID}
        onCancel={() => setSelectedUBID(null)}
        footer={null}
        width={700}
      >
        <Timeline>
          {timeline.map((evt, i) => (
            <Timeline.Item key={i} color={evt.signal_weight > 0 ? 'green' : 'red'}>
              <strong>{evt.event_type}</strong> via {evt.source_system}
              <br />
              <span style={{ color: '#888', fontSize: 12 }}>
                {new Date(evt.event_timestamp).toLocaleDateString('en-IN')}
                {' | '}Weight: {evt.signal_weight > 0 ? '+' : ''}{evt.signal_weight}
              </span>
            </Timeline.Item>
          ))}
        </Timeline>
      </Modal>
    </div>
  );
}
```

---

## 10. Phase 8 — Docker Compose & Integration

**Target duration: Day 12–13**

### 10.1 `docker-compose.yml` — Complete Stack

```yaml
version: '3.9'

services:

  postgres:
    image: postgres:15-alpine
    container_name: ubid_postgres
    environment:
      POSTGRES_DB: ubid_platform
      POSTGRES_USER: ubid_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-localdevpass}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ubid_user -d ubid_platform"]
      interval: 10s
      timeout: 5s
      retries: 5

  nominatim:
    image: mediagis/nominatim:4.3
    container_name: ubid_nominatim
    ports:
      - "8080:8080"
    environment:
      PBF_URL: https://download.geofabrik.io/asia/india/karnataka-latest.osm.pbf
      REPLICATION_URL: https://download.geofabrik.io/asia/india/karnataka-updates/
      NOMINATIM_PASSWORD: nominatim_local
    volumes:
      - nominatim_data:/var/lib/postgresql/14/main
    # NOTE: First startup takes 30-60 min to import Karnataka OSM data
    # For demo: use the pin centroid fallback in geocoder.py instead of Nominatim

  mlflow:
    image: python:3.11-slim
    container_name: ubid_mlflow
    command: >
      bash -c "pip install mlflow && mlflow server
      --backend-store-uri sqlite:///mlflow.db
      --default-artifact-root /mlflow/artifacts
      --host 0.0.0.0 --port 5000"
    ports:
      - "5000:5000"
    volumes:
      - mlflow_data:/mlflow

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: ubid_backend
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=ubid_platform
      - POSTGRES_USER=ubid_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-localdevpass}
      - NOMINATIM_URL=http://nominatim:8080
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - SCRAMBLER_SECRET_KEY=${SCRAMBLER_SECRET_KEY:-dev_secret}
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./src:/app/src
      - ./data:/app/data

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
    container_name: ubid_frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    depends_on:
      - backend

volumes:
  postgres_data:
  nominatim_data:
  mlflow_data:
```

### 10.2 `Dockerfile.backend`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN alembic upgrade head || true
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 10.3 `Dockerfile.frontend`

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
```

---

## 11. Phase 9 — Demo Preparation & Pre-computation

**Target duration: Day 13 (demo rehearsal day)**

### 11.1 `scripts/run_pipeline.py` — One-Shot Pre-computation

Run this script **once before the demo** to populate the UBID registry from scratch. Never run live ML during the demo presentation.

```python
"""
Full pipeline execution script.
Run: python scripts/run_pipeline.py
Expected runtime on a 5,000-entity dataset: ~10-15 minutes
"""
import sys
sys.path.insert(0, '.')

from tqdm import tqdm
from src.database.connection import SessionLocal
from src.normalisation.standardiser import standardise_record
from src.entity_resolution.blocker import generate_candidate_pairs
from src.entity_resolution.feature_extractor import extract_features
from src.entity_resolution.scorer import load_models, score_pair
from src.entity_resolution.ubid_assigner import assign_ubids
from src.activity_engine.event_router import route_all_events
from src.activity_engine.signal_scorer import compute_activity_score
from src.database.models import *
import uuid

def run_full_pipeline():
    db = SessionLocal()
    calibrated_model, lgbm_model = load_models()

    print("📂 Step 1: Loading source records from all 4 departments...")
    all_raw_records = load_all_source_records(db)
    print(f"   Loaded {len(all_raw_records)} raw records")

    print("🔧 Step 2: Normalising all records...")
    normalised = []
    for rec in tqdm(all_raw_records):
        normalised.append(standardise_record(rec))
    print(f"   Normalised {len(normalised)} records")

    print("🔗 Step 3: Generating candidate pairs via blocking...")
    pairs = generate_candidate_pairs(normalised)
    print(f"   Generated {len(pairs):,} candidate pairs")

    print("📐 Step 4: Extracting features for all pairs...")
    record_lookup = {r["record_id"]: r for r in normalised}
    scored_pairs = {"auto_link": [], "review": [], "keep_separate": []}
    all_evidence = []

    for rec_a_id, rec_b_id in tqdm(pairs):
        rec_a = record_lookup.get(rec_a_id)
        rec_b = record_lookup.get(rec_b_id)
        if not rec_a or not rec_b:
            continue
        features = extract_features(rec_a, rec_b)
        result = score_pair(features, calibrated_model, lgbm_model)
        all_evidence.append((rec_a_id, rec_b_id, features, result))
        scored_pairs[result["decision"].lower().replace("-", "_")].append((rec_a_id, rec_b_id))

    print(f"   Auto-link: {len(scored_pairs['auto_link'])} | "
          f"Review: {len(scored_pairs['review'])} | "
          f"Keep Separate: {len(scored_pairs['keep_separate'])}")

    print("🏷️  Step 5: Assigning UBIDs...")
    record_to_ubid, ubid_to_anchor = assign_ubids(scored_pairs['auto_link'], normalised)

    print("💾 Step 6: Persisting UBID registry...")
    persist_ubid_registry(record_to_ubid, ubid_to_anchor, all_evidence, db)

    print("📋 Step 7: Creating review tasks for ambiguous pairs...")
    create_review_tasks(scored_pairs['review'], all_evidence, db)

    print("📡 Step 8: Routing activity events to UBIDs...")
    route_all_events(record_to_ubid, db)

    print("📊 Step 9: Computing activity scores for all UBIDs...")
    compute_all_activity_scores(list(set(record_to_ubid.values())), db)

    db.commit()
    print("\n✅ Pipeline complete!")
    print(f"   UBIDs created: {len(ubid_to_anchor)}")
    print(f"   Review queue items: {len(scored_pairs['review'])}")

if __name__ == "__main__":
    run_full_pipeline()
```

### 11.2 `scripts/reset_demo.py`

```python
"""
Resets the demo to a clean state.
Deletes all UBID registry tables but leaves source data intact.
Run before each demo to start fresh.
"""
from src.database.connection import engine
from src.database.models import *

def reset():
    print("⚠️  Resetting UBID registry to clean state...")
    with engine.connect() as conn:
        conn.execute("TRUNCATE ubid_entities, ubid_source_links, ubid_link_evidence, "
                     "review_tasks, ubid_activity_events, activity_scores, "
                     "unmatched_events RESTART IDENTITY CASCADE")
        conn.commit()
    print("✅ Reset complete. Run scripts/run_pipeline.py to re-populate.")

if __name__ == "__main__":
    reset()
```

---

## 12. Testing Strategy

### 12.1 Unit Tests — `tests/test_normalisation.py`

```python
import pytest
from src.normalisation.name_normaliser import canonicalise_name
from src.normalisation.identifier_validator import validate_and_normalise_pan

def test_legal_suffix_removal():
    assert canonicalise_name("Peenya Garments Pvt Ltd")["canonical"] == "PEENYA GARMENTS"
    assert canonicalise_name("Sharma Textiles Private Limited")["canonical"] == "SHARMA TEXTILES"
    assert canonicalise_name("KSR Industries LLP")["canonical"] == "KSR INDUSTRIES"

def test_abbreviation_expansion():
    assert "INDUSTRIES" in canonicalise_name("Peenya Inds")["canonical"]
    assert "MANUFACTURING" in canonicalise_name("BLR Mfg Co")["canonical"]

def test_bangalore_normalisation():
    result = canonicalise_name("Bangalore Steel Works")["canonical"]
    assert "BENGALURU" in result

def test_pan_validation():
    result = validate_and_normalise_pan("AABCP1234Q")
    assert result["valid"] == True
    assert result["normalised"] == "AABCP1234Q"

def test_pan_invalid():
    result = validate_and_normalise_pan("123456789A")
    assert result["valid"] == False

def test_pan_absent():
    result = validate_and_normalise_pan("NA")
    assert result["has_value"] == False
```

### 12.2 Unit Tests — `tests/test_features.py`

```python
import pytest
from src.entity_resolution.feature_extractor import extract_features, _identifier_match_score

def test_pan_match_both_present_match():
    assert _identifier_match_score("AABCP1234Q", "AABCP1234Q") == 1.0

def test_pan_mismatch_both_present():
    assert _identifier_match_score("AABCP1234Q", "XYZAB9999Z") == -1.0

def test_pan_one_absent():
    assert _identifier_match_score("AABCP1234Q", None) == 0.5

def test_same_source_flag():
    rec_a = {"source_system": "factories", "record_id": "R1", "canonical_name": "PEENYA GARMENTS"}
    rec_b = {"source_system": "factories", "record_id": "R2", "canonical_name": "PEENYA GARMTS"}
    features = extract_features(rec_a, rec_b)
    assert features["F12"] == 1.0

def test_full_feature_vector_has_13_keys():
    rec_a = {"canonical_name": "PEENYA GARMENTS", "source_system": "factories",
             "record_id": "R1", "pin_code": "560058"}
    rec_b = {"canonical_name": "PEENYA GARMTS", "source_system": "labour",
             "record_id": "R2", "pin_code": "560058"}
    features = extract_features(rec_a, rec_b)
    assert all(f"F{str(i).zfill(2)}" in features for i in range(1, 14))
```

### 12.3 Blocking Recall Validation

```python
# tests/test_blocker.py
def test_blocking_recall(labelled_pairs, normalised_records):
    """
    Recall = true_match_pairs_in_candidates / all_true_match_pairs
    Target: >= 99.5%
    """
    candidate_pairs = set(generate_candidate_pairs(normalised_records))
    true_match_pairs = set(
        (min(a, b), max(a, b))
        for a, b in labelled_pairs
        if labelled_pairs[(a, b)] == 1
    )
    found = true_match_pairs & candidate_pairs
    recall = len(found) / len(true_match_pairs) if true_match_pairs else 1.0
    assert recall >= 0.995, f"Blocking recall {recall:.4f} below target 0.995"
```

---

## 13. Success Metrics Validation

After running the full pipeline, verify these metrics before the demo:

| Metric | Target | How to Verify |
|---|---|---|
| Entity Resolution F1 | ≥ 0.92 | Run `scorer.py` evaluation on 500-pair held-out labelled set |
| Blocking Pair Recall | ≥ 99.5% | Run `test_blocker.py` against labelled pairs |
| Auto-link Rate | 60–75% | `GET /api/review/stats` → `auto_link_rate_pct` |
| Activity Classification Accuracy | ≥ 88% | Compare computed status vs. ground truth status in synthetic data |
| UBID Lookup Response Time (p99) | < 200ms | Run `locust` or `k6` with 100 concurrent lookups |
| Unmatched Event Rate | < 5% | `SELECT COUNT(*) FROM unmatched_events` / total events |
| Review Queue Depth | 2,400–3,600 items | `GET /api/review/stats` → `queue_depth` |

---

## 14. Day-by-Day Build Schedule

```
DAY 1
  Morning:  Set up repo structure, virtual environment, install all dependencies
  Afternoon: Write entity_generator.py — 5,000 ground truth entities with all fields
  Evening:  Write department_record_generator.py — raw records per dept

DAY 2
  Morning:  Write variation_injector.py — name/address/PAN variation injection
  Afternoon: Write activity_event_generator.py — 12-month events per entity
  Evening:  Run generation, verify CSVs look realistic; fix any issues
            Set up PostgreSQL (Docker), run Alembic migrations, load CSVs

DAY 3
  Morning:  Write and test name_normaliser.py — all suffix/abbrev/phonetic logic
  Afternoon: Write and test address_parser.py — all Karnataka address formats
  Evening:  Write identifier_validator.py and pii_scrambler.py
            Write standardiser.py orchestrator; run it on all source records

DAY 4
  Morning:  Write blocker.py — all 6 blocking keys; validate recall
  Afternoon: Write feature_extractor.py — all 13 features with full test coverage
  Evening:  Generate 10,000 labelled training pairs from ground truth

DAY 5
  Morning:  Write scorer.py — LightGBM training + Platt calibration
  Afternoon: Train model; evaluate; generate SHAP values; verify explainability
            Log model to MLflow
  Evening:  Write ubid_assigner.py — Union-Find + UBID minting + DB persistence

DAY 6
  Morning:  Write signal_config.py and signal_scorer.py — decay formula + classification
  Afternoon: Write event_router.py — join events to UBIDs; unmatched event handler
  Evening:  Write activity_classifier.py; run on all UBIDs; verify status distribution

DAY 7
  Morning:  Write FastAPI main.py, dependencies.py, all Pydantic schemas
  Afternoon: Write ubid.py router — lookup and detail endpoints
  Evening:  Write activity.py router — THE DEMO QUERY endpoint

DAY 8
  Morning:  Write review.py router — queue, task detail, decision submission
  Afternoon: Write admin.py router — audit log, model stats, threshold tuning
  Evening:  API integration testing with httpx; fix all 404s and 500s

DAY 9
  Morning:  Set up React app; install Ant Design + recharts + react-leaflet
  Afternoon: Build App.jsx with routing; build api/client.js
  Evening:  Build LookupPage — search form + UBID detail card with evidence

DAY 10
  Morning:  Build ActivityPage — query form + results table + timeline modal
  Afternoon: Build ReviewPage — queue list + side-by-side card + SHAP chart
  Evening:  Build DashboardPage — status pie, sector bar chart, queue health stats

DAY 11
  Morning:  Polish all 4 frontend views; fix layout/styling issues
  Afternoon: Add error states, loading spinners, empty states
  Evening:  Connect frontend to backend; test all API calls end-to-end

DAY 12
  Morning:  Write docker-compose.yml + Dockerfiles; test full docker compose up
  Afternoon: Run scripts/run_pipeline.py on full synthetic dataset
  Evening:  Verify all success metrics; fix any failures

DAY 13 — DEMO REHEARSAL
  Morning:  Run scripts/reset_demo.py + scripts/run_pipeline.py fresh
  Afternoon: Full demo walkthrough (7 scenes) — time each scene
  Evening:  Tighten any slow queries; add indexes if needed; prepare backup screenshots
```

---

## Quick Reference: Key Commands

```bash
# First-time setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
docker compose up postgres mlflow -d

# Database setup
alembic upgrade head

# Generate synthetic data
python scripts/generate_synthetic_data.py

# Train ML model
python scripts/train_model.py

# Run full pipeline (pre-compute before demo)
python scripts/run_pipeline.py

# Start API server (dev)
uvicorn src.api.main:app --reload --port 8000

# Start frontend (dev)
cd frontend && npm start

# Full stack via Docker
docker compose up --build

# Reset demo to clean state
python scripts/reset_demo.py && python scripts/run_pipeline.py

# Run tests
pytest tests/ -v

# Check success metrics
python scripts/validate_metrics.py
```

---

*UBID Platform — Comprehensive Prototype Build Plan*
*AI Bharat Hackathon 2026 | Karnataka Commerce & Industry | Theme 1*