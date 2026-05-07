"""
api/audit_middleware.py
Starlette middleware that writes an AuditEvent row for every mutating API call
(POST / PUT / PATCH / DELETE) that returns a 2xx status.
Read-only GET requests are not logged — too noisy, and the DB handles history.
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Paths that are too chatty to audit individually (polling endpoints)
_SKIP_PATHS = {"/health", "/api/admin/pipeline/status"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        method = request.method
        path = request.url.path

        # Only audit mutating calls that succeeded
        if method in ("POST", "PUT", "PATCH", "DELETE") and 200 <= response.status_code < 300:
            if not any(path.startswith(skip) for skip in _SKIP_PATHS):
                _write_audit_background(
                    event_type=f"{method.lower()}:{path}",
                    actor=request.headers.get("X-Reviewer-ID", "anonymous"),
                    target_id=path.split("/")[-1],
                    detail={"status_code": response.status_code, "path": path},
                )

        return response


def _write_audit_background(event_type: str, actor: str, target_id: str, detail: dict):
    """Fire-and-forget DB write — runs in the same thread, keeps it simple."""
    try:
        from src.database.connection import SessionLocal
        from src.database.models import AuditEvent
        db = SessionLocal()
        try:
            db.add(AuditEvent(
                event_type=event_type,
                actor=actor,
                target_id=target_id,
                detail=detail,
            ))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning("Audit write failed: %s", e)
