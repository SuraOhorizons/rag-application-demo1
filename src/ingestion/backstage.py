import json
import urllib.request
from typing import Any


BACKSTAGE_URL = "https://backstage.nttdatacolombia.com"


def fetch_entities() -> list[dict[str, Any]]:
    url = f"{BACKSTAGE_URL}/api/catalog/entities"

    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def normalize_component(entity: dict[str, Any]) -> dict[str, Any]:
    metadata = entity.get("metadata", {})
    spec = entity.get("spec", {})

    return {
        "id": f"backstage:component:{metadata.get('namespace', 'default')}/{metadata.get('name')}",
        "source": "backstage",
        "kind": "Component",
        "name": metadata.get("name"),
        "description": metadata.get("description"),
        "type": spec.get("type"),
        "lifecycle": spec.get("lifecycle"),
        "owner": spec.get("owner"),
        "system": spec.get("system"),
        "tags": metadata.get("tags", []),
        "repository": metadata.get("annotations", {}).get(
            "github.com/project-slug"
        ),
        "argocd_app": metadata.get("annotations", {}).get(
            "argocd/app-name"
        ),
        "depends_on": spec.get("dependsOn", []),
        "provides_apis": spec.get("providesApis", []),
    }


def get_component(name: str) -> dict[str, Any] | None:
    entities = fetch_entities()

    for entity in entities:
        if (
            entity.get("kind") == "Component"
            and entity.get("metadata", {}).get("name") == name
        ):
            return normalize_component(entity)

    return None


if __name__ == "__main__":
    component = get_component("rag-application-demo1")

    if component is None:
        raise SystemExit("Component not found in Backstage")

    print(json.dumps(component, indent=2, ensure_ascii=False))
