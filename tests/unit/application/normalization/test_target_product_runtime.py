from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from tallylot.application.capture_paths import (
    checkpoint_compatibility_references_file,
    checkpoint_ref,
    reconciliation_state_compatibility_snapshots_file,
    reconciliation_state_ref,
)
from tallylot.application.compatibility.checkpoints import (
    observation_details_from_evidence_set,
    project_balance_references_from_checkpoint,
)
from tallylot.application.compatibility.reconciliation_states import (
    project_balance_snapshots_from_reconciliation_state,
)
from tallylot.application.normalization.contracts import NormalizeUpdateMode
from tallylot.application.normalization.target_products.models import (
    CheckpointExecutionDecision,
    ReconciliationStateExecutionDecision,
    TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION,
    TargetProductExecutionPlan,
    TargetProductStageAction,
)
from tallylot.application.normalization.target_products import runtime as runtime_module
from tallylot.application.normalization.target_products.runtime import (
    CheckpointResolutionRequest,
    ReconciliationStateResolutionRequest,
    resolve_checkpoints,
    resolve_reconciliation_states,
)
from tallylot.application.normalization.target_products.signatures import (
    checkpoint_reference_signature,
    reconciliation_state_snapshot_signature,
)
from tallylot.domain.assertion import QuantityValue
from tallylot.domain.checkpoint import (
    Checkpoint,
    CheckpointAssertionBasis,
    CheckpointAssertionContinuityKind,
    CheckpointAssertionRecord,
    CheckpointAssertionSupportShape,
    CheckpointAssertionTrustLevel,
    CheckpointAssertionValueKind,
    CheckpointRecord,
    checkpoint_fingerprint,
)
from tallylot.domain.claim import ClaimSet
from tallylot.domain.economics import EconomicFacts
from tallylot.domain.evidence import (
    EvidenceMemberKind,
    EvidenceMemberRecord,
    EvidenceMemberStatus,
    EvidenceObservationKind,
    EvidenceObservationRecord,
    EvidenceSelectionBasis,
    EvidenceSelectionRecord,
    EvidenceSet,
)
from tallylot.domain.reconciliation import (
    BalanceTargetKind,
    BalanceTargetObservationStatus,
    BalanceTargetRecord,
    CheckpointProposalRecord,
    CheckpointProposalStatus,
    ComparisonOutcome,
    ContinuitySegmentRecord,
    ContinuitySegmentStatus,
    ReconciliationState,
    reconciliation_state_fingerprint,
)
from tallylot.domain.temporal import TemporalPrecision
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import (
    FilesystemCheckpointRepository,
    FilesystemEconomicFactsRepository,
    FilesystemEvidenceRepository,
    FilesystemFactRepository,
    FilesystemReconciliationStateRepository,
)


@dataclass
class _Dependencies:
    facts: FilesystemFactRepository = field(default_factory=FilesystemFactRepository)
    evidence: FilesystemEvidenceRepository = field(
        default_factory=FilesystemEvidenceRepository
    )
    economic_facts: FilesystemEconomicFactsRepository = field(
        default_factory=FilesystemEconomicFactsRepository
    )
    reconciliation_states: FilesystemReconciliationStateRepository = field(
        default_factory=FilesystemReconciliationStateRepository
    )
    checkpoints: FilesystemCheckpointRepository = field(
        default_factory=FilesystemCheckpointRepository
    )
    artifacts: FilesystemArtifactStore = field(default_factory=FilesystemArtifactStore)


