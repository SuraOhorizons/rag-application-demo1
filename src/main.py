"""
rag-application-demo1 - RAG Application

FastAPI backend base for the RAG application.

Phase 1:
- Run the backend without AI dependencies.
- Health, readiness and metrics endpoints are available.
- Chat and document endpoints return HTTP 503 until Phase 2.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)
from pydantic import BaseModel
from starlette.responses import Response
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from src.rag import RAGService
import os


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


credential = DefaultAzureCredential()

openai_client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2024-10-21",
    azure_ad_token_provider=lambda: credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token,
)

OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_INDEX = os.environ.get(
    "AZURE_SEARCH_INDEX",
    "documents",
)

rag_service = RAGService(
    openai_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    openai_key="",
    openai_deployment=OPENAI_DEPLOYMENT,
    search_endpoint=SEARCH_ENDPOINT,
    search_key="",
    search_index=SEARCH_INDEX,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""

    logger.info(
        "Starting rag-application-demo1 in backend-only mode"
    )

    logger.info(
        "RAG service is disabled until Phase 2"
    )

    yield

    logger.info(
        "Shutting down application"
    )


app = FastAPI(
    title="rag-application-demo1",
    description=(
        "Backend base for the RAG Application. "
        "Phase 1 runs without Azure OpenAI or Azure AI Search."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    """Chat request model."""

    query: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    """Chat response model."""

    answer: str
    sources: list[dict]
    conversation_id: str


class HealthResponse(BaseModel):
    """Health response model."""

    status: str
    version: str


@app.get(
    "/health",
    response_model=HealthResponse,
)
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
        "rag_enabled": False,
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(request: ChatRequest):
    """Chat endpoint."""

    try:
        result = await rag_service.chat(
            query=request.query,
            conversation_id=request.conversation_id,
        )

        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            conversation_id=result["conversation_id"],
        )

    except Exception as exc:
        logger.exception("Azure OpenAI request failed")
        raise HTTPException(
            status_code=502,
            detail=f"Azure OpenAI error: {exc}",
        )

@app.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
):
    """Document ingestion endpoint reserved for Phase 2."""

    raise HTTPException(
        status_code=503,
        detail="Document service is not configured yet",
    )


@app.get("/documents")
async def list_documents():
    """Document listing endpoint reserved for Phase 2."""

    raise HTTPException(
        status_code=503,
        detail="Document service is not configured yet",
    )
