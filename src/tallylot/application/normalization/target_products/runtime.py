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
    reconciliation_state_compatibility_snapshots_file,
    reconciliation_state_product_file,
    reconciliation_state_ref,
)
from tallylot.application.checkpoint import build_checkpoints
from tallylot.application.compatibility.checkpoints import (
    observation_details_from_evidence_set,
)
from tallylot.application.compatibility.economic_facts import (
    EconomicFactsCompatibilityArtifacts,
)
from tallylot.application.normalization.contracts import NormalizeUpdateMode
from tallylot.application.normalization.translation import TranslationExecutionResult
from tallylot.application.reconciliation import build_reconciliation_states
from tallylot.domain.balances import BalanceReference, BalanceSnapshot
from tallylot.domain.checkpoint import Checkpoint, checkpoint_fingerprint
from tallylot.domain.claim import ClaimSet
from tallylot.domain.economics import EconomicFacts
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
from .detail_outputs import (
    DETAIL_READ_EXCEPTIONS,
    refresh_checkpoint_references,
    refresh_economic_facts_compatibility,
    refresh_reconciliation_state_snapshots,
)
from .kernel_reuse import (
    resolve_economic_facts_kernel,
    resolve_checkpoint_kernels,
    resolve_reconciliation_state_kernels,
    validate_checkpoint_kernel_ref,
    validate_reconciliation_state_kernel_ref,
)
from .planning import decide_detail_action, decide_kernel_action
from .payloads import read_fact_annotations
from .signatures import (
    checkpoint_reference_signature,
    economic_facts_compatibility_signature,
    reconciliation_state_snapshot_signature,
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
    prior_evidence_set_id: str | None
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
    kernel_resolution = resolve_economic_facts_kernel(request)
    economic_facts = kernel_resolution.economic_facts
    current_fingerprint = kernel_resolution.fingerprint
    economic_facts_ref_value = kernel_resolution.economic_facts_ref_value
    existing_kernel_invalid = kernel_resolution.existing_kernel_invalid
    kernel_action = decide_kernel_action(
        update_mode=request.update_mode,
        prior_fingerprint=(
            None
            if prior_economic_facts is None or existing_kernel_invalid
            else prior_economic_facts.fingerprint
        ),
        current_fingerprint=current_fingerprint,
        kernel_exists=(
            (request.workspace_root / economic_facts_ref_value).is_file()
            and not existing_kernel_invalid
        ),
        upstream_rebuilt=False,
    )
    if kernel_action is TargetProductStageAction.REBUILT:
        assert kernel_resolution.built_current_kernel is True
        request.dependencies.economic_facts.write_economic_facts(
            economic_facts_product_file(
                request.workspace_root,
                economic_facts.economic_facts_id,
            ),
            economic_facts,
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
    compatibility_action = decide_detail_action(
        update_mode=request.update_mode,
        kernel_action=kernel_action,
        prior_signature=(
            None
            if prior_economic_facts is None
            or prior_economic_facts.economic_facts_ref != economic_facts_ref_value
            else prior_economic_facts.compatibility_signature
        ),
        current_signature=current_compatibility_signature,
        detail_paths=(compatibility_fact_path, compatibility_annotation_path),
    )
    if compatibility_action is TargetProductStageAction.REFRESHED:
        compatibility = refresh_economic_facts_compatibility(
            request=request,
            economic_facts=economic_facts,
            facts_path=compatibility_fact_path,
            annotations_path=compatibility_annotation_path,
        )
    else:
        try:
            compatibility = EconomicFactsCompatibilityArtifacts(
                facts=request.dependencies.facts.read_facts(compatibility_fact_path),
                fact_annotations=read_fact_annotations(compatibility_annotation_path),
            )
        except DETAIL_READ_EXCEPTIONS:
            compatibility_action = TargetProductStageAction.REFRESHED
            compatibility = refresh_economic_facts_compatibility(
                request=request,
                economic_facts=economic_facts,
                facts_path=compatibility_fact_path,
                annotations_path=compatibility_annotation_path,
            )
    compatibility_signature = current_compatibility_signature
    return (
        economic_facts,
        EconomicFactsExecutionDecision(
            economic_facts_id=economic_facts.economic_facts_id,
            economic_facts_ref=economic_facts_ref_value,
            fingerprint=current_fingerprint,
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
    states, validation_state = resolve_reconciliation_state_kernels(
        request=request,
        prior_states=prior_states,
        build_current=lambda: build_reconciliation_states(
            economic_facts=request.economic_facts,
            claim_set=request.claim_set,
            evidence_set=request.evidence_set,
        ),
    )

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
        state_path = request.workspace_root / state_ref_value
        prior_state = prior_by_ref.get(state_ref_value)
        validate_reconciliation_state_kernel_ref(
            request=request,
            state_ref_value=state_ref_value,
            state_path=state_path,
            prior_state=prior_state,
            validation_state=validation_state,
        )
        current_fingerprint = reconciliation_state_fingerprint(state)
        kernel_action = decide_kernel_action(
            update_mode=request.update_mode,
            prior_fingerprint=(
                None
                if (
                    prior_state is None
                    or state_ref_value in validation_state.invalid_refs
                )
                else prior_state.fingerprint
            ),
            current_fingerprint=current_fingerprint,
            kernel_exists=(
                state_path.is_file()
                and state_ref_value not in validation_state.invalid_refs
            ),
            upstream_rebuilt=False,
        )
        if kernel_action is TargetProductStageAction.REBUILT:
            request.dependencies.reconciliation_states.write_reconciliation_state(
                reconciliation_state_product_file(
                    request.workspace_root,
                    state.reconciliation_state_id,
                ),
                state,
            )
        snapshot_path = reconciliation_state_compatibility_snapshots_file(
            request.workspace_root,
            state.reconciliation_state_id,
        )
        current_snapshot_signature = reconciliation_state_snapshot_signature(state)
        snapshot_action = decide_detail_action(
            update_mode=request.update_mode,
            kernel_action=kernel_action,
            prior_signature=(
                None if prior_state is None else prior_state.snapshot_signature
            ),
            current_signature=current_snapshot_signature,
            detail_paths=(snapshot_path,),
        )
        if snapshot_action is TargetProductStageAction.REFRESHED:
            projected_snapshots = refresh_reconciliation_state_snapshots(
                request=request,
                state=state,
                snapshot_path=snapshot_path,
            )
        else:
            try:
                projected_snapshots = (
                    request.dependencies.evidence.read_balance_snapshots(snapshot_path)
                )
            except DETAIL_READ_EXCEPTIONS:
                snapshot_action = TargetProductStageAction.REFRESHED
                projected_snapshots = refresh_reconciliation_state_snapshots(
                    request=request,
                    state=state,
                    snapshot_path=snapshot_path,
                )
        snapshot_signature = current_snapshot_signature
        snapshot_rows.extend(projected_snapshots)
        decisions.append(
            ReconciliationStateExecutionDecision(
                reconciliation_state_id=state.reconciliation_state_id,
                reconciliation_state_ref=state_ref_value,
                fingerprint=current_fingerprint,
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
    checkpoints, validation_state = resolve_checkpoint_kernels(
        request=request,
        prior_checkpoints=prior_checkpoints,
        build_current=lambda: build_checkpoints(
            reconciliation_states=request.reconciliation_states
        ),
    )

    prior_by_ref = {decision.checkpoint_ref: decision for decision in prior_checkpoints}
    observation_details = observation_details_from_evidence_set(request.evidence_set)
    reference_rows: list[BalanceReference] = []
    decisions: list[CheckpointExecutionDecision] = []
    for checkpoint in checkpoints:
        checkpoint_ref_value = checkpoint_ref(
            request.workspace_root,
            checkpoint.checkpoint_id,
        )
        checkpoint_path = request.workspace_root / checkpoint_ref_value
        prior_checkpoint = prior_by_ref.get(checkpoint_ref_value)
        validate_checkpoint_kernel_ref(
            request=request,
            checkpoint_ref_value=checkpoint_ref_value,
            checkpoint_path=checkpoint_path,
            prior_checkpoint=prior_checkpoint,
            validation_state=validation_state,
        )
        current_fingerprint = checkpoint_fingerprint(checkpoint)
        kernel_action = decide_kernel_action(
            update_mode=request.update_mode,
            prior_fingerprint=(
                None
                if (
                    prior_checkpoint is None
                    or checkpoint_ref_value in validation_state.invalid_refs
                )
                else prior_checkpoint.fingerprint
            ),
            current_fingerprint=current_fingerprint,
            kernel_exists=(
                checkpoint_path.is_file()
                and checkpoint_ref_value not in validation_state.invalid_refs
            ),
            upstream_rebuilt=False,
        )
        if kernel_action is TargetProductStageAction.REBUILT:
            request.dependencies.checkpoints.write_checkpoint(
                checkpoint_product_file(
                    request.workspace_root,
                    checkpoint.checkpoint_id,
                ),
                checkpoint,
            )
        reference_path = checkpoint_compatibility_references_file(
            request.workspace_root,
            checkpoint.checkpoint_id,
        )
        current_reference_signature = checkpoint_reference_signature(
            checkpoint=checkpoint,
            reconciliation_states=request.reconciliation_states,
            evidence_set=request.evidence_set,
        )
        reference_action = decide_detail_action(
            update_mode=request.update_mode,
            kernel_action=kernel_action,
            prior_signature=(
                None
                if prior_checkpoint is None
                else prior_checkpoint.reference_signature
            ),
            current_signature=current_reference_signature,
            detail_paths=(reference_path,),
        )
        if reference_action is TargetProductStageAction.REFRESHED:
            projected_references = refresh_checkpoint_references(
                request=request,
                checkpoint=checkpoint,
                observation_details=observation_details,
                reference_path=reference_path,
            )
        else:
            try:
                projected_references = (
                    request.dependencies.evidence.read_balance_references(
                        reference_path
                    )
                )
            except DETAIL_READ_EXCEPTIONS:
                reference_action = TargetProductStageAction.REFRESHED
                projected_references = refresh_checkpoint_references(
                    request=request,
                    checkpoint=checkpoint,
                    observation_details=observation_details,
                    reference_path=reference_path,
                )
        reference_signature = current_reference_signature
        reference_rows.extend(projected_references)
        decisions.append(
            CheckpointExecutionDecision(
                checkpoint_id=checkpoint.checkpoint_id,
                checkpoint_ref=checkpoint_ref_value,
                fingerprint=current_fingerprint,
                kernel_action=kernel_action,
                reference_action=reference_action,
                reference_signature=reference_signature,
            )
        )
    return tuple(checkpoints), tuple(decisions), tuple(reference_rows)
