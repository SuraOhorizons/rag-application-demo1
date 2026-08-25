import json
import ssl
import urllib.request
from typing import Any


APPLICATION = "rag-application"
NAMESPACE = "argocd"


def fetch_application() -> dict[str, Any]:
    token = open(
        "/var/run/secrets/kubernetes.io/serviceaccount/token"
    ).read().strip()

    url = (
        "https://kubernetes.default.svc"
        f"/apis/argoproj.io/v1alpha1"
        f"/namespaces/{NAMESPACE}/applications/{APPLICATION}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )

    context = ssl.create_default_context(
        cafile="/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
    )

    with urllib.request.urlopen(
        request,
        context=context,
        timeout=10,
    ) as response:
        return json.loads(response.read().decode())


def normalize_application(app: dict[str, Any]) -> dict[str, Any]:
    metadata = app.get("metadata", {})
    spec = app.get("spec", {})
    status = app.get("status", {})

    source = spec.get("source", {})
    destination = spec.get("destination", {})

    return {
        "id": f"argocd:application:{metadata.get('name')}",
        "source": "argocd",
        "application": metadata.get("name"),
        "project": spec.get("project"),
        "repository": source.get("repoURL"),
        "path": source.get("path"),
        "revision": source.get("targetRevision"),
        "resolved_revision": status.get("sync", {}).get("revision"),
        "cluster": destination.get("server"),
        "namespace": destination.get("namespace"),
        "sync_status": status.get("sync", {}).get("status"),
        "health_status": status.get("health", {}).get("status"),
    }


if __name__ == "__main__":
    application = fetch_application()
    document = normalize_application(application)

    print(json.dumps(document, indent=2, ensure_ascii=False))
