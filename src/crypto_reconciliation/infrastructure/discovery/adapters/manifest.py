"""Discovery-time manifest validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from crypto_reconciliation.domain.models import AdapterCapability, AdapterManifest
from crypto_reconciliation.domain.types import AdapterId


class AdapterManifestModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    adapter_id: str
    display_name: str
    version: str
    capabilities: frozenset[AdapterCapability]
    supported: bool = True
    description: str = ""


def validated_manifest(raw_manifest: AdapterManifest) -> AdapterManifest:
    validated = AdapterManifestModel.model_validate(raw_manifest.__dict__)
    return AdapterManifest(
        adapter_id=AdapterId(validated.adapter_id),
        display_name=validated.display_name,
        version=validated.version,
        capabilities=validated.capabilities,
        supported=validated.supported,
        description=validated.description,
    )
