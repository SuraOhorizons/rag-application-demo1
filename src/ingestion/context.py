import json

from backstage import get_component
from argocd import fetch_application, normalize_application
from kubernetes import fetch_deployment, fetch_pods, normalize_runtime


COMPONENT = "rag-application-demo1"


def build_context() -> dict:
    backstage = get_component(COMPONENT)

    if backstage is None:
        raise RuntimeError(
            f"Component '{COMPONENT}' not found in Backstage"
        )

    argocd = normalize_application(fetch_application())

    deployment = fetch_deployment()
    pods = fetch_pods()

    kubernetes = normalize_runtime(deployment, pods)

    return {
        "service": COMPONENT,
        "sources": {
            "backstage": backstage,
            "argocd": argocd,
            "kubernetes": kubernetes,
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
