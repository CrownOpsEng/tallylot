"""Detail-output refresh helpers for target-product execution."""

from __future__ import annotations

from json import JSONDecodeError
from pathlib import Path
from typing import Protocol

from tallylot.application.compatibility.checkpoints import (
    ObservationCompatibilityDetail,
    project_balance_references_from_checkpoint,
)
from tallylot.application.compatibility.economic_facts import (
    EconomicFactsCompatibilityArtifacts,
    project_compatibility_artifacts_from_economic_facts,
)
from tallylot.application.compatibility.reconciliation_states import (
    project_balance_snapshots_from_reconciliation_state,
)
from tallylot.domain.balances import BalanceReference, BalanceSnapshot
from tallylot.domain.checkpoint import Checkpoint
from tallylot.domain.claim import ClaimSet
from tallylot.domain.economics import EconomicFacts
from tallylot.domain.evidence import EvidenceSet
from tallylot.domain.reconciliation import ReconciliationState
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import EvidenceRepositoryPort
from tallylot.ports.facts import FactRepositoryPort

from ..translation import TranslationExecutionResult

DETAIL_READ_EXCEPTIONS = (JSONDecodeError, OSError, KeyError, TypeError, ValueError)


class _EconomicFactsDependenciesProtocol(Protocol):
    @property
    def facts(self) -> FactRepositoryPort: ...

    @property
    def artifacts(self) -> ArtifactStorePort: ...


class _EvidenceDependenciesProtocol(Protocol):
    @property
    def evidence(self) -> EvidenceRepositoryPort: ...


class EconomicFactsRefreshRequestProtocol(Protocol):
    @property
    def claim_set(self) -> ClaimSet: ...

    @property
    def evidence_set(self) -> EvidenceSet: ...

    @property
    def translation_result(self) -> TranslationExecutionResult: ...

    @property
    def dependencies(self) -> _EconomicFactsDependenciesProtocol: ...


class ReconciliationStateRefreshRequestProtocol(Protocol):
    @property
    def dependencies(self) -> _EvidenceDependenciesProtocol: ...


class CheckpointRefreshRequestProtocol(Protocol):
    @property
    def reconciliation_states(self) -> tuple[ReconciliationState, ...]: ...

    @property
    def dependencies(self) -> _EvidenceDependenciesProtocol: ...


def refresh_economic_facts_compatibility(
    *,
    request: EconomicFactsRefreshRequestProtocol,
    economic_facts: EconomicFacts,
    facts_path: Path,
    annotations_path: Path,
) -> EconomicFactsCompatibilityArtifacts:
    compatibility = project_compatibility_artifacts_from_economic_facts(
        economic_facts=economic_facts,
        claim_set=request.claim_set,
        evidence_set=request.evidence_set,
        draft_projection_field_records=request.translation_result.draft_projection_field_records,
    )
    request.dependencies.facts.write_facts(
        facts_path,
        compatibility.facts,
    )
    request.dependencies.artifacts.write_json(
        annotations_path,
        [record.to_json() for record in compatibility.fact_annotations],
    )
    return compatibility


def refresh_reconciliation_state_snapshots(
    *,
    request: ReconciliationStateRefreshRequestProtocol,
    state: ReconciliationState,
    snapshot_path: Path,
) -> tuple[BalanceSnapshot, ...]:
    projected_snapshots = project_balance_snapshots_from_reconciliation_state(state)
    request.dependencies.evidence.write_balance_snapshots(
        snapshot_path,
        projected_snapshots,
    )
    return projected_snapshots


def refresh_checkpoint_references(
    *,
    request: CheckpointRefreshRequestProtocol,
    checkpoint: Checkpoint,
    observation_details: dict[str, ObservationCompatibilityDetail],
    reference_path: Path,
) -> tuple[BalanceReference, ...]:
    projected_references = project_balance_references_from_checkpoint(
        checkpoint=checkpoint,
        reconciliation_states=request.reconciliation_states,
        observation_details=observation_details,
    )
    request.dependencies.evidence.write_balance_references(
        reference_path,
        projected_references,
    )
    return projected_references
