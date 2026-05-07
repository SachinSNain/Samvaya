import sys, os
sys.path.insert(0, '.')
import logging
from sqlalchemy.orm import Session
from src.database.connection import SessionLocal
from src.database.models import UBIDSourceLink, UBIDEntity
from src.activity_engine.event_router import route_all_events
from src.activity_engine.activity_classifier import classify_all_ubids

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def finish_step_9():
    with SessionLocal() as db:
        logger.info("Fetching record_to_ubid mapping from DB...")
        links = db.query(UBIDSourceLink).all()
        record_to_ubid = {f"{link.source_system}:{link.source_record_id}": link.ubid for link in links}
        
        logger.info("=== STEP 9: Activity Engine Routing & Classification ===")
        route_stats = route_all_events(record_to_ubid, db)
        logger.info(f"Route Stats: {route_stats}")

        all_ubids = [u[0] for u in db.query(UBIDEntity.ubid).all()]
        logger.info(f"Classifying {len(all_ubids)} UBIDs...")
        classify_all_ubids(all_ubids, db)

        logger.info("=== PIPELINE RUN COMPLETE ===")

if __name__ == '__main__':
    finish_step_9()
