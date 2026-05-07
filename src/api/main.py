"""
api/main.py
FastAPI application entrypoint.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import ubid, activity, review, admin, nlquery
from src.api.audit_middleware import AuditMiddleware
import os

app = FastAPI(
    title="UBID Platform API",
    description="Unified Business Identifier & Active Business Intelligence Platform",
    version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

app.include_router(ubid.router,      prefix="/api/ubid",      tags=["UBID"])
app.include_router(activity.router,  prefix="/api/activity",  tags=["Activity"])
app.include_router(review.router,    prefix="/api/review",    tags=["Review"])
app.include_router(admin.router,     prefix="/api/admin",     tags=["Admin"])
app.include_router(nlquery.router,   prefix="/api",           tags=["NL Query"])


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ubid-platform"}
