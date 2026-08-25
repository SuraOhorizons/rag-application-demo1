"""Kubernetes operational context collector."""

from __future__ import annotations

import json
import ssl
import urllib.request
from typing import Any


API_SERVER = "https://kubernetes.default.svc"

TOKEN_PATH = (
    "/var/run/secrets/kubernetes.io/serviceaccount/token"
)

CA_PATH = (
    "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
)

DEPLOYMENT = "rag-application-demo1"
NAMESPACE = "default"

LABEL_SELECTOR = (
    "app.kubernetes.io/name=rag-application-demo1"
)


def kubernetes_get(
    path: str,
) -> dict[str, Any]:
    """Read a Kubernetes API resource."""

    token = open(
        TOKEN_PATH
    ).read().strip()

    request = urllib.request.Request(
        f"{API_SERVER}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )

    context = ssl.create_default_context(
        cafile=CA_PATH
    )

    with urllib.request.urlopen(
        request,
        context=context,
        timeout=10,
    ) as response:
        return json.loads(
            response.read().decode()
        )


def fetch_deployment() -> dict[str, Any]:
    """Fetch the RAG deployment."""

    return kubernetes_get(
        f"/apis/apps/v1/namespaces/"
        f"{NAMESPACE}/deployments/{DEPLOYMENT}"
    )


def fetch_pods() -> dict[str, Any]:
    """Fetch RAG pods."""

    return kubernetes_get(
        f"/api/v1/namespaces/{NAMESPACE}/pods"
        f"?labelSelector={LABEL_SELECTOR}"
    )


def fetch_deployments() -> list[dict[str, Any]]:
    """Fetch all cluster deployments."""

    data = kubernetes_get(
        "/apis/apps/v1/deployments"
    )

    return data.get(
        "items",
        [],
    )


def fetch_services() -> list[dict[str, Any]]:
    """Fetch all cluster services."""

    data = kubernetes_get(
        "/api/v1/services"
    )

    return data.get(
        "items",
        [],
    )


def fetch_pods_all() -> list[dict[str, Any]]:
    """Fetch all cluster pods."""

    data = kubernetes_get(
        "/api/v1/pods"
    )

    return data.get(
        "items",
        [],
    )


def fetch_namespaces() -> list[dict[str, Any]]:
    """Fetch all cluster namespaces."""

    data = kubernetes_get(
        "/api/v1/namespaces"
    )

    return data.get(
        "items",
        [],
    )


def normalize_deployment(
    deployment: dict[str, Any],
) -> dict[str, Any]:
    """Normalize a Kubernetes Deployment."""

    metadata = deployment.get(
        "metadata",
        {},
    )

    spec = deployment.get(
        "spec",
        {},
    )

    status = deployment.get(
        "status",
        {},
    )

    containers = (
        spec
        .get("template", {})
        .get("spec", {})
        .get("containers", [])
    )

    images = [
        container.get("image")
        for container in containers
    ]

    namespace = metadata.get(
        "namespace"
    )

    name = metadata.get(
        "name"
    )

    return {
        "id": (
            f"kubernetes:deployment:"
            f"{namespace}/{name}"
        ),
        "source": "kubernetes",
        "resource_type": "deployment",
        "name": name,
        "namespace": namespace,
        "replicas": spec.get(
            "replicas",
            0,
        ),
        "available_replicas": status.get(
            "availableReplicas",
            0,
        ),
        "ready_replicas": status.get(
            "readyReplicas",
            0,
        ),
        "images": images,
    }


def normalize_service(
    service: dict[str, Any],
) -> dict[str, Any]:
    """Normalize a Kubernetes Service."""

    metadata = service.get(
        "metadata",
        {}
    )

    spec = service.get(
        "spec",
        {}
    )

    namespace = metadata.get(
        "namespace"
    )

    name = metadata.get(
        "name"
    )

    return {
        "id": (
            f"kubernetes:service:"
            f"{namespace}/{name}"
        ),
        "source": "kubernetes",
        "resource_type": "service",
        "name": name,
        "namespace": namespace,
        "type": spec.get(
            "type"
        ),
        "cluster_ip": spec.get(
            "clusterIP"
        ),
        "selector": spec.get(
            "selector",
            {},
        ),
        "ports": spec.get(
            "ports",
            [],
        ),
    }


def normalize_pod(
    pod: dict[str, Any],
) -> dict[str, Any]:
    """Normalize a Kubernetes Pod."""

    metadata = pod.get(
        "metadata",
        {}
    )

    spec = pod.get(
        "spec",
        {}
    )

    status = pod.get(
        "status",
        {}
    )

    namespace = metadata.get(
        "namespace"
    )

    name = metadata.get(
        "name"
    )

    return {
        "id": (
            f"kubernetes:pod:"
            f"{namespace}/{name}"
        ),
        "source": "kubernetes",
        "resource_type": "pod",
        "name": name,
        "namespace": namespace,
        "status": status.get(
            "phase"
        ),
        "pod_ip": status.get(
            "podIP"
        ),
        "node": spec.get(
            "nodeName"
        ),
        "owner_references": [
            ref.get("name")
            for ref in metadata.get(
                "ownerReferences",
                [],
            )
        ],
    }


def normalize_namespace(
    namespace: dict[str, Any],
) -> dict[str, Any]:
    """Normalize a Kubernetes Namespace."""

    metadata = namespace.get(
        "metadata",
        {}
    )

    name = metadata.get(
        "name"
    )

    return {
        "id": (
            f"kubernetes:namespace:{name}"
        ),
        "source": "kubernetes",
        "resource_type": "namespace",
        "name": name,
        "status": namespace.get(
            "status",
            {},
        ).get(
            "phase"
        ),
    }


def normalize_runtime(
    deployment: dict[str, Any],
    pods: dict[str, Any],
) -> dict[str, Any]:
    """Normalize the RAG application runtime."""

    normalized_deployment = normalize_deployment(
        deployment
    )

    normalized_pods = [
        normalize_pod(pod)
        for pod in pods.get(
            "items",
            [],
        )
    ]

    normalized_deployment["pods"] = normalized_pods

    return normalized_deployment


def collect_cluster_context() -> dict[str, list[dict[str, Any]]]:
    """Collect cluster-wide Kubernetes context."""

    return {
        "deployments": [
            normalize_deployment(item)
            for item in fetch_deployments()
        ],
        "services": [
            normalize_service(item)
            for item in fetch_services()
        ],
        "pods": [
            normalize_pod(item)
            for item in fetch_pods_all()
        ],
        "namespaces": [
            normalize_namespace(item)
            for item in fetch_namespaces()
        ],
    }


if __name__ == "__main__":
    context = collect_cluster_context()

    print(
        json.dumps(
            context,
            indent=2,
            ensure_ascii=False,
        )
    )
