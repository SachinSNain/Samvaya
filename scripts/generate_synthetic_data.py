"""
Phase 1 — run once to populate data/raw/ and data/ground_truth/.

Usage:
    python scripts/generate_synthetic_data.py [--entities 5000] [--seed 42]
"""
import argparse
import csv
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

# MUST be before any src.* imports
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from src.data_generation import (
    generate_entities,
    generate_department_records,
    generate_activity_events,
)

from tqdm import tqdm

# Absolute paths to avoid Docker-Windows volume issues
RAW_DIR = _REPO_ROOT / "data" / "raw"
PROCESSED_DIR = _REPO_ROOT / "data" / "processed"
GROUND_TRUTH_DIR = _REPO_ROOT / "data" / "ground_truth"


def write_csv(path: Path, rows: list, fieldnames: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Delete first to avoid Docker-Windows WSL2 file lock (OSError 22)
    path.unlink(missing_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {len(rows):,} rows -> {path}")


def main(n_entities: int = 5000, seed: int = 42):
    print(f"\n=== UBID Synthetic Data Generator ===")
    print(f"Entities: {n_entities:,}  |  Seed: {seed}\n")

    # ── Step 1: Ground-truth entities ─────────────────────────────────────
    print("Step 1/4  Generating ground-truth entities...")
    entities = generate_entities(n=n_entities, seed=seed)
    print(f"  Generated {len(entities):,} entities\n")

    # ── Step 2: Department records ─────────────────────────────────────────
    print("Step 2/4  Generating department records...")
    dept_records = generate_department_records(entities)
    total_dept = sum(len(v) for v in dept_records.values())
    print(f"  Total department records: {total_dept:,}")
    for dept, rows in dept_records.items():
        print(f"    {dept}: {len(rows):,}")

    # Write shop_establishment.csv
    write_csv(
        RAW_DIR /
        "shop_establishment.csv",
        dept_records["shop_establishment"],
        fieldnames=[
            "se_reg_no",
            "business_name",
            "owner_name",
            "address",
            "pin_code",
            "pan",
            "gstin",
            "phone",
            "trade_category",
            "registration_date",
            "status",
            "entity_id",
        ],
    )

    # Write factories.csv
    write_csv(
        RAW_DIR / "factories.csv",
        dept_records["factories"],
        fieldnames=[
            "factory_licence_no",
            "factory_name",
            "owner_name",
            "address",
            "pin_code",
            "pan",
            "gstin",
            "phone",
            "product_description",
            "nic_code",
            "num_workers",
            "licence_valid_until",
            "registration_date",
            "status",
            "entity_id",
        ],
    )

    # Write labour.csv
    write_csv(
        RAW_DIR / "labour.csv",
        dept_records["labour"],
        fieldnames=[
            "employer_code",
            "employer_name",
            "owner_name",
            "address",
            "pin_code",
            "pan",
            "gstin",
            "phone",
            "industry_type",
            "num_employees",
            "registration_date",
            "status",
            "entity_id",
        ],
    )

    # Write kspcb.csv
    write_csv(
        RAW_DIR / "kspcb.csv",
        dept_records["kspcb"],
        fieldnames=[
            "consent_order_no",
            "unit_name",
            "owner_name",
            "address",
            "pin_code",
            "pan",
            "gstin",
            "phone",
            "nic_code",
            "consent_type",
            "consent_valid_until",
            "registration_date",
            "status",
            "entity_id",
        ],
    )

    # ── Step 3: Activity events ────────────────────────────────────────────
    print("\nStep 3/4  Generating activity events (12-month stream)...")
    events = generate_activity_events(entities)
    print(f"  Generated {len(events):,} events")

    write_csv(
        RAW_DIR / "activity_events.csv",
        events,
        fieldnames=[
            "event_id", "source_system", "source_record_id", "event_type",
            "event_timestamp", "entity_id", "payload_json", "processed",
        ],
    )

    # ── Step 4: Ground-truth files ─────────────────────────────────────────
    print("\nStep 4/4  Writing ground-truth files...")

    # entity_clusters.csv — maps every (source_system, source_record_id) to
    # entity_id
    cluster_rows = []
    id_field_map = {
        "shop_establishment": "se_reg_no",
        "factories": "factory_licence_no",
        "labour": "employer_code",
        "kspcb": "consent_order_no",
    }
    for dept, rows in dept_records.items():
        id_field = id_field_map[dept]
        for row in rows:
            cluster_rows.append({
                "entity_id": row["entity_id"],
                "source_system": dept,
                "source_record_id": row[id_field],
            })

    write_csv(
        GROUND_TRUTH_DIR / "entity_clusters.csv",
        cluster_rows,
        fieldnames=["entity_id", "source_system", "source_record_id"],
    )

    # labelled_pairs.csv — positive + negative pairs for ML training
    print("  Building labelled pairs...")
    labelled_pairs = _build_labelled_pairs(
        dept_records, id_field_map, n_entities)
    write_csv(
        GROUND_TRUTH_DIR /
        "labelled_pairs.csv",
        labelled_pairs,
        fieldnames=[
            "pair_id",
            "record_a_id",
            "record_b_id",
            "source_a",
            "source_b",
            "label"],
    )

    # Summary
    print(f"\n{'=' * 40}")
    print(f"Summary:")
    print(f"  Ground-truth entities : {len(entities):,}")
    print(f"  Total dept records    : {total_dept:,}")
    print(f"  Activity events       : {len(events):,}")
    print(f"  Labelled pairs        : {len(labelled_pairs):,}")
    print(f"{'=' * 40}\n")
    print("Done! All files written to data/")


def _build_labelled_pairs(
        dept_records: dict,
        id_field_map: dict,
        n_entities: int) -> list:
    import random

    # Build entity_id → list of (source_system, source_record_id)
    entity_to_records: dict[str, list] = {}
    for dept, rows in dept_records.items():
        id_field = id_field_map[dept]
        for row in rows:
            eid = row["entity_id"]
            entity_to_records.setdefault(eid, []).append((dept, row[id_field]))

    # Positive pairs: records from same entity across different depts
    positives = []
    all_entity_ids = list(entity_to_records.keys())
    for eid in all_entity_ids:
        recs = entity_to_records[eid]
        if len(recs) >= 2:
            a, b = random.sample(recs, 2)
            positives.append({
                "pair_id": f"P_{len(positives) + 1:06d}",
                "record_a_id": a[1], "source_a": a[0],
                "record_b_id": b[1], "source_b": b[0],
                "label": 1,
            })

    # Negative pairs: records from different entities
    negatives = []
    target_neg = len(positives)
    all_records = [(dept, row[id_field_map[dept]], row["entity_id"])
                   for dept, rows in dept_records.items()
                   for row in rows]

    attempts = 0
    while len(negatives) < target_neg and attempts < target_neg * 10:
        attempts += 1
        a, b = random.sample(all_records, 2)
        if a[2] != b[2]:  # different entity
            negatives.append({
                "pair_id": f"N_{len(negatives) + 1:06d}",
                "record_a_id": a[1], "source_a": a[0],
                "record_b_id": b[1], "source_b": b[0],
                "label": 0,
            })

    return positives + negatives


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate UBID synthetic data")
    parser.add_argument(
        "--entities",
        type=int,
        default=5000,
        help="Number of ground-truth entities")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    main(n_entities=args.entities, seed=args.seed)
