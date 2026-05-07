"""
Pre-generates AI reviewer summaries via Gemini 2.5 Flash for all REVIEW-bucket tasks.
Input:  scrambled canonical fields (safe for API lane — no raw PII sent to cloud).
Output: stored in review_tasks.reviewer_summary (DB).
Rate-limited to 12 req/min to stay under Gemini free tier 15 RPM.

Run the night before the demo:
    python scripts/pregenerate_summaries.py
Then:
    python scripts/reset_demo.py
Zero live API calls will be needed during the presentation.
"""
import time
import sys
from pathlib import Path

# Add project root to sys.path so src.* imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tqdm import tqdm
from src.database.connection import SessionLocal
from src.database.models import ReviewTask
from src.normalisation.pii_scrambler import scramble_record
from src.llm_router import generate_reviewer_summary

# Lazy-loaded source model map — avoids circular imports at module level
_SOURCE_MODELS = None


def _get_source_models() -> dict:
    global _SOURCE_MODELS
    if _SOURCE_MODELS is None:
        from src.database.models import (
            DeptShopEstablishment, DeptFactories, DeptLabour, DeptKSPCB,
        )
        _SOURCE_MODELS = {
            "shop_establishment": (
                DeptShopEstablishment, "se_reg_no",         "business_name", "address",
            ),
            "factories": (
                DeptFactories,         "factory_licence_no", "factory_name",  "address",
            ),
            "labour": (
                DeptLabour,            "employer_code",      "employer_name", "address",
            ),
            "kspcb": (
                DeptKSPCB,             "consent_order_no",   "unit_name",     "address",
            ),
        }
    return _SOURCE_MODELS


def _fetch_source_record(source_ref: str, db) -> dict:
    """
    Fetch raw record from the correct dept table and scramble it before
    sending to the API lane. source_ref format: "source_system:record_id".
    """
    if ":" not in source_ref:
        raise ValueError(
            f"source_ref must be 'system:record_id', got: {source_ref!r}"
        )

    source_system, record_id = source_ref.split(":", 1)
    models = _get_source_models()

    if source_system not in models:
        raise ValueError(f"Unknown source_system: {source_system!r}")

    model_cls, pk_field, name_field, addr_field = models[source_system]
    record = db.query(model_cls).filter(
        getattr(model_cls, pk_field) == record_id
    ).first()

    if record is None:
        raise LookupError(
            f"Record {record_id!r} not found in {source_system}"
        )

    raw = {
        "name":    getattr(record, name_field, None),
        "address": getattr(record, addr_field, None),
        "pan":     getattr(record, "pan", None),
        "phone":   getattr(record, "phone", None),
    }
    return scramble_record(raw)


def pregenerate():
    db = SessionLocal()
    tasks = (
        db.query(ReviewTask)
        .filter(
            ReviewTask.status == "PENDING",
            ReviewTask.reviewer_summary == None,
        )
        .all()
    )

    print(f"Found {len(tasks)} tasks without pre-generated summaries.")

    for task in tqdm(tasks, desc="Generating summaries"):
        try:
            rec_a = _fetch_source_record(task.pair_record_a, db)
            rec_b = _fetch_source_record(task.pair_record_b, db)

            feature_scores = task.feature_vector or {}
            if isinstance(feature_scores, str):
                import json
                feature_scores = json.loads(feature_scores)

            summary = generate_reviewer_summary(
                rec_a, rec_b, feature_scores, task.calibrated_score or 0.0
            )
            task.reviewer_summary = summary
            db.commit()
            time.sleep(5)   # 12 req/min — stays under free tier 15 RPM
        except Exception as e:
            print(f"  WARNING: Failed task {task.task_id}: {e}")
            db.rollback()

    db.close()
    print("Pre-generation complete. Now run: python scripts/reset_demo.py")


if __name__ == "__main__":
    pregenerate()
