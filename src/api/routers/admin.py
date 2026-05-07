"""
api/routers/admin.py
Endpoints for admin controls, stats, audit logs, and pipeline job management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database.connection import get_db
from src.database.models import AuditEvent
import os
import json
from pathlib import Path

router = APIRouter()

_METRICS_PATH = Path(__file__).resolve().parent.parent.parent / "entity_resolution" / "models" / "metrics.json"


@router.get("/model-stats")
def get_model_stats():
    metrics = {}
    try:
        with open(_METRICS_PATH) as f:
            metrics = json.load(f)
    except Exception:
        pass

    return {
        "model_version": metrics.get("model_version", "1.0.0"),
        "val_auc": metrics.get("val_auc", None),
        "val_f1": metrics.get("val_f1", None),
        "last_retrain": metrics.get("trained_at", None),
        "train_size": metrics.get("train_size", None),
        "val_size": metrics.get("val_size", None),
        "auto_link_threshold": float(os.getenv("THRESHOLD_AUTO_LINK", "0.95")),
        "review_threshold": float(os.getenv("THRESHOLD_REVIEW", "0.75")),
    }


@router.post("/thresholds")
def update_thresholds(payload: dict):
    auto = payload.get("auto_link_threshold")
    rev = payload.get("review_threshold")
    return {
        "status": "success",
        "message": "Thresholds updated (requires restart to take effect)",
        "new_auto_link_threshold": auto,
        "new_review_threshold": rev
    }


# ── Pipeline job management ────────────────────────────────────────────────────

@router.post("/pipeline/run")
def trigger_pipeline(db: Session = Depends(get_db)):
    """Enqueue the full entity resolution pipeline as a Celery task."""
    try:
        from src.celery_app import run_pipeline_task
        task = run_pipeline_task.delay()
        _write_audit(db, "pipeline_triggered", "system", {"task_id": task.id})
        return {"task_id": task.id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not enqueue pipeline: {e}")


@router.post("/pipeline/reroute")
def trigger_reroute(db: Session = Depends(get_db)):
    """Enqueue the event rerouting step as a Celery task."""
    try:
        from src.celery_app import reroute_events_task
        task = reroute_events_task.delay()
        _write_audit(db, "reroute_triggered", "system", {"task_id": task.id})
        return {"task_id": task.id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not enqueue reroute: {e}")


@router.get("/pipeline/status/{task_id}")
def get_pipeline_status(task_id: str):
    """Poll Celery task status and progress."""
    try:
        from src.celery_app import app as celery_app
        result = celery_app.AsyncResult(task_id)
        info = result.info if isinstance(result.info, dict) else {}
        return {
            "task_id": task_id,
            "state": result.state,        # PENDING / PROGRESS / SUCCESS / FAILURE
            "step": info.get("step"),
            "detail": info.get("detail"),
            "result": result.result if result.state == "SUCCESS" else None,
            "error": str(result.info) if result.state == "FAILURE" else None,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch task status: {e}")


# ── Audit log ──────────────────────────────────────────────────────────────────

@router.get("/audit-log")
def get_audit_log(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    logs = (
        db.query(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "logs": [
            {
                "event_type": e.event_type,
                "actor": e.actor,
                "target_id": e.target_id,
                "detail": e.detail,
                "timestamp": str(e.created_at),
            }
            for e in logs
        ]
    }


def _write_audit(db: Session, event_type: str, actor: str, detail: dict = None, target_id: str = None):
    """Helper used by other routers to write audit events."""
    try:
        db.add(AuditEvent(
            event_type=event_type,
            actor=actor,
            target_id=target_id,
            detail=detail or {},
        ))
        db.commit()
    except Exception:
        db.rollback()
