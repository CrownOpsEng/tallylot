"""Runtime adapter registry assembly."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.ports.output_adapters import OutputAdapter
from tallylot.ports.source_adapters import SourceAdapter

from .contracts import (
    validate_output_adapter_contract,
    validate_source_adapter_contract,
    validate_unique_ids,
)
from .modules import iter_discoverable_modules


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


def _collect_source_adapters(package_name: str) -> tuple[SourceAdapter, ...]:
    discovered: list[SourceAdapter] = []
    for module in iter_discoverable_modules(package_name):
        adapter = getattr(module, "ADAPTER", None)
        if adapter is None:
            continue
        discovered.append(validate_source_adapter_contract(adapter, module))
    validate_unique_ids(discovered)
    return tuple(sorted(discovered, key=lambda item: str(item.manifest.adapter_id)))


def _collect_output_adapters(package_name: str) -> tuple[OutputAdapter, ...]:
    discovered: list[OutputAdapter] = []
    for module in iter_discoverable_modules(package_name):
        adapter = getattr(module, "ADAPTER", None)
        if adapter is None:
            continue
        discovered.append(validate_output_adapter_contract(adapter, module))
    validate_unique_ids(discovered)
    return tuple(sorted(discovered, key=lambda item: str(item.manifest.adapter_id)))


def build_registry() -> AdapterRegistry:
    source_adapters = _collect_source_adapters("tallylot.adapters.sources")
    output_adapters = _collect_output_adapters("tallylot.adapters.outputs")
    validate_unique_ids((*source_adapters, *output_adapters))
    return AdapterRegistry(
        source_adapters=source_adapters,
        output_adapters=output_adapters,
    )