def test_resolve_reconciliation_states_reuses_unchanged_current_partitions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    dependencies = _Dependencies()
    prior_state_1 = _sample_state(state_id="state-1", quantity="1.25")
    prior_state_2 = _sample_state(state_id="state-2", quantity="2.50")
    for state in (prior_state_1, prior_state_2):
        state_path = workspace_root / reconciliation_state_ref(
            workspace_root,
            state.reconciliation_state_id,
        )
        dependencies.reconciliation_states.write_reconciliation_state(state_path, state)
        dependencies.evidence.write_balance_snapshots(
            reconciliation_state_compatibility_snapshots_file(
                workspace_root,
                state.reconciliation_state_id,
            ),
            project_balance_snapshots_from_reconciliation_state(state),
        )
    prior_plan = TargetProductExecutionPlan(
        signature_version=TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION,
        update_mode_requested="auto",
        update_mode_effective="auto",
        claim_set_fingerprint="prior-claim-fingerprint",
        economic_facts=None,
        reconciliation_states=(
            _state_decision(workspace_root, prior_state_1),
            _state_decision(workspace_root, prior_state_2),
        ),
        checkpoints=(),
    )
    current_state_1 = _sample_state(state_id="state-1", quantity="1.25")
    current_state_2 = _sample_state(state_id="state-2", quantity="3.00")

    def _build_reconciliation_states(
        *,
        economic_facts: EconomicFacts,
        claim_set: ClaimSet,
        evidence_set: EvidenceSet,
    ) -> tuple[ReconciliationState, ReconciliationState]:
        del economic_facts, claim_set, evidence_set
        return current_state_1, current_state_2

    monkeypatch.setattr(
        runtime_module,
        "build_reconciliation_states",
        _build_reconciliation_states,
    )

    _, decisions, _ = resolve_reconciliation_states(
        ReconciliationStateResolutionRequest(
            workspace_root=workspace_root,
            update_mode=NormalizeUpdateMode.AUTO,
            claim_set=cast(ClaimSet, object()),
            claim_set_fingerprint="current-claim-fingerprint",
            evidence_set=_sample_evidence_set(),
            prior_evidence_set_id="evidence-set-1",
            economic_facts=cast(EconomicFacts, object()),
            economic_facts_reused=False,
            prior_plan=prior_plan,
            dependencies=dependencies,
        )
    )

    assert [decision.reconciliation_state_id for decision in decisions] == [
        "state-1",
        "state-2",
    ]
    assert decisions[0].kernel_action is TargetProductStageAction.REUSED
    assert decisions[0].snapshot_action is TargetProductStageAction.REUSED
    assert decisions[1].kernel_action is TargetProductStageAction.REBUILT
    assert decisions[1].snapshot_action is TargetProductStageAction.REFRESHED


def test_resolve_reconciliation_states_recomputes_current_partitions_when_evidence_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    dependencies = _Dependencies()
    prior_state = _sample_state(state_id="state-1", quantity="1.25")
    state_path = workspace_root / reconciliation_state_ref(
        workspace_root,
        prior_state.reconciliation_state_id,
    )
    dependencies.reconciliation_states.write_reconciliation_state(
        state_path, prior_state
    )
    dependencies.evidence.write_balance_snapshots(
        reconciliation_state_compatibility_snapshots_file(
            workspace_root,
            prior_state.reconciliation_state_id,
        ),
        project_balance_snapshots_from_reconciliation_state(prior_state),
    )
    prior_plan = TargetProductExecutionPlan(
        signature_version=TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION,
        update_mode_requested="auto",
        update_mode_effective="auto",
        claim_set_fingerprint="claim-fingerprint",
        economic_facts=None,
        reconciliation_states=(_state_decision(workspace_root, prior_state),),
        checkpoints=(),
    )
    rebuilt_state = ReconciliationState(
        reconciliation_state_id="state-1",
        economic_facts_ref="facts-1",
        continuity_segment_records=prior_state.continuity_segment_records,
        event_link_records=prior_state.event_link_records,
        balance_target_records=prior_state.balance_target_records,
        checkpoint_proposal_records=(
            CheckpointProposalRecord(
                proposal_id="proposal-state-1",
                segment_id="segment-state-1",
                subject_ref=prior_state.balance_target_records[0].subject_ref,
                as_of=prior_state.balance_target_records[0].as_of,
                status=CheckpointProposalStatus.PARTIAL,
                superseding_proposal_ref="",
                target_refs=("target-state-1",),
                evidence_refs=(),
            ),
        ),
    )
    build_called = False

    def _build_reconciliation_states(
        *,
        economic_facts: EconomicFacts,
        claim_set: ClaimSet,
        evidence_set: EvidenceSet,
    ) -> tuple[ReconciliationState]:
        nonlocal build_called
        del economic_facts, claim_set, evidence_set
        build_called = True
        return (rebuilt_state,)

    monkeypatch.setattr(
        runtime_module,
        "build_reconciliation_states",
        _build_reconciliation_states,
    )

    _, decisions, _ = resolve_reconciliation_states(
        ReconciliationStateResolutionRequest(
            workspace_root=workspace_root,
            update_mode=NormalizeUpdateMode.AUTO,
            claim_set=cast(ClaimSet, object()),
            claim_set_fingerprint="claim-fingerprint",
            evidence_set=_sample_evidence_set(evidence_set_id="evidence-set-2"),
            prior_evidence_set_id="evidence-set-1",
            economic_facts=cast(EconomicFacts, object()),
            economic_facts_reused=True,
            prior_plan=prior_plan,
            dependencies=dependencies,
        )
    )

    assert build_called is True
    assert decisions[0].kernel_action is TargetProductStageAction.REBUILT
    assert decisions[0].snapshot_action is TargetProductStageAction.REFRESHED
    persisted_state = dependencies.reconciliation_states.read_reconciliation_state(
        state_path
    )
    assert persisted_state.checkpoint_proposal_records[0].status is (
        CheckpointProposalStatus.PARTIAL
    )


