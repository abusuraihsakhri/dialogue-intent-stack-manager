"""
FastAPI REST API Server for Dialogue Intent Stack Manager.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pathlib import Path
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard, SecurityException
from .metrics import GLOBAL_METRICS
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Dialogue Intent Stack Manager API",
    description="Enterprise Distributed Component Platform (Long-Horizon Agent Context & State Architecture)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "index.html")


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "dialogue-intent-stack-manager", "domain": "Long-Horizon Agent Context & State Architecture", "standard": "Autonomous Agent State Machine & Token Economy RFC", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    GLOBAL_METRICS.audit_blocks_total = len(AuditLogger.get_trail())
    return PlainTextResponse(
        GLOBAL_METRICS.export_prometheus_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
    except SecurityException:
        GLOBAL_METRICS.record_phi_block()
        raise HTTPException(status_code=422, detail="Input contains a prohibited identifier pattern")
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException:
        GLOBAL_METRICS.record_phi_block()
        raise HTTPException(status_code=422, detail="Input contains a prohibited identifier pattern")


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
