import json
import subprocess
from typing import Any


DEPLOYMENT = "rag-application-demo1"
NAMESPACE = "default"
LABEL_SELECTOR = "app.kubernetes.io/name=rag-application-demo1"


def kubectl(*args: str) -> Any:
    result = subprocess.run(
        ["kubectl", *args],
        check=True,
        capture_output=True,
        text=True,
    )

    return json.loads(result.stdout)


def fetch_deployment() -> dict[str, Any]:
    return kubectl(
        "-n",
        NAMESPACE,
        "get",
        "deployment",
        DEPLOYMENT,
        "-o",
        "json",
    )


def fetch_pods() -> dict[str, Any]:
    return kubectl(
        "-n",
        NAMESPACE,
        "get",
        "pods",
        "-l",
        LABEL_SELECTOR,
        "-o",
        "json",
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

    document = normalize_runtime(deployment, pods)

    print(json.dumps(document, indent=2, ensure_ascii=False))
