"""
rag-application-demo1 - Backend API

Phase 1:
- FastAPI backend
- Health endpoint
- Readiness endpoint
- Prometheus metrics
- Chat endpoint reserved for Phase 2
- Documents endpoint reserved for Phase 2
"""

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from starlette.responses import Response


# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# Metrics
CHAT_REQUESTS = Counter(
    "rag_chat_requests_total",
    "Total chat requests",
)

CHAT_LATENCY = Histogram(
    "rag_chat_latency_seconds",
    "Chat request latency",
)

DOCUMENTS_INDEXED = Counter(
    "rag_documents_indexed_total",
    "Total documents indexed",
)


# Application
app = FastAPI(
    title="rag-application-demo1",
    description=(
        "RAG Application backend. "
        "Phase 1 provides the backend foundation and observability. "
        "AI capabilities will be enabled in Phase 2."
    ),
    version="1.0.0",
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str


# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
    )


@app.get("/ready")
async def ready():
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "phase": 1,
        "ai_enabled": False,
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint reserved for Phase 2 AI integration."""

    CHAT_REQUESTS.inc()

    raise HTTPException(
        status_code=503,
        detail="Chat service is not available in Phase 1",
    )


@app.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    """Document ingestion endpoint reserved for Phase 2."""

    raise HTTPException(
        status_code=503,
        detail="Document service is not available in Phase 1",
    )


@app.get("/documents")
async def list_documents():
    """Document listing endpoint reserved for Phase 2."""

    raise HTTPException(
        status_code=503,
        detail="Document service is not available in Phase 1",
    )
