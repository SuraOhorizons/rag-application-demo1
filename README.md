# rag-application-demo1

Prueba exploratoria del golden path RAG Application (H3) — evaluar la infraestructura y el pipeline generados antes de definir el caso de uso final.

## Overview

This RAG (Retrieval-Augmented Generation) application was created using the Open Horizons Platform - H3 Innovation template.
|||||
| Property | Value |
|----------|-------|
| Owner | group:default/platform-engineering |
| System | default |
| Lifecycle | production |
| AI Model |  |

## Architecture

![RAG Architecture](../../../../docs/assets/gp-rag-application.svg)

## Features

- Document ingestion and chunking
- Vector embeddings with Azure OpenAI
- Semantic search with Azure AI Search
- Conversational memory
- Source citations
- Content safety filtering

## Getting Started

### Prerequisites

- Python 3.11+
- Azure subscription with:
  - Azure OpenAI Service
  - Azure AI Search
  - Azure Blob Storage
- Docker

### Environment Variables

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-search-key
AZURE_SEARCH_INDEX=documents

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
AZURE_STORAGE_CONTAINER=documents
```

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn src.main:app --reload

# Run tests
pytest
```

### Docker

```bash
# Build
docker build -t rag-application-demo1:local .

# Run
docker run -p 8000:8000 --env-file .env rag-application-demo1:local
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /chat | Send a chat message |
| POST | /documents | Upload documents |
| GET | /documents | List indexed documents |
| DELETE | /documents/{id} | Remove document |
| GET | /health | Health check |
| GET | /metrics | Prometheus metrics |

## Document Processing

Supported formats:
- PDF
- DOCX
- TXT
- MD
- HTML

Chunking strategy:
- Chunk size: 1000 tokens
- Overlap: 200 tokens
- Semantic chunking for better context

## Monitoring

- **Metrics**: Token usage, latency, cache hits
- **Logging**: Structured JSON logs
- **Tracing**: OpenTelemetry integration

## Security

- Content Safety API for input/output filtering
- API key authentication
- Rate limiting
- Input validation

## Links

- [Open Horizons Documentation](https://github.com/suraOhorizons/open-horizons-platform)
- [Azure OpenAI Documentation](https://docs.microsoft.com/azure/cognitive-services/openai/)
- [LangChain Documentation](https://python.langchain.com/)
