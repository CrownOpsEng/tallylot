"""Discovery-time manifest validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from tallylot.domain.types import AdapterId
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest


class AdapterManifestModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    adapter_id: str
    display_name: str
    version: str
    capabilities: frozenset[AdapterCapability]
    supported: bool = True
    description: str = ""


def validated_manifest(raw_manifest: object) -> AdapterManifest:
    validated = AdapterManifestModel.model_validate(vars(raw_manifest))
    return AdapterManifest(
        adapter_id=AdapterId(validated.adapter_id),
        display_name=validated.display_name,
        version=validated.version,
        capabilities=validated.capabilities,
        supported=validated.supported,
        description=validated.description,
    )
