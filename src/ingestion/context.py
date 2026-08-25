"""Build operational context for the RAG index."""

from __future__ import annotations

import json

from .argocd import collect_applications
from .backstage import collect_entities, get_component
from .kubernetes import (
    collect_cluster_context,
    fetch_deployment,
    fetch_pods,
    normalize_runtime,
)


COMPONENT = "rag-application-demo1"


def build_context() -> dict:
    """Build global and application-specific context."""

    backstage_entities = collect_entities()

    backstage_component = get_component(
        COMPONENT
    )

    if backstage_component is None:
        raise RuntimeError(
            f"Component '{COMPONENT}' not found in Backstage"
        )

    argocd_applications = collect_applications()

    deployment = fetch_deployment()
    pods = fetch_pods()

    rag_runtime = normalize_runtime(
        deployment,
        pods,
    )

    kubernetes_cluster = (
        collect_cluster_context()
    )

    return {
        "service": COMPONENT,
        "sources": {
            "backstage": {
                "entities": backstage_entities,
                "component": backstage_component,
            },
            "argocd": {
                "applications": argocd_applications,
            },
            "kubernetes": {
                "cluster": kubernetes_cluster,
                "service_runtime": rag_runtime,
            },
        },
    }


if __name__ == "__main__":
    print(
        json.dumps(
            build_context(),
            indent=2,
            ensure_ascii=False,
        )
    )
