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
    Counter,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel
from starlette.responses import Response
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
import os


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


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


credential = DefaultAzureCredential()

openai_client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2024-10-21",
    azure_ad_token_provider=lambda: credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token,
)

OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]


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

    CHAT_REQUESTS.inc()

    with CHAT_LATENCY.time():
        conversation_id = request.conversation_id or str(uuid.uuid4())

        try:
            response = openai_client.chat.completions.create(
                model=OPENAI_DEPLOYMENT,
                messages=[
                    {
                        "role": "user",
                        "content": request.query,
                    },
                ],
                max_completion_tokens=1000,
            )

            return ChatResponse(
                answer=response.choices[0].message.content or "",
                sources=[],
                conversation_id=conversation_id,
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

    DOCUMENTS_INDEXED.inc()

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
