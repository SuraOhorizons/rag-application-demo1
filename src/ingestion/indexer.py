"""Operational context indexer."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

from .context import build_context


logger = logging.getLogger(__name__)


SEARCH_ENDPOINT = os.environ.get(
    "AZURE_SEARCH_ENDPOINT",
    "https://rag-application-demo1-search.search.windows.net",
)

SEARCH_INDEX = os.environ.get(
    "AZURE_SEARCH_INDEX",
    "documents",
)


def stable_id(
    prefix: str,
    value: str,
) -> str:
    """Generate a deterministic Azure AI Search document ID."""

    digest = hashlib.sha256(
        value.encode()
    ).hexdigest()[:16]

    return f"{prefix}_{digest}"


def serialize_content(
    data: dict[str, Any],
) -> str:
    """Serialize operational data into searchable text."""

    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        default=str,
    )


def build_documents(
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convert operational context into Search documents."""

    documents: list[dict[str, Any]] = []

    sources = context["sources"]

    # ---------------------------------------------------------
    # Backstage
    # ---------------------------------------------------------

    backstage = sources.get(
        "backstage",
        {},
    )

    entities = backstage.get(
        "entities",
        [],
    )

    for entity in entities:
        kind = entity.get(
            "kind",
            "Unknown",
        )

        name = entity.get(
            "name",
            "unknown",
        )

        documents.append(
            {
                "id": stable_id(
                    "backstage",
                    f"{kind}:{name}",
                ),
                "title": (
                    f"Backstage {kind} {name}"
                ),
                "content": serialize_content(
                    entity
                ),
                "source": "backstage",
            }
        )

    # ---------------------------------------------------------
    # ArgoCD
    # ---------------------------------------------------------

    argocd = sources.get(
        "argocd",
        {},
    )

    applications = argocd.get(
        "applications",
        [],
    )

    for application in applications:
        name = application.get(
            "application",
            "unknown",
        )

        documents.append(
            {
                "id": stable_id(
                    "argocd",
                    name,
                ),
                "title": (
                    f"ArgoCD Application {name}"
                ),
                "content": serialize_content(
                    application
                ),
                "source": "argocd",
            }
        )

    # ---------------------------------------------------------
    # Kubernetes
    # ---------------------------------------------------------

    kubernetes = sources.get(
        "kubernetes",
        {},
    )

    cluster = kubernetes.get(
        "cluster",
        {},
    )

    deployments = cluster.get(
        "deployments",
        [],
    )

    for deployment in deployments:
        namespace = deployment.get(
            "namespace",
            "unknown",
        )

        name = deployment.get(
            "name",
            "unknown",
        )

        documents.append(
            {
                "id": stable_id(
                    "kubernetes_deployment",
                    f"{namespace}/{name}",
                ),
                "title": (
                    f"Kubernetes Deployment "
                    f"{namespace}/{name}"
                ),
                "content": serialize_content(
                    deployment
                ),
                "source": "kubernetes",
            }
        )

    services = cluster.get(
        "services",
        [],
    )

    for service in services:
        namespace = service.get(
            "namespace",
            "unknown",
        )

        name = service.get(
            "name",
            "unknown",
        )

        documents.append(
            {
                "id": stable_id(
                    "kubernetes_service",
                    f"{namespace}/{name}",
                ),
                "title": (
                    f"Kubernetes Service "
                    f"{namespace}/{name}"
                ),
                "content": serialize_content(
                    service
                ),
                "source": "kubernetes",
            }
        )

    namespaces = cluster.get(
        "namespaces",
        [],
    )

    for namespace in namespaces:
        name = namespace.get(
            "name",
            "unknown",
        )

        documents.append(
            {
                "id": stable_id(
                    "kubernetes_namespace",
                    name,
                ),
                "title": (
                    f"Kubernetes Namespace {name}"
                ),
                "content": serialize_content(
                    namespace
                ),
                "source": "kubernetes",
            }
        )

    # ---------------------------------------------------------
    # Detailed RAG runtime
    # ---------------------------------------------------------

    runtime = kubernetes.get(
        "service_runtime"
    )

    if runtime:
        namespace = runtime.get(
            "namespace",
            "default",
        )

        deployment = runtime.get(
            "deployment",
            "rag-application-demo1",
        )

        documents.append(
            {
                "id": stable_id(
                    "kubernetes_runtime",
                    f"{namespace}/{deployment}",
                ),
                "title": (
                    f"Kubernetes Runtime "
                    f"{namespace}/{deployment}"
                ),
                "content": serialize_content(
                    runtime
                ),
                "source": "kubernetes",
            }
        )

    return documents


def index_documents(
    documents: list[dict[str, Any]],
) -> None:
    """Upload operational documents to Azure AI Search."""

    if not documents:
        logger.warning(
            "No documents generated"
        )
        return

    credential = DefaultAzureCredential()

    client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX,
        credential=credential,
    )

    result = client.upload_documents(
        documents=documents
    )

    succeeded = 0
    failed = 0

    for item in result:
        key = item.key
        success = item.succeeded

        if success:
            succeeded += 1
        else:
            failed += 1

        logger.info(
            "Indexed %s: %s",
            key,
            success,
        )

    print(
        f"Azure AI Search: "
        f"{succeeded} succeeded, "
        f"{failed} failed"
    )


def main() -> None:
    """Build and index operational context."""

    context = build_context()

    documents = build_documents(
        context
    )

    print(
        f"Operational documents: "
        f"{len(documents)}"
    )

    counters: dict[str, int] = {}

    for document in documents:
        source = document["source"]

        counters[source] = (
            counters.get(source, 0) + 1
        )

    print("Documents by source:")

    for source, count in sorted(
        counters.items()
    ):
        print(
            f"- {source}: {count}"
        )

    print()
    print("Documents:")

    for document in documents:
        print(
            f"- {document['id']} "
            f"[{document['source']}] "
            f"{document['title']}"
        )

    print()
    print("Indexing operational context...")

    index_documents(
        documents
    )

    print(
        "Indexing completed."
    )


if __name__ == "__main__":
    main()
