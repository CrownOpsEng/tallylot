"""Render external output artifacts from stored facts."""

from __future__ import annotations

from tallylot.application.outputs.contracts import RenderOutputRequest, RenderOutputResponse
from tallylot.ports.adapter_contracts import AdapterCapability
from tallylot.ports.facts import FactRepositoryPort
from tallylot.ports.output_adapters import OutputAdapterRegistryPort


class RenderOutputUseCase:
    def __init__(self, registry: OutputAdapterRegistryPort, facts: FactRepositoryPort) -> None:
        self._registry = registry
        self._facts = facts

    def execute(self, request: RenderOutputRequest) -> RenderOutputResponse:
        facts = self._facts.read_facts(request.facts_path)
        adapter = self._registry.output_adapter(request.output_adapter)
        if not adapter.manifest.supported:
            raise ValueError(f"output adapter {adapter.manifest.adapter_id} is not supported for rendering")
        if AdapterCapability.OUTPUT_RENDER not in adapter.manifest.capabilities:
            raise ValueError(f"output adapter {adapter.manifest.adapter_id} does not declare render capability")
        artifact = adapter.render(facts, request.output_path)
        return RenderOutputResponse(output_path=artifact.path, row_count=artifact.row_count)
