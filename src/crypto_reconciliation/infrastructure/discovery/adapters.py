"""Auto-discovery for source and output adapters."""

from __future__ import annotations

import importlib
import importlib.util
import pkgutil
from collections.abc import Iterable
from dataclasses import dataclass
from types import ModuleType
from typing import cast

from pydantic import BaseModel, ConfigDict

from crypto_reconciliation.domain.models import AdapterCapability, AdapterManifest
from crypto_reconciliation.domain.types import AdapterId
from crypto_reconciliation.ports.adapters import OutputAdapter, SourceAdapter

DISCOVERABLE_MODULE_NAMES = ("adapter", "stub")
IGNORED_DISCOVERY_PARTS = frozenset({"tests", "fixtures", "__pycache__"})


class AdapterManifestModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    adapter_id: str
    display_name: str
    version: str
    capabilities: frozenset[AdapterCapability]
    supported: bool = True
    description: str = ""


@dataclass(frozen=True)
class AdapterRegistry:
    source_adapters: tuple[SourceAdapter, ...]
    output_adapters: tuple[OutputAdapter, ...]

    def source_adapter(self, adapter_id: str) -> SourceAdapter:
        for adapter in self.source_adapters:
            if str(adapter.manifest.adapter_id) == adapter_id:
                return adapter
        raise KeyError(f"unknown source adapter: {adapter_id}")

    def output_adapter(self, adapter_id: str) -> OutputAdapter:
        for adapter in self.output_adapters:
            if str(adapter.manifest.adapter_id) == adapter_id:
                return adapter
        raise KeyError(f"unknown output adapter: {adapter_id}")


def iter_discoverable_modules(package_name: str) -> tuple[ModuleType, ...]:
    package = importlib.import_module(package_name)
    modules: list[ModuleType] = []
    for package_info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if _is_ignored_discovery_name(package_info.name):
            continue
        if package_info.ispkg:
            modules.extend(_iter_adapter_package_modules(package_info.name))
            continue
        modules.append(importlib.import_module(package_info.name))
    return tuple(modules)


def _iter_adapter_package_modules(package_name: str) -> tuple[ModuleType, ...]:
    package = importlib.import_module(package_name)
    if getattr(package, "ADAPTER", None) is not None:
        return (package,)

    modules: list[ModuleType] = []
    for module_name in DISCOVERABLE_MODULE_NAMES:
        qualified_name = f"{package_name}.{module_name}"
        if importlib.util.find_spec(qualified_name) is None:
            continue
        modules.append(importlib.import_module(qualified_name))
    return tuple(modules)


def _is_ignored_discovery_name(module_name: str) -> bool:
    parts = module_name.split(".")
    return any(part in IGNORED_DISCOVERY_PARTS or part.startswith(("test_", "_")) for part in parts)


def _collect_source_adapters(package_name: str) -> tuple[SourceAdapter, ...]:
    discovered: list[SourceAdapter] = []
    for module in iter_discoverable_modules(package_name):
        adapter = getattr(module, "ADAPTER", None)
        if adapter is None:
            continue
        discovered.append(_validate_source_adapter_contract(adapter, module))
    _validate_unique_ids(discovered)
    return tuple(sorted(discovered, key=lambda item: str(item.manifest.adapter_id)))


def _collect_output_adapters(package_name: str) -> tuple[OutputAdapter, ...]:
    discovered: list[OutputAdapter] = []
    for module in iter_discoverable_modules(package_name):
        adapter = getattr(module, "ADAPTER", None)
        if adapter is None:
            continue
        discovered.append(_validate_output_adapter_contract(adapter, module))
    _validate_unique_ids(discovered)
    return tuple(sorted(discovered, key=lambda item: str(item.manifest.adapter_id)))


def _validated_manifest(raw_manifest: AdapterManifest) -> AdapterManifest:
    validated = AdapterManifestModel.model_validate(raw_manifest.__dict__)
    return AdapterManifest(
        adapter_id=AdapterId(validated.adapter_id),
        display_name=validated.display_name,
        version=validated.version,
        capabilities=validated.capabilities,
        supported=validated.supported,
        description=validated.description,
    )


def _validate_source_adapter_contract(adapter: object, module: ModuleType) -> SourceAdapter:
    manifest = _validated_manifest(_manifest_from_adapter(adapter, module))
    if AdapterCapability.NORMALIZE not in manifest.capabilities:
        raise ValueError(f"{module.__name__} adapter {manifest.adapter_id} must declare normalize capability")
    if AdapterCapability.OUTPUT_RENDER in manifest.capabilities:
        raise ValueError(f"{module.__name__} adapter {manifest.adapter_id} cannot declare output render capability")
    if not _has_callable(adapter, "match") or not _has_callable(adapter, "normalize"):
        raise TypeError(f"{module.__name__} ADAPTER does not implement the source adapter contract")
    return cast(SourceAdapter, adapter)


def _validate_output_adapter_contract(adapter: object, module: ModuleType) -> OutputAdapter:
    manifest = _validated_manifest(_manifest_from_adapter(adapter, module))
    if AdapterCapability.OUTPUT_RENDER not in manifest.capabilities:
        raise ValueError(f"{module.__name__} adapter {manifest.adapter_id} must declare output render capability")
    forbidden_capabilities = {
        AdapterCapability.NORMALIZE,
        AdapterCapability.WALLET_INVENTORY,
    }
    if manifest.capabilities.intersection(forbidden_capabilities):
        raise ValueError(f"{module.__name__} adapter {manifest.adapter_id} declares source-only capabilities")
    if not _has_callable(adapter, "render"):
        raise TypeError(f"{module.__name__} ADAPTER does not implement the output adapter contract")
    return cast(OutputAdapter, adapter)


def _manifest_from_adapter(adapter: object, module: ModuleType) -> AdapterManifest:
    manifest = getattr(adapter, "manifest", None)
    if not isinstance(manifest, AdapterManifest):
        raise TypeError(f"{module.__name__} ADAPTER is missing a valid AdapterManifest")
    return manifest


def _has_callable(adapter: object, attribute: str) -> bool:
    candidate = getattr(adapter, attribute, None)
    return callable(candidate)


def _validate_unique_ids(adapters: Iterable[SourceAdapter | OutputAdapter]) -> None:
    seen: set[str] = set()
    for adapter in adapters:
        adapter_id = str(adapter.manifest.adapter_id)
        if adapter_id in seen:
            raise ValueError(f"duplicate adapter_id discovered: {adapter_id}")
        seen.add(adapter_id)


def build_registry() -> AdapterRegistry:
    source_adapters = _collect_source_adapters("crypto_reconciliation.adapters.sources")
    output_adapters = _collect_output_adapters("crypto_reconciliation.adapters.outputs")
    _validate_unique_ids((*source_adapters, *output_adapters))
    return AdapterRegistry(
        source_adapters=source_adapters,
        output_adapters=output_adapters,
    )
