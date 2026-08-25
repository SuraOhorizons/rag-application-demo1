"""RAG Service implementation."""

import json
import logging
import time
import uuid

from prometheus_client import Counter, Gauge, Histogram

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


# ============================================================
# PROMETHEUS METRICS
# ============================================================

CHAT_REQUESTS = Counter(
    "rag_chat_requests_total",
    "Total chat requests",
)

CHAT_EMPTY_RESPONSES = Counter(
    "rag_chat_empty_responses_total",
    "Total chat requests that returned an empty response",
)

CHAT_ERRORS = Counter(
    "rag_chat_errors_total",
    "Total chat processing errors",
)

CHAT_LATENCY = Histogram(
    "rag_chat_latency_seconds",
    "Total chat request latency",
)

RETRIEVAL_REQUESTS = Counter(
    "rag_retrieval_requests_total",
    "Total Azure AI Search retrieval operations",
)

RETRIEVAL_DOCUMENTS = Counter(
    "rag_retrieval_documents_total",
    "Total documents returned by retrieval",
)

RETRIEVAL_LATENCY = Histogram(
    "rag_retrieval_latency_seconds",
    "Azure AI Search retrieval latency",
)

LLM_REQUESTS = Counter(
    "rag_llm_requests_total",
    "Total Azure OpenAI generation requests",
)

LLM_ERRORS = Counter(
    "rag_llm_errors_total",
    "Total Azure OpenAI generation errors",
)

LLM_LATENCY = Histogram(
    "rag_llm_latency_seconds",
    "Azure OpenAI generation latency",
)

DOCUMENTS_BY_SOURCE = Gauge(
    "rag_documents_by_source",
    "Documents retrieved by source in the latest request",
    ["source"],
)

RETRIEVAL_RESULTS = Gauge(
    "rag_retrieval_results",
    "Number of documents returned by the latest retrieval",
)

CONTEXT_LENGTH = Gauge(
    "rag_context_characters",
    "Characters included in the latest RAG context",
)

CONVERSATION_HISTORY = Gauge(
    "rag_conversation_history_messages",
    "Messages retained in the latest conversation",
)