def test_resolve_reconciliation_states_rebuilds_semantically_drifted_persisted_kernel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    dependencies = _Dependencies()
    prior_state = _sample_state(state_id="state-1", quantity="1.25")
    drifted_state = replace(
        prior_state,
        checkpoint_proposal_records=(
            replace(
                prior_state.checkpoint_proposal_records[0],
                status=CheckpointProposalStatus.PARTIAL,
            ),
        ),
    )
    state_path = workspace_root / reconciliation_state_ref(
        workspace_root,
        prior_state.reconciliation_state_id,
    )
    dependencies.reconciliation_states.write_reconciliation_state(
        state_path, drifted_state
    )
    dependencies.evidence.write_balance_snapshots(
        reconciliation_state_compatibility_snapshots_file(
            workspace_root,
            prior_state.reconciliation_state_id,
        ),
        project_balance_snapshots_from_reconciliation_state(drifted_state),
    )
    prior_plan = TargetProductExecutionPlan(
        signature_version=TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION,
        update_mode_requested="auto",
        update_mode_effective="auto",
        claim_set_fingerprint="claim-fingerprint",
        economic_facts=None,
        reconciliation_states=(_state_decision(workspace_root, prior_state),),
        checkpoints=(),
    )

    def _build_reconciliation_states(
        *,
        economic_facts: EconomicFacts,
        claim_set: ClaimSet,
        evidence_set: EvidenceSet,
    ) -> tuple[ReconciliationState]:
        del economic_facts, claim_set, evidence_set
        return (prior_state,)

    monkeypatch.setattr(
        runtime_module,
        "build_reconciliation_states",
        _build_reconciliation_states,
    )

    _, decisions, _ = resolve_reconciliation_states(
        ReconciliationStateResolutionRequest(
            workspace_root=workspace_root,
            update_mode=NormalizeUpdateMode.AUTO,
            claim_set=cast(ClaimSet, object()),
            claim_set_fingerprint="claim-fingerprint",
            evidence_set=_sample_evidence_set(),
            prior_evidence_set_id="evidence-set-1",
            economic_facts=cast(EconomicFacts, object()),
            economic_facts_reused=True,
            prior_plan=prior_plan,
            dependencies=dependencies,
        )
    )

    assert decisions[0].kernel_action is TargetProductStageAction.REBUILT
    assert decisions[0].snapshot_action is TargetProductStageAction.REFRESHED
    assert (
        dependencies.reconciliation_states.read_reconciliation_state(state_path)
        == prior_state
    )


