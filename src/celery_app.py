"""
src/celery_app.py
Celery application instance and task definitions.
"""
import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

broker = os.getenv("CELERY_BROKER_URL", "amqp://ubid:ubid_rabbit@localhost:5672//")
backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

app = Celery("ubid", broker=broker, backend=backend)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,           # re-queue if worker crashes mid-task
    worker_prefetch_multiplier=1,  # one task at a time per worker (pipeline is heavy)
    result_expires=86400,          # keep results for 24 h
)


@app.task(bind=True, name="ubid.run_pipeline", max_retries=0)
def run_pipeline_task(self):
    """
    Runs the full entity resolution pipeline as a Celery task.
    Progress is reported via self.update_state so the API can poll it.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    self.update_state(state="PROGRESS", meta={"step": "starting", "detail": "Pipeline initialising"})
    logger.info("Celery pipeline task started: %s", self.request.id)

    try:
        # Import here so the worker only loads heavy deps when actually running
        from scripts.run_pipeline import run
        run(progress_callback=lambda step, detail: self.update_state(
            state="PROGRESS", meta={"step": step, "detail": detail}
        ))
    except Exception as exc:
        logger.exception("Pipeline task failed")
        raise

    return {"status": "complete"}


@app.task(bind=True, name="ubid.reroute_events", max_retries=1)
def reroute_events_task(self):
    """Runs reroute_events.py as an async task after pipeline completes."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    self.update_state(state="PROGRESS", meta={"step": "rerouting", "detail": "Routing events to UBIDs"})
    try:
        from scripts.reroute_events import run
        result = run()
        return result
    except Exception as exc:
        logger.exception("Reroute task failed")
        raise