class RAGService:
    """Retrieval-Augmented Generation service."""

    def __init__(
        self,
        openai_endpoint: str,
        openai_key: str,
        openai_deployment: str,
        search_endpoint: str,
        search_key: str,
        search_index: str,
    ):
        """Initialize RAG service."""
        credential = DefaultAzureCredential()

        self.openai_client = AzureOpenAI(
            azure_endpoint=openai_endpoint,
            api_version="2024-10-21",
            azure_ad_token_provider=lambda: credential.get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
        )

        self.openai_deployment = openai_deployment

        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=search_index,
            credential=DefaultAzureCredential(),
        )

        self.conversations: dict = {}

    async def chat(
        self,
        query: str,
        conversation_id: str | None = None,
    ) -> dict:
        """Process a chat query with RAG."""

        chat_start = time.perf_counter()
        CHAT_REQUESTS.inc()

        try:
            if conversation_id is None:
                conversation_id = str(uuid.uuid4())
                self.conversations[conversation_id] = []

            history = self.conversations.get(
                conversation_id,
                [],
            )

            embedding = await self._get_embedding(query)

            results = self._search_documents(
                embedding,
                query,
            )

            RETRIEVAL_RESULTS.set(len(results))

            source_counts: dict[str, int] = {}

            for result in results:
                source = result.get(
                    "source",
                    "unknown",
                )

                source_counts[source] = (
                    source_counts.get(source, 0) + 1
                )

            for source in (
                "argocd",
                "backstage",
                "kubernetes",
            ):
                DOCUMENTS_BY_SOURCE.labels(
                    source=source,
                ).set(
                    source_counts.get(source, 0)
                )

            context = self._build_context(results)

            CONTEXT_LENGTH.set(len(context))

            sources = [
                {
                    "id": result["id"],
                    "title": result.get("title", ""),
                    "score": result["@search.score"],
                }
                for result in results
            ]

            answer = await self._generate_response(
                query,
                context,
                history,
            )

            if not answer:
                CHAT_EMPTY_RESPONSES.inc()

            history.append(
                {
                    "role": "user",
                    "content": query,
                }
            )

            history.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )

            self.conversations[conversation_id] = history[-10:]

            CONVERSATION_HISTORY.set(
                len(self.conversations[conversation_id])
            )

            return {
                "answer": answer,
                "sources": sources,
                "conversation_id": conversation_id,
            }

        except Exception:
            CHAT_ERRORS.inc()
            logger.exception("RAG chat request failed")
            raise

        finally:
            CHAT_LATENCY.observe(
                time.perf_counter() - chat_start
            )

    async def _get_embedding(
        self,
        text: str,
    ) -> list[float]:
        """Generate embedding for text."""

        response = self.openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=text,
        )

        return response.data[0].embedding

    def _search_documents(
        self,
        embedding: list[float],
        query: str,
        top_k: int = 5,
    ) -> list:
        """Search for relevant operational documents."""

        query_lower = query.lower()

        source_filter = None
        resource_type = None

        # ---------------------------------------------------------
        # Source detection
        # ---------------------------------------------------------

        if "argocd" in query_lower:
            source_filter = "argocd"

        elif "backstage" in query_lower:
            source_filter = "backstage"

        elif "kubernetes" in query_lower:
            source_filter = "kubernetes"

        # ---------------------------------------------------------
        # Resource type detection
        # ---------------------------------------------------------

        if source_filter == "kubernetes":
            if any(term in query_lower for term in (
                "servicio",
                "servicios",
                "service",
                "services",
            )):
                resource_type = "service"

            elif any(term in query_lower for term in (
                "deployment",
                "deployments",
                "despliegue",
                "despliegues",
            )):
                resource_type = "deployment"

            elif any(term in query_lower for term in (
                "pod",
                "pods",
            )):
                resource_type = "pod"

            elif any(term in query_lower for term in (
                "namespace",
                "namespaces",
                "espacio de nombres",
            )):
                resource_type = "namespace"

        inventory_terms = (
            "qué aplicaciones",
            "que aplicaciones",
            "cuáles aplicaciones",
            "cuales aplicaciones",
            "todas las aplicaciones",
            "cada una",
            "inventario",
            "lista",
            "listar",
            "qué servicios",
            "que servicios",
            "cuáles servicios",
            "cuales servicios",
            "todos los servicios",
            "qué deployments",
            "que deployments",
            "qué pods",
            "que pods",
        )

        is_inventory_query = any(
            term in query_lower
            for term in inventory_terms
        )

        if is_inventory_query:
            top_k = max(top_k, 50)
        else:
            top_k = max(top_k, 10)

        retrieval_start = time.perf_counter()
        RETRIEVAL_REQUESTS.inc()

        vector_query = VectorizedQuery(
            vector=embedding,
            k_nearest_neighbors=top_k,
            fields="content_vector",
        )

        filter_expression = None

        if source_filter:
            filter_expression = (
                f"source eq '{source_filter}'"
            )

        try:
            results = self.search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                filter=filter_expression,
                select=[
                    "id",
                    "title",
                    "content",
                    "source",
                ],
                top=top_k,
            )

            results = list(results)

            # -----------------------------------------------------
            # Resource-level filtering
            #
            # resource_type is stored inside the serialized JSON
            # content, therefore filtering is performed locally.
            # -----------------------------------------------------

            if resource_type:
                filtered_results = []

                for result in results:
                    content = result.get("content", "")

                    try:
                        document = json.loads(content)
                    except (json.JSONDecodeError, TypeError):
                        document = {}

                    if (
                        document.get("resource_type")
                        == resource_type
                    ):
                        filtered_results.append(result)

                results = filtered_results

            RETRIEVAL_RESULTS.set(len(results))
            RETRIEVAL_DOCUMENTS.inc(len(results))

            return results

        finally:
            RETRIEVAL_LATENCY.observe(
                time.perf_counter() - retrieval_start
            )

    def _build_context(
        self,
        results: list,
    ) -> str:
        """Build context string from search results."""

        context_parts = []

        for index, result in enumerate(
            results,
            1,
        ):
            content = result.get(
                "content",
                "",
            )

            title = result.get(
                "title",
                f"Document {index}",
            )

            context_parts.append(
                f"[{index}] {title}:\n{content}\n"
            )

        return "\n".join(context_parts)

    async def _generate_response(
        self,
        query: str,
        context: str,
        history: list,
    ) -> str:
        """Generate response using Azure OpenAI."""

        system_prompt = (
            "You are an operational assistant for the Open Horizons "
            "engineering platform. "
            "Answer only from the provided context. "
            "Do not invent or assume information. "
            "Always cite factual statements using [1], [2], etc. "
            "corresponding to the context documents. "
            "\n\n"
            "When the user asks for a list, inventory, or status of "
            "multiple resources, enumerate all relevant resources "
            "available in the context. "
            "Do not return only one example when multiple matching "
            "resources are present. "
            "\n\n"
            "When information comes from different operational sources "
            "such as Backstage, ArgoCD, and Kubernetes, explain the "
            "relationship between them when relevant. "
            "\n\n"
            "If the context does not contain enough information to "
            "answer the question, say so clearly. "
            "Be concise, precise, and operationally useful."
        )

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question: {query}"
                ),
            },
        ]

        # Conversation history temporarily disabled during RAG validation.
        # Retrieval and answer generation must be deterministic.

        llm_start = time.perf_counter()
        LLM_REQUESTS.inc()

        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_deployment,
                messages=messages,
                max_completion_tokens=1000,
            )

            return response.choices[0].message.content

        except Exception:
            LLM_ERRORS.inc()
            logger.exception(
                "Azure OpenAI generation failed"
            )
            raise

        finally:
            LLM_LATENCY.observe(
                time.perf_counter() - llm_start
            )

    async def index_document(
        self,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> None:
        """Index a document for RAG."""

        logger.info(
            "Indexing document: %s",
            filename,
        )

        # Document processing and Azure AI Search
        # integration will be implemented in Phase 2.

    async def list_documents(self) -> list[dict]:
        """List indexed documents."""

        # Azure AI Search document listing will be
        # implemented in Phase 2.
        return []
