import json
import os
import ssl
import urllib.request
from typing import Any


API_SERVER = "https://kubernetes.default.svc"
TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

DEPLOYMENT = "rag-application-demo1"
NAMESPACE = "default"
LABEL_SELECTOR = "app.kubernetes.io/name=rag-application-demo1"


def kubernetes_get(path: str) -> dict[str, Any]:
    token = open(TOKEN_PATH).read().strip()

    request = urllib.request.Request(
        f"{API_SERVER}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )

    context = ssl.create_default_context(cafile=CA_PATH)

    with urllib.request.urlopen(
        request,
        context=context,
        timeout=10,
    ) as response:
        return json.loads(response.read().decode())


def fetch_deployment() -> dict[str, Any]:
    return kubernetes_get(
        f"/apis/apps/v1/namespaces/{NAMESPACE}/deployments/{DEPLOYMENT}"
    )


def fetch_pods() -> dict[str, Any]:
    return kubernetes_get(
        f"/api/v1/namespaces/{NAMESPACE}/pods"
        f"?labelSelector={LABEL_SELECTOR}"
    )


def normalize_runtime(
    deployment: dict[str, Any],
    pods: dict[str, Any],
) -> dict[str, Any]:

    deployment_spec = deployment.get("spec", {})
    deployment_status = deployment.get("status", {})

    containers = (
        deployment_spec
        .get("template", {})
        .get("spec", {})
        .get("containers", [])
    )

    image = containers[0].get("image") if containers else None

    normalized_pods = []

    for pod in pods.get("items", []):
        metadata = pod.get("metadata", {})
        status = pod.get("status", {})

        normalized_pods.append(
            {
                "name": metadata.get("name"),
                "status": status.get("phase"),
                "ip": status.get("podIP"),
                "node": pod.get("spec", {}).get("nodeName"),
            }
        )

    return {
        "id": f"kubernetes:deployment:{NAMESPACE}/{DEPLOYMENT}",
        "source": "kubernetes",
        "deployment": DEPLOYMENT,
        "namespace": NAMESPACE,
        "replicas": deployment_spec.get("replicas", 0),
        "available_replicas": deployment_status.get(
            "availableReplicas", 0
        ),
        "ready_replicas": deployment_status.get(
            "readyReplicas", 0
        ),
        "image": image,
        "pods": normalized_pods,
    }


if __name__ == "__main__":
    deployment = fetch_deployment()
    pods = fetch_pods()

    document = normalize_runtime(
        deployment,
        pods,
    )

    print(
        json.dumps(
            document,
            indent=2,
            ensure_ascii=False,
        )
    )
