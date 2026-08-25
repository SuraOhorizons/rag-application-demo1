"""RAG Service implementation."""

import logging
import uuid

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


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

        context = self._build_context(results)

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

        return {
            "answer": answer,
            "sources": sources,
            "conversation_id": conversation_id,
        }

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

        if "argocd" in query_lower:
            source_filter = "argocd"

        elif "backstage" in query_lower:
            source_filter = "backstage"

        elif "kubernetes" in query_lower:
            source_filter = "kubernetes"

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
        )

        is_inventory_query = any(
            term in query_lower
            for term in inventory_terms
        )

        if is_inventory_query and source_filter:
            top_k = 50
        else:
            top_k = max(top_k, 10)

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

        return list(results)

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

        for message in history[-4:]:
            messages.insert(
                -1,
                message,
            )

        response = self.openai_client.chat.completions.create(
            model=self.openai_deployment,
            messages=messages,
            max_completion_tokens=1000,
        )

        return response.choices[0].message.content

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
