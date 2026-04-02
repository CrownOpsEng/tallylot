"""Review adapter selection for staging workflows."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.domain.models import AdapterCapability
from crypto_reconciliation.ports.adapters import OutputAdapter, OutputAdapterRegistryPort
from crypto_reconciliation.ports.artifacts import ArtifactStorePort


def resolve_review_adapter(
    registry: OutputAdapterRegistryPort,
    candidate_path: Path,
    artifacts: ArtifactStorePort,
) -> OutputAdapter:
    matches = [
        (adapter.match_candidate(candidate_path, artifacts), adapter)
        for adapter in registry.output_adapters
        if adapter.manifest.supported and AdapterCapability.REVIEW in adapter.manifest.capabilities
    ]
    scored_matches = [(score, adapter) for score, adapter in matches if score > 0]
    if not scored_matches:
        raise ValueError(f"unable to detect supported output adapter for candidate {candidate_path}")
    scored_matches.sort(key=lambda item: item[0], reverse=True)
    best_score = scored_matches[0][0]
    best_adapters = [adapter for score, adapter in scored_matches if score == best_score]
    if len(best_adapters) > 1:
        adapter_ids = ", ".join(sorted(str(adapter.manifest.adapter_id) for adapter in best_adapters))
        raise ValueError(f"ambiguous output adapter for candidate {candidate_path}: {adapter_ids}")
    return best_adapters[0]
