"""Adapter contract validation."""

from __future__ import annotations

from collections.abc import Iterable
from types import ModuleType
from typing import cast

from crypto_reconciliation.domain.models import AdapterCapability, AdapterManifest
from crypto_reconciliation.ports.adapters import OutputAdapter, SourceAdapter

from .manifest import validated_manifest


def validate_source_adapter_contract(adapter: object, module: ModuleType) -> SourceAdapter:
    manifest = validated_manifest(manifest_from_adapter(adapter, module))
    source_capabilities = {
        AdapterCapability.INTAKE_ROUTE,
        AdapterCapability.NORMALIZE,
        AdapterCapability.WALLET_INVENTORY,
    }
    if not manifest.capabilities.intersection(source_capabilities):
        raise ValueError(
            f"{module.__name__} adapter {manifest.adapter_id} must declare intake route, normalize, "
            "or wallet inventory capability"
        )
    if AdapterCapability.OUTPUT_RENDER in manifest.capabilities:
        raise ValueError(f"{module.__name__} adapter {manifest.adapter_id} cannot declare output render capability")
    required_methods = (
        "match",
        "match_intake",
        "route_intake",
        "validate_profile_timezones",
        "extract_wallet_inventory",
        "normalize",
    )
    if not all(has_callable(adapter, method_name) for method_name in required_methods):
        raise TypeError(f"{module.__name__} ADAPTER does not implement the source adapter contract")
    return cast(SourceAdapter, adapter)


def validate_output_adapter_contract(adapter: object, module: ModuleType) -> OutputAdapter:
    manifest = validated_manifest(manifest_from_adapter(adapter, module))
    if AdapterCapability.OUTPUT_RENDER not in manifest.capabilities:
        raise ValueError(f"{module.__name__} adapter {manifest.adapter_id} must declare output render capability")
    forbidden_capabilities = {
        AdapterCapability.NORMALIZE,
        AdapterCapability.WALLET_INVENTORY,
    }
    if manifest.capabilities.intersection(forbidden_capabilities):
        raise ValueError(f"{module.__name__} adapter {manifest.adapter_id} declares source-only capabilities")
    if not has_callable(adapter, "render"):
        raise TypeError(f"{module.__name__} ADAPTER does not implement the output adapter contract")
    return cast(OutputAdapter, adapter)


def manifest_from_adapter(adapter: object, module: ModuleType) -> AdapterManifest:
    manifest = getattr(adapter, "manifest", None)
    if not isinstance(manifest, AdapterManifest):
        raise TypeError(f"{module.__name__} ADAPTER is missing a valid AdapterManifest")
    return manifest


def has_callable(adapter: object, attribute: str) -> bool:
    candidate = getattr(adapter, attribute, None)
    return callable(candidate)


def validate_unique_ids(adapters: Iterable[SourceAdapter | OutputAdapter]) -> None:
    seen: set[str] = set()
    for adapter in adapters:
        adapter_id = str(adapter.manifest.adapter_id)
        if adapter_id in seen:
            raise ValueError(f"duplicate adapter_id discovered: {adapter_id}")
        seen.add(adapter_id)
