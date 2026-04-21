"""Target-product runtime execution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from tallylot.application.capture_paths import (
    checkpoint_compatibility_references_file,
    checkpoint_product_file,
    checkpoint_ref,
    economic_facts_compatibility_fact_annotations_file,
    economic_facts_compatibility_facts_file,
    economic_facts_product_file,
    economic_facts_ref,
    reconciliation_state_compatibility_snapshots_file,
    reconciliation_state_product_file,
    reconciliation_state_ref,
)
from tallylot.application.checkpoint import build_checkpoints
from tallylot.application.compatibility.checkpoints import (
    observation_details_from_evidence_set,
    project_balance_references_from_checkpoint,
)
from tallylot.application.compatibility.economic_facts import (
    EconomicFactsCompatibilityArtifacts,
    project_compatibility_artifacts_from_economic_facts,
)
from tallylot.application.compatibility.reconciliation_states import (
    project_balance_snapshots_from_reconciliation_state,
)
from tallylot.application.economics import build_economic_facts
from tallylot.application.normalization.contracts import NormalizeUpdateMode
from tallylot.application.normalization.translation import TranslationExecutionResult
from tallylot.application.reconciliation import build_reconciliation_states
from tallylot.domain.balances import BalanceReference, BalanceSnapshot
from tallylot.domain.checkpoint import Checkpoint, checkpoint_fingerprint
from tallylot.domain.claim import ClaimSet
from tallylot.domain.economics import EconomicFacts, economic_facts_fingerprint
from tallylot.domain.evidence import EvidenceSet
from tallylot.domain.reconciliation import (
    ReconciliationState,
    reconciliation_state_fingerprint,
)
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.checkpoints import CheckpointRepositoryPort
from tallylot.ports.economic_facts import EconomicFactsRepositoryPort
from tallylot.ports.evidence import EvidenceRepositoryPort
from tallylot.ports.facts import FactRepositoryPort
from tallylot.ports.reconciliation_states import ReconciliationStateRepositoryPort

from .models import (
    CheckpointExecutionDecision,
    EconomicFactsExecutionDecision,
    ReconciliationStateExecutionDecision,
    TargetProductExecutionPlan,
    TargetProductStageAction,
)
from .payloads import (
    read_fact_annotations,
    reference_rows_signature,
    snapshot_rows_signature,
)
from .signatures import (
    checkpoint_reference_signature,
    economic_facts_compatibility_signature,
)


class TargetProductDependenciesProtocol(Protocol):
    @property
    def facts(self) -> FactRepositoryPort: ...

    @property
    def evidence(self) -> EvidenceRepositoryPort: ...

    @property
    def economic_facts(self) -> EconomicFactsRepositoryPort: ...

    @property
    def reconciliation_states(self) -> ReconciliationStateRepositoryPort: ...

    @property
    def checkpoints(self) -> CheckpointRepositoryPort: ...

    @property
    def artifacts(self) -> ArtifactStorePort: ...


@dataclass(frozen=True)
class EconomicFactsResolutionRequest:
    workspace_root: Path
    update_mode: NormalizeUpdateMode
    claim_set: ClaimSet
    claim_set_fingerprint: str
    evidence_set: EvidenceSet
    translation_result: TranslationExecutionResult
    prior_plan: TargetProductExecutionPlan | None
    dependencies: TargetProductDependenciesProtocol


@dataclass(frozen=True)
class ReconciliationStateResolutionRequest:
    workspace_root: Path
    update_mode: NormalizeUpdateMode
    claim_set: ClaimSet
    claim_set_fingerprint: str
    evidence_set: EvidenceSet
    economic_facts: EconomicFacts
    economic_facts_reused: bool
    prior_plan: TargetProductExecutionPlan | None
    dependencies: TargetProductDependenciesProtocol


@dataclass(frozen=True)
class CheckpointResolutionRequest:
    workspace_root: Path
    update_mode: NormalizeUpdateMode
    claim_set_fingerprint: str
    evidence_set: EvidenceSet
    reconciliation_states: tuple[ReconciliationState, ...]
    reconciliation_states_reused: bool
    prior_plan: TargetProductExecutionPlan | None
    dependencies: TargetProductDependenciesProtocol


def resolve_economic_facts(
    request: EconomicFactsResolutionRequest,
) -> tuple[
    EconomicFacts,
    EconomicFactsExecutionDecision,
    EconomicFactsCompatibilityArtifacts,
]:
    prior_plan = request.prior_plan
    prior_economic_facts = None if prior_plan is None else prior_plan.economic_facts
    can_reuse_kernel = (
        request.update_mode is not NormalizeUpdateMode.REBUILD
        and prior_plan is not None
        and prior_economic_facts is not None
        and prior_plan.claim_set_fingerprint == request.claim_set_fingerprint
        and (request.workspace_root / prior_economic_facts.economic_facts_ref).is_file()
    )
    if can_reuse_kernel:
        assert prior_economic_facts is not None
        economic_facts = request.dependencies.economic_facts.read_economic_facts(
            request.workspace_root / prior_economic_facts.economic_facts_ref
        )
        kernel_action = TargetProductStageAction.REUSED
        fingerprint = prior_economic_facts.fingerprint
        economic_facts_ref_value = prior_economic_facts.economic_facts_ref
    else:
        economic_facts = build_economic_facts(claim_set=request.claim_set)
        request.dependencies.economic_facts.write_economic_facts(
            economic_facts_product_file(
                request.workspace_root,
                economic_facts.economic_facts_id,
            ),
            economic_facts,
        )
        kernel_action = TargetProductStageAction.REBUILT
        fingerprint = economic_facts_fingerprint(economic_facts)
        economic_facts_ref_value = economic_facts_ref(
            request.workspace_root,
            economic_facts.economic_facts_id,
        )

    compatibility_fact_path = economic_facts_compatibility_facts_file(
        request.workspace_root,
        economic_facts.economic_facts_id,
    )
    compatibility_annotation_path = economic_facts_compatibility_fact_annotations_file(
        request.workspace_root,
        economic_facts.economic_facts_id,
    )
    current_compatibility_signature = economic_facts_compatibility_signature(
        economic_facts=economic_facts,
        claim_set=request.claim_set,
        evidence_set=request.evidence_set,
        draft_projection_field_records=request.translation_result.draft_projection_field_records,
    )
    must_refresh_detail = (
        request.update_mode
        in {NormalizeUpdateMode.FULL_UPDATE, NormalizeUpdateMode.REBUILD}
        or kernel_action is TargetProductStageAction.REBUILT
        or not compatibility_fact_path.is_file()
        or not compatibility_annotation_path.is_file()
        or (
            prior_economic_facts is not None
            and prior_economic_facts.compatibility_signature
            != current_compatibility_signature
        )
    )
    if must_refresh_detail:
        compatibility = project_compatibility_artifacts_from_economic_facts(
            economic_facts=economic_facts,
            claim_set=request.claim_set,
            evidence_set=request.evidence_set,
            draft_projection_field_records=request.translation_result.draft_projection_field_records,
        )
        request.dependencies.facts.write_facts(
            compatibility_fact_path,
            compatibility.facts,
        )
        request.dependencies.artifacts.write_json(
            compatibility_annotation_path,
            [record.to_json() for record in compatibility.fact_annotations],
        )
        compatibility_action = TargetProductStageAction.REFRESHED
        compatibility_signature = current_compatibility_signature
    else:
        compatibility = EconomicFactsCompatibilityArtifacts(
            facts=request.dependencies.facts.read_facts(compatibility_fact_path),
            fact_annotations=read_fact_annotations(compatibility_annotation_path),
        )
        compatibility_action = TargetProductStageAction.REUSED
        compatibility_signature = current_compatibility_signature
    return (
        economic_facts,
        EconomicFactsExecutionDecision(
            economic_facts_id=economic_facts.economic_facts_id,
            economic_facts_ref=economic_facts_ref_value,
            fingerprint=fingerprint,
            kernel_action=kernel_action,
            compatibility_action=compatibility_action,
            compatibility_signature=compatibility_signature,
        ),
        compatibility,
    )


def resolve_reconciliation_states(
    request: ReconciliationStateResolutionRequest,
) -> tuple[
    tuple[ReconciliationState, ...],
    tuple[ReconciliationStateExecutionDecision, ...],
    tuple[BalanceSnapshot, ...],
]:
    prior_plan = request.prior_plan
    prior_states = () if prior_plan is None else prior_plan.reconciliation_states
    can_reuse_kernels = (
        request.update_mode is not NormalizeUpdateMode.REBUILD
        and prior_plan is not None
        and prior_plan.claim_set_fingerprint == request.claim_set_fingerprint
        and request.economic_facts_reused
        and prior_states
        and all(
            (request.workspace_root / decision.reconciliation_state_ref).is_file()
            for decision in prior_states
        )
    )
    if can_reuse_kernels:
        states = tuple(
            request.dependencies.reconciliation_states.read_reconciliation_state(
                request.workspace_root / decision.reconciliation_state_ref
            )
            for decision in prior_states
        )
        kernel_action = TargetProductStageAction.REUSED
    else:
        states = build_reconciliation_states(
            economic_facts=request.economic_facts,
            claim_set=request.claim_set,
            evidence_set=request.evidence_set,
        )
        for state in states:
            request.dependencies.reconciliation_states.write_reconciliation_state(
                reconciliation_state_product_file(
                    request.workspace_root,
                    state.reconciliation_state_id,
                ),
                state,
            )
        kernel_action = TargetProductStageAction.REBUILT

    prior_by_ref = {
        decision.reconciliation_state_ref: decision for decision in prior_states
    }
    snapshot_rows: list[BalanceSnapshot] = []
    decisions: list[ReconciliationStateExecutionDecision] = []
    for state in states:
        state_ref_value = reconciliation_state_ref(
            request.workspace_root,
            state.reconciliation_state_id,
        )
        snapshot_path = reconciliation_state_compatibility_snapshots_file(
            request.workspace_root,
            state.reconciliation_state_id,
        )
        prior_snapshot_signature = prior_by_ref.get(state_ref_value)
        current_snapshot_signature: str | None = None
        if not (
            request.update_mode
            in {NormalizeUpdateMode.FULL_UPDATE, NormalizeUpdateMode.REBUILD}
            or kernel_action is TargetProductStageAction.REBUILT
            or not snapshot_path.is_file()
        ):
            current_snapshot_signature = snapshot_rows_signature(
                project_balance_snapshots_from_reconciliation_state(state)
            )
        snapshot_action = (
            TargetProductStageAction.REFRESHED
            if request.update_mode
            in {NormalizeUpdateMode.FULL_UPDATE, NormalizeUpdateMode.REBUILD}
            or kernel_action is TargetProductStageAction.REBUILT
            or not snapshot_path.is_file()
            or (
                prior_snapshot_signature is None
                or prior_snapshot_signature.snapshot_signature
                != current_snapshot_signature
            )
            else TargetProductStageAction.REUSED
        )
        if snapshot_action is TargetProductStageAction.REFRESHED:
            projected_snapshots = project_balance_snapshots_from_reconciliation_state(
                state
            )
            request.dependencies.evidence.write_balance_snapshots(
                snapshot_path,
                projected_snapshots,
            )
            snapshot_signature = (
                current_snapshot_signature
                if current_snapshot_signature is not None
                else snapshot_rows_signature(projected_snapshots)
            )
        else:
            projected_snapshots = request.dependencies.evidence.read_balance_snapshots(
                snapshot_path
            )
            assert current_snapshot_signature is not None
            snapshot_signature = current_snapshot_signature
        snapshot_rows.extend(projected_snapshots)
        decisions.append(
            ReconciliationStateExecutionDecision(
                reconciliation_state_id=state.reconciliation_state_id,
                reconciliation_state_ref=state_ref_value,
                fingerprint=(
                    prior_by_ref[state_ref_value].fingerprint
                    if kernel_action is TargetProductStageAction.REUSED
                    else reconciliation_state_fingerprint(state)
                ),
                kernel_action=kernel_action,
                snapshot_action=snapshot_action,
                snapshot_signature=snapshot_signature,
            )
        )
    return tuple(states), tuple(decisions), tuple(snapshot_rows)


def resolve_checkpoints(
    request: CheckpointResolutionRequest,
) -> tuple[
    tuple[Checkpoint, ...],
    tuple[CheckpointExecutionDecision, ...],
    tuple[BalanceReference, ...],
]:
    prior_plan = request.prior_plan
    prior_checkpoints = () if prior_plan is None else prior_plan.checkpoints
    can_reuse_kernels = (
        request.update_mode is not NormalizeUpdateMode.REBUILD
        and prior_plan is not None
        and prior_plan.claim_set_fingerprint == request.claim_set_fingerprint
        and request.reconciliation_states_reused
        and all(
            (request.workspace_root / decision.checkpoint_ref).is_file()
            for decision in prior_checkpoints
        )
    )
    if can_reuse_kernels:
        checkpoints = tuple(
            request.dependencies.checkpoints.read_checkpoint(
                request.workspace_root / decision.checkpoint_ref
            )
            for decision in prior_checkpoints
        )
        kernel_action = TargetProductStageAction.REUSED
    else:
        checkpoints = build_checkpoints(
            reconciliation_states=request.reconciliation_states
        )
        for checkpoint in checkpoints:
            request.dependencies.checkpoints.write_checkpoint(
                checkpoint_product_file(
                    request.workspace_root,
                    checkpoint.checkpoint_id,
                ),
                checkpoint,
            )
        kernel_action = TargetProductStageAction.REBUILT

    prior_by_ref = {decision.checkpoint_ref: decision for decision in prior_checkpoints}
    observation_details = observation_details_from_evidence_set(request.evidence_set)
    reference_rows: list[BalanceReference] = []
    decisions: list[CheckpointExecutionDecision] = []
    for checkpoint in checkpoints:
        checkpoint_ref_value = checkpoint_ref(
            request.workspace_root,
            checkpoint.checkpoint_id,
        )
        reference_path = checkpoint_compatibility_references_file(
            request.workspace_root,
            checkpoint.checkpoint_id,
        )
        prior_reference_signature = prior_by_ref.get(checkpoint_ref_value)
        current_reference_signature: str | None = None
        if not (
            request.update_mode
            in {NormalizeUpdateMode.FULL_UPDATE, NormalizeUpdateMode.REBUILD}
            or kernel_action is TargetProductStageAction.REBUILT
            or not reference_path.is_file()
        ):
            current_reference_signature = checkpoint_reference_signature(
                checkpoint=checkpoint,
                reconciliation_states=request.reconciliation_states,
                evidence_set=request.evidence_set,
            )
        reference_action = (
            TargetProductStageAction.REFRESHED
            if request.update_mode
            in {NormalizeUpdateMode.FULL_UPDATE, NormalizeUpdateMode.REBUILD}
            or kernel_action is TargetProductStageAction.REBUILT
            or not reference_path.is_file()
            or (
                prior_reference_signature is None
                or prior_reference_signature.reference_signature
                != current_reference_signature
            )
            else TargetProductStageAction.REUSED
        )
        if reference_action is TargetProductStageAction.REFRESHED:
            projected_references = project_balance_references_from_checkpoint(
                checkpoint=checkpoint,
                reconciliation_states=request.reconciliation_states,
                observation_details=observation_details,
            )
            request.dependencies.evidence.write_balance_references(
                reference_path,
                projected_references,
            )
            reference_signature = (
                current_reference_signature
                if current_reference_signature is not None
                else reference_rows_signature(projected_references)
            )
        else:
            projected_references = (
                request.dependencies.evidence.read_balance_references(reference_path)
            )
            assert current_reference_signature is not None
            reference_signature = current_reference_signature
        reference_rows.extend(projected_references)
        decisions.append(
            CheckpointExecutionDecision(
                checkpoint_id=checkpoint.checkpoint_id,
                checkpoint_ref=checkpoint_ref_value,
                fingerprint=(
                    prior_by_ref[checkpoint_ref_value].fingerprint
                    if kernel_action is TargetProductStageAction.REUSED
                    else checkpoint_fingerprint(checkpoint)
                ),
                kernel_action=kernel_action,
                reference_action=reference_action,
                reference_signature=reference_signature,
            )
        )
    return tuple(checkpoints), tuple(decisions), tuple(reference_rows)
