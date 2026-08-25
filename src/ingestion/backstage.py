"""Backstage operational context collector."""

from __future__ import annotations

import json
import urllib.request
from typing import Any


BACKSTAGE_URL = "https://backstage.nttdatacolombia.com"


def fetch_entities() -> list[dict[str, Any]]:
    """Fetch all Backstage catalog entities."""

    url = f"{BACKSTAGE_URL}/api/catalog/entities"

    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        return json.loads(
            response.read().decode()
        )


def normalize_entity(
    entity: dict[str, Any],
) -> dict[str, Any]:
    """Normalize a Backstage catalog entity."""

    metadata = entity.get("metadata", {})
    spec = entity.get("spec", {})

    annotations = metadata.get(
        "annotations",
        {},
    )

    return {
        "id": (
            f"backstage:"
            f"{metadata.get('namespace', 'default')}:"
            f"{entity.get('kind', 'Unknown')}:"
            f"{metadata.get('name')}"
        ),
        "source": "backstage",
        "kind": entity.get("kind"),
        "namespace": metadata.get(
            "namespace",
            "default",
        ),
        "name": metadata.get("name"),
        "description": metadata.get("description"),
        "type": spec.get("type"),
        "lifecycle": spec.get("lifecycle"),
        "owner": spec.get("owner"),
        "system": spec.get("system"),
        "tags": metadata.get("tags", []),
        "repository": annotations.get(
            "github.com/project-slug"
        ),
        "argocd_app": annotations.get(
            "argocd/app-name"
        ),
        "depends_on": spec.get(
            "dependsOn",
            [],
        ),
        "provides_apis": spec.get(
            "providesApis",
            [],
        ),
    }


def collect_entities() -> list[dict[str, Any]]:
    """Fetch and normalize all Backstage entities."""

    return [
        normalize_entity(entity)
        for entity in fetch_entities()
    ]


def get_component(
    name: str,
) -> dict[str, Any] | None:
    """Get a specific Backstage Component."""

    for entity in collect_entities():
        if (
            entity.get("kind") == "Component"
            and entity.get("name") == name
        ):
            return entity

    return None


if __name__ == "__main__":
    entities = collect_entities()

    print(
        json.dumps(
            entities,
            indent=2,
            ensure_ascii=False,
        )
    )
