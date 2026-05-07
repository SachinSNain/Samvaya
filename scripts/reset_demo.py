"""
scripts/reset_demo.py
Truncates the UBID registry and activity tables to allow fresh pipeline runs,
while leaving raw source records and raw activity events intact.
"""
import sys
import logging
from pathlib import Path
from sqlalchemy import text

# Ensure src is in the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.connection import engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def reset_tables():
    logger.info("Connecting to database to truncate UBID tables...")

    tables_to_truncate = [
        "unmatched_events",
        "activity_scores",
        "ubid_activity_events",
        "review_tasks",
        "ubid_link_evidence",
        "ubid_source_links",
        "ubid_entities"
    ]

    with engine.begin() as conn:
        for table in tables_to_truncate:
            logger.info(f"Truncating {table}...")
            # Use CASCADE to handle any lingering foreign key dependencies
            conn.execute(
                text(
                    f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))

        # Reset processed flags in raw events
        logger.info("Resetting processed flag in activity_events_raw...")
        conn.execute(text("UPDATE activity_events_raw SET processed = FALSE;"))

    logger.info("Database successfully reset for a fresh pipeline run.")


if __name__ == "__main__":
    reset_tables()