def test_resolve_checkpoints_reuses_unchanged_current_partitions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    dependencies = _Dependencies()
    evidence_set = _sample_evidence_set()
    state_1 = _sample_state(state_id="state-1", quantity="1.25")
    state_2 = _sample_state(state_id="state-2", quantity="2.50")
    prior_checkpoint_1 = _sample_checkpoint(
        checkpoint_id="checkpoint-1",
        state=state_1,
        quantity="1.25",
    )
    prior_checkpoint_2 = _sample_checkpoint(
        checkpoint_id="checkpoint-2",
        state=state_2,
        quantity="2.50",
    )
    for checkpoint, states in (
        (prior_checkpoint_1, (state_1,)),
        (prior_checkpoint_2, (state_2,)),
    ):
        checkpoint_path = workspace_root / checkpoint_ref(
            workspace_root,
            checkpoint.checkpoint_id,
        )
        dependencies.checkpoints.write_checkpoint(checkpoint_path, checkpoint)
        dependencies.evidence.write_balance_references(
            checkpoint_compatibility_references_file(
                workspace_root,
                checkpoint.checkpoint_id,
            ),
            project_balance_references_from_checkpoint(
                checkpoint=checkpoint,
                reconciliation_states=states,
                observation_details=observation_details_from_evidence_set(evidence_set),
            ),
        )
    prior_plan = TargetProductExecutionPlan(
        signature_version=TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION,
        update_mode_requested="auto",
        update_mode_effective="auto",
        claim_set_fingerprint="prior-claim-fingerprint",
        economic_facts=None,
        reconciliation_states=(),
        checkpoints=(
            _checkpoint_decision(
                workspace_root,
                prior_checkpoint_1,
                evidence_set,
                (state_1,),
            ),
            _checkpoint_decision(
                workspace_root,
                prior_checkpoint_2,
                evidence_set,
                (state_2,),
            ),
        ),
    )
    current_checkpoint_1 = _sample_checkpoint(
        checkpoint_id="checkpoint-1",
        state=state_1,
        quantity="1.25",
    )
    current_checkpoint_2 = _sample_checkpoint(
        checkpoint_id="checkpoint-2",
        state=state_2,
        quantity="3.00",
    )

    def _build_checkpoints(
        *, reconciliation_states: tuple[ReconciliationState, ...]
    ) -> tuple[Checkpoint, Checkpoint]:
        del reconciliation_states
        return current_checkpoint_1, current_checkpoint_2

    monkeypatch.setattr(
        runtime_module,
        "build_checkpoints",
        _build_checkpoints,
    )

    _, decisions, _ = resolve_checkpoints(
        CheckpointResolutionRequest(
            workspace_root=workspace_root,
            update_mode=NormalizeUpdateMode.AUTO,
            claim_set_fingerprint="current-claim-fingerprint",
            evidence_set=evidence_set,
            reconciliation_states=(state_1, state_2),
            reconciliation_states_reused=False,
            prior_plan=prior_plan,
            dependencies=dependencies,
        )
    )

    assert [decision.checkpoint_id for decision in decisions] == [
        "checkpoint-1",
        "checkpoint-2",
    ]
    assert decisions[0].kernel_action is TargetProductStageAction.REUSED
    assert decisions[0].reference_action is TargetProductStageAction.REUSED
    assert decisions[1].kernel_action is TargetProductStageAction.REBUILT
    assert decisions[1].reference_action is TargetProductStageAction.REFRESHED


