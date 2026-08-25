"""ArgoCD operational context collector."""

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

NAMESPACE = "argocd"
APPLICATION = "rag-application"


def kubernetes_get(path: str) -> dict[str, Any]:
    """Read a Kubernetes API resource using the pod ServiceAccount."""

    token = open(TOKEN_PATH).read().strip()

    request = urllib.request.Request(
        f"{API_SERVER}{path}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
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


def fetch_applications() -> list[dict[str, Any]]:
    """Fetch all ArgoCD Applications."""

    data = kubernetes_get(
        f"/apis/argoproj.io/v1alpha1"
        f"/namespaces/{NAMESPACE}/applications"
    )

    return data.get("items", [])


def fetch_application(
    name: str = APPLICATION,
) -> dict[str, Any]:
    """Fetch a single ArgoCD Application."""

    return kubernetes_get(
        f"/apis/argoproj.io/v1alpha1"
        f"/namespaces/{NAMESPACE}/applications/{name}"
    )


def normalize_application(
    app: dict[str, Any],
) -> dict[str, Any]:
    """Normalize an ArgoCD Application."""

    metadata = app.get("metadata", {})
    spec = app.get("spec", {})
    status = app.get("status", {})

    source = spec.get("source", {})
    destination = spec.get("destination", {})

    sync = status.get("sync", {})
    health = status.get("health", {})

    return {
        "id": (
            f"argocd:application:"
            f"{metadata.get('name')}"
        ),
        "source": "argocd",
        "application": metadata.get("name"),
        "project": spec.get("project"),
        "repository": source.get("repoURL"),
        "path": source.get("path"),
        "revision": source.get("targetRevision"),
        "resolved_revision": sync.get("revision"),
        "cluster": destination.get("server"),
        "namespace": destination.get("namespace"),
        "sync_status": sync.get("status"),
        "health_status": health.get("status"),
    }


def collect_applications() -> list[dict[str, Any]]:
    """Fetch and normalize all ArgoCD Applications."""

    applications = fetch_applications()

    return [
        normalize_application(application)
        for application in applications
    ]


if __name__ == "__main__":
    applications = collect_applications()

    print(
        json.dumps(
            applications,
            indent=2,
            ensure_ascii=False,
        )
    )
