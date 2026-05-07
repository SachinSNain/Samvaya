"""
scripts/run_pipeline.py
End-to-end orchestration of the UBID Entity Resolution & Activity Pipeline.
"""
import sys
import uuid
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.activity_engine.activity_classifier import classify_all_ubids
from src.activity_engine.event_router import route_all_events
from src.entity_resolution.ubid_assigner import assign_ubids
from src.entity_resolution.scorer import load_models, score_pair
from src.entity_resolution.feature_extractor import extract_features
from src.entity_resolution.blocker import generate_candidate_pairs
from src.normalisation.standardiser import standardise_record
from src.database.models import (
    DeptShopEstablishment, DeptFactories, DeptLabour, DeptKSPCB,
    UBIDEntity, UBIDSourceLink, UBIDLinkEvidence, ReviewTask
)
from src.database.connection import SessionLocal


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run(progress_callback=None):
    def _progress(step: str, detail: str = ""):
        logger.info("=== %s === %s", step, detail)
        if progress_callback:
            progress_callback(step, detail)

    db = SessionLocal()
    try:
        _progress("STEP 1", "Load Source Records")
        raw_records = []
        for model, source_name in [
            (DeptShopEstablishment, "shop_establishment"),
            (DeptFactories, "factories"),
            (DeptLabour, "labour"),
            (DeptKSPCB, "kspcb")
        ]:
            records = db.query(model).all()
            for r in records:
                d = r.__dict__.copy()
                d.pop('_sa_instance_state', None)
                d["source_system"] = source_name
                raw_records.append(d)
        logger.info(f"Loaded {len(raw_records)} total raw records.")

        _progress("STEP 2", "Normalise Records")
        normalised_records = [
            standardise_record(
                r, skip_geocoding=True) for r in raw_records]

        # Build lookup dicts for quick access later
        record_lookup = {r["record_id"]: r for r in normalised_records}

        _progress("STEP 3", "Generate Candidate Pairs (Blocking)")
        candidate_pairs = generate_candidate_pairs(normalised_records)
        logger.info(f"Generated {len(candidate_pairs)} candidate pairs.")

        _progress("STEP 4", f"Feature Extraction & Scoring ({len(candidate_pairs)} pairs)")
        calib_model, base_model, shap_explainer = load_models()

        auto_link_pairs = []
        # scored_evidence: record_id pair -> {features, shap, score} for AUTO_LINK
        scored_evidence: dict = {}
        review_bucket = []

        for idx, (id_a, id_b) in enumerate(candidate_pairs):
            if idx > 0 and idx % 1000 == 0:
                logger.info(f"Scored {idx} pairs...")

            rec_a = record_lookup[id_a]
            rec_b = record_lookup[id_b]

            features = extract_features(rec_a, rec_b)
            result = score_pair(features, calib_model, base_model, shap_explainer, rec_a, rec_b)

            decision = result["decision"]
            if decision == "AUTO_LINK":
                auto_link_pairs.append((id_a, id_b))
                scored_evidence[(id_a, id_b)] = {
                    "features": features,
                    "shap": result["shap_values"],
                    "score": result["calibrated_score"],
                }
            elif decision == "REVIEW":
                review_bucket.append({
                    "record_a_id": id_a,
                    "record_b_id": id_b,
                    "score": result["calibrated_score"],
                    "features": features,
                    "shap": result["shap_values"],
                    "reviewer_notes": result.get("reviewer_explanation")
                })

        logger.info(
            f"Scoring Complete. Auto-Link: {len(auto_link_pairs)}, Review: {len(review_bucket)}")

        _progress("STEP 6", "UBID Assignment (Union-Find)")
        record_to_ubid, ubid_to_anchor = assign_ubids(
            auto_link_pairs, normalised_records)
        logger.info(f"Generated {len(ubid_to_anchor)} unique UBIDs.")

        _progress("STEP 7", "Persist UBID Registry")
        for ubid, anchor_data in ubid_to_anchor.items():
            db.add(UBIDEntity(
                ubid=ubid,
                pan_anchor=anchor_data["pan_anchor"],
                gstin_anchors=anchor_data["gstin_anchors"],
                anchor_status=anchor_data["anchor_status"],
                activity_status="UNKNOWN"
            ))

        # Build record -> best evidence index once (O(n)) instead of scanning per record (O(n²))
        record_best_evidence: dict = {}
        for (pa, pb), ev in scored_evidence.items():
            for rid in (pa, pb):
                existing = record_best_evidence.get(rid)
                if existing is None or ev["score"] > existing["score"]:
                    record_best_evidence[rid] = {"pa": pa, "pb": pb, **ev}

        for rid, ubid in record_to_ubid.items():
            source_sys, source_id = rid.split(":", 1)
            link_id = str(uuid.uuid4())
            link = UBIDSourceLink(
                link_id=link_id,
                ubid=ubid,
                source_system=source_sys,
                source_record_id=source_id,
                confidence=1.0,
                link_type="AUTO_LINK",
                is_active=True
            )
            db.add(link)
            db.flush()

            best = record_best_evidence.get(rid)
            db.add(UBIDLinkEvidence(
                evidence_id=str(uuid.uuid4()),
                link_id=link_id,
                pair_record_a=best["pa"] if best else None,
                pair_record_b=best["pb"] if best else None,
                calibrated_score=best["score"] if best else None,
                feature_vector=best["features"] if best else {},
                shap_values=best["shap"] if best else {},
                decision="AUTO_LINK" if best else "STANDALONE",
                model_version="1.0.0",
            ))

        _progress("STEP 8", "Create Review Tasks")
        for rev in review_bucket:
            evidence_id = str(uuid.uuid4())
            db.add(UBIDLinkEvidence(
                evidence_id=evidence_id,
                link_id=None,
                pair_record_a=rev["record_a_id"],
                pair_record_b=rev["record_b_id"],
                calibrated_score=rev["score"],
                feature_vector=rev["features"],
                shap_values=rev["shap"],
                decision="REVIEW",
                model_version="1.0.0",
            ))
            db.flush()  # ensure evidence row exists before review_task FK references it
            task = ReviewTask(
                task_id=str(uuid.uuid4()),
                pair_record_a=rev["record_a_id"],
                pair_record_b=rev["record_b_id"],
                evidence_id=evidence_id,
                calibrated_score=rev["score"],
                status="PENDING",
                reviewer_notes=rev["reviewer_notes"]
            )
            db.add(task)

        db.commit()
        logger.info("UBID Registry and Review Queue saved to DB.")

        _progress("STEP 9", "Activity Engine Routing & Classification")
        # Build entity_id → ubid lookup from dept tables so events with ENT_XXXXXX
        # source_record_ids can be routed correctly
        from sqlalchemy import text as _text
        entity_id_to_ubid: dict = {}
        for dept_table, pk_col in [
            ("dept_shop_establishment", "se_reg_no"),
            ("dept_factories",          "factory_licence_no"),
            ("dept_labour",             "employer_code"),
            ("dept_kspcb",              "consent_order_no"),
        ]:
            rows = db.execute(
                _text(f"SELECT entity_id, {pk_col} FROM {dept_table} WHERE entity_id IS NOT NULL")
            ).fetchall()
            for entity_id, pk in rows:
                source_key = f"{dept_table.replace('dept_', '')}:{pk}"
                if source_key in record_to_ubid:
                    entity_id_to_ubid[entity_id] = record_to_ubid[source_key]

        # Merge entity_id → ubid into record_to_ubid under the "any:" prefix
        for eid, ubid in entity_id_to_ubid.items():
            record_to_ubid[f"any:{eid}"] = ubid

        logger.info(f"Built entity_id→UBID map: {len(entity_id_to_ubid)} entries")
        route_stats = route_all_events(record_to_ubid, db)

        all_ubids = list(ubid_to_anchor.keys())
        classify_all_ubids(all_ubids, db)

        _progress("COMPLETE", "Pipeline run complete")

    except Exception as e:
        db.rollback()
        logger.error(f"Pipeline failed: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    run()