def test_resolve_checkpoints_rebuilds_semantically_drifted_persisted_kernel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    dependencies = _Dependencies()
    evidence_set = _sample_evidence_set()
    state = _sample_state(state_id="state-1", quantity="1.25")
    prior_checkpoint = _sample_checkpoint(
        checkpoint_id="checkpoint-1",
        state=state,
        quantity="1.25",
    )
    drifted_checkpoint = replace(
        prior_checkpoint,
        checkpoint_assertion_records=(
            replace(
                prior_checkpoint.checkpoint_assertion_records[0],
                trust_level=CheckpointAssertionTrustLevel.ANALYSIS_READY,
            ),
        ),
    )
    checkpoint_path = workspace_root / checkpoint_ref(
        workspace_root,
        prior_checkpoint.checkpoint_id,
    )
    dependencies.checkpoints.write_checkpoint(checkpoint_path, drifted_checkpoint)
    dependencies.evidence.write_balance_references(
        checkpoint_compatibility_references_file(
            workspace_root,
            prior_checkpoint.checkpoint_id,
        ),
        project_balance_references_from_checkpoint(
            checkpoint=drifted_checkpoint,
            reconciliation_states=(state,),
            observation_details=observation_details_from_evidence_set(evidence_set),
        ),
    )
    prior_plan = TargetProductExecutionPlan(
        signature_version=TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION,
        update_mode_requested="auto",
        update_mode_effective="auto",
        claim_set_fingerprint="claim-fingerprint",
        economic_facts=None,
        reconciliation_states=(),
        checkpoints=(
            _checkpoint_decision(
                workspace_root,
                prior_checkpoint,
                evidence_set,
                (state,),
            ),
        ),
    )

    def _build_checkpoints(
        *, reconciliation_states: tuple[ReconciliationState, ...]
    ) -> tuple[Checkpoint]:
        del reconciliation_states
        return (prior_checkpoint,)

    monkeypatch.setattr(runtime_module, "build_checkpoints", _build_checkpoints)

    _, decisions, _ = resolve_checkpoints(
        CheckpointResolutionRequest(
            workspace_root=workspace_root,
            update_mode=NormalizeUpdateMode.AUTO,
            claim_set_fingerprint="claim-fingerprint",
            evidence_set=evidence_set,
            reconciliation_states=(state,),
            reconciliation_states_reused=True,
            prior_plan=prior_plan,
            dependencies=dependencies,
        )
    )

    assert decisions[0].kernel_action is TargetProductStageAction.REBUILT
    assert decisions[0].reference_action is TargetProductStageAction.REFRESHED
    assert dependencies.checkpoints.read_checkpoint(checkpoint_path) == prior_checkpoint


def _sample_state(*, state_id: str, quantity: str) -> ReconciliationState:
    location_id, instrument_id = (
        ("coinbase", "symbol:BTC@coinbase")
        if state_id == "state-1"
        else ("coinbase:coinbase_cash", "symbol:CAD@coinbase")
    )
    subject_ref = (
        "position",
        (
            ("beneficial_owner:filing",),
            (location_id,),
            (instrument_id,),
            None,
            "held_position",
        ),
    )
    as_of = datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC)
    accepted_value = QuantityValue(quantity=Decimal(quantity), subject_ref=subject_ref)
    return ReconciliationState(
        reconciliation_state_id=state_id,
        economic_facts_ref="facts-1",
        continuity_segment_records=(
            ContinuitySegmentRecord(
                segment_id=f"segment-{state_id}",
                subject_ref=subject_ref,
                segment_start_at=datetime(2024, 2, 8, 16, 31, 22, tzinfo=UTC),
                segment_end_at=as_of,
                status=ContinuitySegmentStatus.COMPLETE,
                as_of=as_of,
            ),
        ),
        event_link_records=(),
        balance_target_records=(
            BalanceTargetRecord(
                target_id=f"target-{state_id}",
                segment_id=f"segment-{state_id}",
                subject_ref=subject_ref,
                kind=BalanceTargetKind.EXACT_BALANCE,
                as_of=as_of,
                expected_value=accepted_value,
                observed_value=accepted_value,
                observation_status=BalanceTargetObservationStatus.OBSERVED,
                comparison_outcome=ComparisonOutcome.MATCHED,
            ),
        ),
        checkpoint_proposal_records=(
            CheckpointProposalRecord(
                proposal_id=f"proposal-{state_id}",
                segment_id=f"segment-{state_id}",
                subject_ref=subject_ref,
                as_of=as_of,
                status=CheckpointProposalStatus.READY,
                superseding_proposal_ref="",
                target_refs=(f"target-{state_id}",),
                evidence_refs=(f"statement-{state_id}.pdf#page=1",),
            ),
        ),
    )


