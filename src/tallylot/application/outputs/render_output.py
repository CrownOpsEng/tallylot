"""Render external output artifacts from stored facts."""

from __future__ import annotations

from tallylot.application.outputs.contracts import RenderOutputRequest, RenderOutputResponse
from tallylot.domain.transactions import LegKind, TransactionFact
from tallylot.ports.adapter_contracts import AdapterCapability
from tallylot.ports.facts import FactRepositoryPort
from tallylot.ports.output_adapters import OutputAdapter, OutputAdapterRegistryPort, OutputRenderPolicy


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
        _validate_render_policy(facts, adapter=adapter)
        artifact = adapter.render(facts, request.output_path)
        return RenderOutputResponse(output_path=artifact.path, row_count=artifact.row_count)


def _validate_render_policy(facts: tuple[TransactionFact, ...], *, adapter: OutputAdapter) -> None:
    adapter_id = str(adapter.manifest.adapter_id)
    policy = adapter.render_policy
    for fact in facts:
        if policy.requires_projection_type and fact.projection_type is None:
            raise ValueError(f"fact {fact.fact_id} is missing required {adapter_id} projection metadata")
        counts_by_kind: dict[LegKind, int] = {}
        directional_counts: dict[tuple[LegKind, str], int] = {}
        for leg in fact.legs:
            counts_by_kind[leg.kind] = counts_by_kind.get(leg.kind, 0) + 1
            directional_key = (leg.kind, leg.direction)
            directional_counts[directional_key] = directional_counts.get(directional_key, 0) + 1
        _validate_fact_shape(
            fact=fact,
            policy=policy,
            adapter_id=adapter_id,
            counts_by_kind=counts_by_kind,
            directional_counts=directional_counts,
        )


def _validate_fact_shape(
    *,
    fact: TransactionFact,
    policy: OutputRenderPolicy,
    adapter_id: str,
    counts_by_kind: dict[LegKind, int],
    directional_counts: dict[tuple[LegKind, str], int],
) -> None:
    for kind, count in counts_by_kind.items():
        limit = policy.shape_policy.limit_for(kind)
        if limit is None:
            raise ValueError(f"fact {fact.fact_id} has unsupported {adapter_id} render leg kind: {kind.value}")
        if count > limit.max_count:
            raise ValueError(f"fact {fact.fact_id} exceeds {adapter_id} render policy for {kind.value} legs")
        inbound_count = directional_counts.get((kind, "in"), 0)
        outbound_count = directional_counts.get((kind, "out"), 0)
        if limit.max_in_count is not None and inbound_count > limit.max_in_count:
            raise ValueError(f"fact {fact.fact_id} exceeds {adapter_id} render policy for inbound {kind.value} legs")
        if limit.max_out_count is not None and outbound_count > limit.max_out_count:
            raise ValueError(f"fact {fact.fact_id} exceeds {adapter_id} render policy for outbound {kind.value} legs")