def _sample_checkpoint(
    *, checkpoint_id: str, state: ReconciliationState, quantity: str
) -> Checkpoint:
    as_of = state.continuity_segment_records[0].as_of
    accepted_value = QuantityValue(
        quantity=Decimal(quantity),
        subject_ref=state.balance_target_records[0].subject_ref,
    )
    return Checkpoint(
        checkpoint_id=checkpoint_id,
        reconciliation_state_refs=(state.reconciliation_state_id,),
        as_of=as_of,
        checkpoint_records=(
            CheckpointRecord(
                checkpoint_id=checkpoint_id,
                as_of=as_of,
                assertion_ids=(f"assertion-{checkpoint_id}",),
                proposal_refs=(state.checkpoint_proposal_records[0].proposal_id,),
            ),
        ),
        checkpoint_assertion_records=(
            CheckpointAssertionRecord(
                assertion_id=f"assertion-{checkpoint_id}",
                checkpoint_id=checkpoint_id,
                subject_ref=state.balance_target_records[0].subject_ref,
                kind=CheckpointAssertionValueKind.POSITION_QUANTITY,
                as_of=as_of,
                accepted_value=accepted_value,
                trust_level=CheckpointAssertionTrustLevel.FILING_READY,
                basis=CheckpointAssertionBasis.DOCUMENT_SUPPORT,
                support_shape=CheckpointAssertionSupportShape.DOCUMENT_OBSERVATION,
                continuity_kind=CheckpointAssertionContinuityKind.RECONCILED_ROLLFORWARD,
            ),
        ),
    )


def _sample_evidence_set(*, evidence_set_id: str = "evidence-set-1") -> EvidenceSet:
    return EvidenceSet(
        evidence_set_id=evidence_set_id,
        selection_fingerprint="selection-1",
        capture_manifest_fingerprint="manifest-1",
        evidence_selection_records=(
            EvidenceSelectionRecord(
                evidence_set_id=evidence_set_id,
                selection_id="selection-1",
                key=("statement_document", "statement.pdf"),
                fingerprint="selection-fingerprint",
                basis=EvidenceSelectionBasis.SINGLE_MEMBER,
            ),
        ),
        evidence_member_records=(
            EvidenceMemberRecord(
                evidence_set_id=evidence_set_id,
                selection_id="selection-1",
                member_id="member-1",
                source_slug="coinbase",
                adapter_id="coinbase",
                capture_uid="capture-1",
                kind=EvidenceMemberKind.STATEMENT_DOCUMENT_FILE,
                locator=("statement.pdf",),
                status=EvidenceMemberStatus.SELECTED,
                capture_manifest_fingerprint="manifest-1",
            ),
        ),
        evidence_observation_records=(
            EvidenceObservationRecord(
                evidence_set_id=evidence_set_id,
                member_id="member-1",
                observation_id="observation-1",
                kind=EvidenceObservationKind.STATEMENT_DOCUMENT,
                key=("document",),
                statement_kind="coinbase",
                document_effective_at=datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC),
                document_effective_precision=TemporalPrecision.TIMESTAMP,
                statement_as_of=datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC),
                statement_as_of_precision=TemporalPrecision.TIMESTAMP,
                provenance_refs=(("capture-1", "statement.pdf"),),
            ),
        ),
    )


def _state_decision(
    workspace_root: Path, state: ReconciliationState
) -> ReconciliationStateExecutionDecision:
    return ReconciliationStateExecutionDecision(
        reconciliation_state_id=state.reconciliation_state_id,
        reconciliation_state_ref=reconciliation_state_ref(
            workspace_root,
            state.reconciliation_state_id,
        ),
        fingerprint=reconciliation_state_fingerprint(state),
        kernel_action=TargetProductStageAction.REBUILT,
        snapshot_action=TargetProductStageAction.REFRESHED,
        snapshot_signature=reconciliation_state_snapshot_signature(state),
    )


def _checkpoint_decision(
    workspace_root: Path,
    checkpoint: Checkpoint,
    evidence_set: EvidenceSet,
    reconciliation_states: tuple[ReconciliationState, ...],
) -> CheckpointExecutionDecision:
    return CheckpointExecutionDecision(
        checkpoint_id=checkpoint.checkpoint_id,
        checkpoint_ref=checkpoint_ref(workspace_root, checkpoint.checkpoint_id),
        fingerprint=checkpoint_fingerprint(checkpoint),
        kernel_action=TargetProductStageAction.REBUILT,
        reference_action=TargetProductStageAction.REFRESHED,
        reference_signature=checkpoint_reference_signature(
            checkpoint=checkpoint,
            reconciliation_states=reconciliation_states,
            evidence_set=evidence_set,
        ),
    )
