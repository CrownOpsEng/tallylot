"""Target-product execution orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
from tallylot.domain.transactions import TransactionFact
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.checkpoints import CheckpointRepositoryPort
from tallylot.ports.economic_facts import EconomicFactsRepositoryPort
from tallylot.ports.evidence import EvidenceRepositoryPort
from tallylot.ports.facts import FactRepositoryPort
from tallylot.ports.reconciliation_states import ReconciliationStateRepositoryPort

from ..annotations import FactAnnotationRecord
from .models import TargetProductExecutionSummary


@dataclass(frozen=True)
class TargetProductExecutionResult:
    economic_facts_id: str = ""
    economic_facts_ref: str = ""
    reconciliation_state_ids: tuple[str, ...] = ()
    reconciliation_state_refs: tuple[str, ...] = ()
    checkpoint_ids: tuple[str, ...] = ()
    checkpoint_refs: tuple[str, ...] = ()
    facts: tuple[TransactionFact, ...] = ()
    fact_annotations: tuple[FactAnnotationRecord, ...] = ()
    balance_snapshots: tuple[BalanceSnapshot, ...] = ()
    balance_references: tuple[BalanceReference, ...] = ()
    execution_summary: TargetProductExecutionSummary = TargetProductExecutionSummary(
        reused_target_product_count=0,
        rebuilt_target_product_count=0,
        pruned_target_product_count=0,
        refreshed_detail_output_count=0,
    )
    update_mode_requested: str = NormalizeUpdateMode.AUTO.value
    update_mode_effective: str = NormalizeUpdateMode.AUTO.value


@dataclass(frozen=True)
class TargetProductDependencies:
    facts: FactRepositoryPort
    evidence: EvidenceRepositoryPort
    economic_facts: EconomicFactsRepositoryPort
    reconciliation_states: ReconciliationStateRepositoryPort
    checkpoints: CheckpointRepositoryPort
    artifacts: ArtifactStorePort


def build_target_product_execution(
    *,
    workspace_root: Path,
    update_mode: NormalizeUpdateMode,
    translation_result: TranslationExecutionResult,
    dependencies: TargetProductDependencies,
) -> TargetProductExecutionResult:
    claim_set = translation_result.claim_set
    evidence_set = translation_result.evidence_set
    if (
        claim_set is None
        or evidence_set is None
        or translation_result.claim_set_ref == ""
    ):
        return TargetProductExecutionResult(
            update_mode_requested=update_mode.value,
            update_mode_effective=update_mode.value,
        )
    economic_facts = build_economic_facts(claim_set=claim_set)
    dependencies.economic_facts.write_economic_facts(
        economic_facts_product_file(workspace_root, economic_facts.economic_facts_id),
        economic_facts,
    )
    economic_facts_ref_value = economic_facts_ref(
        workspace_root,
        economic_facts.economic_facts_id,
    )
    economic_compatibility = project_compatibility_artifacts_from_economic_facts(
        economic_facts=economic_facts,
        claim_set=claim_set,
        evidence_set=evidence_set,
        draft_projection_field_records=translation_result.draft_projection_field_records,
    )
    dependencies.facts.write_facts(
        economic_facts_compatibility_facts_file(
            workspace_root,
            economic_facts.economic_facts_id,
        ),
        economic_compatibility.facts,
    )
    dependencies.artifacts.write_json(
        economic_facts_compatibility_fact_annotations_file(
            workspace_root,
            economic_facts.economic_facts_id,
        ),
        [record.to_json() for record in economic_compatibility.fact_annotations],
    )
    reconciliation_states = build_reconciliation_states(
        economic_facts=economic_facts,
        claim_set=claim_set,
        evidence_set=evidence_set,
    )
    snapshot_rows: list[BalanceSnapshot] = []
    reconciliation_state_ids: list[str] = []
    reconciliation_state_refs: list[str] = []
    for state in reconciliation_states:
        reconciliation_state_ids.append(state.reconciliation_state_id)
        reconciliation_state_refs.append(
            reconciliation_state_ref(workspace_root, state.reconciliation_state_id)
        )
        dependencies.reconciliation_states.write_reconciliation_state(
            reconciliation_state_product_file(
                workspace_root,
                state.reconciliation_state_id,
            ),
            state,
        )
        projected_snapshots = project_balance_snapshots_from_reconciliation_state(state)
        dependencies.evidence.write_balance_snapshots(
            reconciliation_state_compatibility_snapshots_file(
                workspace_root,
                state.reconciliation_state_id,
            ),
            projected_snapshots,
        )
        snapshot_rows.extend(projected_snapshots)
    observation_details = observation_details_from_evidence_set(evidence_set)
    checkpoints = build_checkpoints(reconciliation_states=reconciliation_states)
    reference_rows: list[BalanceReference] = []
    checkpoint_ids: list[str] = []
    checkpoint_refs: list[str] = []
    for checkpoint in checkpoints:
        checkpoint_ids.append(checkpoint.checkpoint_id)
        checkpoint_refs.append(checkpoint_ref(workspace_root, checkpoint.checkpoint_id))
        dependencies.checkpoints.write_checkpoint(
            checkpoint_product_file(workspace_root, checkpoint.checkpoint_id),
            checkpoint,
        )
        projected_references = project_balance_references_from_checkpoint(
            checkpoint=checkpoint,
            reconciliation_states=reconciliation_states,
            observation_details=observation_details,
        )
        dependencies.evidence.write_balance_references(
            checkpoint_compatibility_references_file(
                workspace_root,
                checkpoint.checkpoint_id,
            ),
            projected_references,
        )
        reference_rows.extend(projected_references)
    return TargetProductExecutionResult(
        economic_facts_id=economic_facts.economic_facts_id,
        economic_facts_ref=economic_facts_ref_value,
        reconciliation_state_ids=tuple(reconciliation_state_ids),
        reconciliation_state_refs=tuple(reconciliation_state_refs),
        checkpoint_ids=tuple(checkpoint_ids),
        checkpoint_refs=tuple(checkpoint_refs),
        facts=economic_compatibility.facts,
        fact_annotations=economic_compatibility.fact_annotations,
        balance_snapshots=_ordered_snapshots(snapshot_rows),
        balance_references=_ordered_references(reference_rows),
        execution_summary=TargetProductExecutionSummary(
            reused_target_product_count=0,
            rebuilt_target_product_count=(
                (1 if economic_facts.economic_facts_id else 0)
                + len(reconciliation_state_ids)
                + len(checkpoint_ids)
            ),
            pruned_target_product_count=0,
            refreshed_detail_output_count=(
                (1 if economic_facts.economic_facts_id else 0)
                + len(reconciliation_state_ids)
                + len(checkpoint_ids)
            ),
        ),
        update_mode_requested=update_mode.value,
        update_mode_effective=update_mode.value,
    )


def _ordered_snapshots(
    snapshot_rows: list[BalanceSnapshot],
) -> tuple[BalanceSnapshot, ...]:
    return tuple(
        sorted(
            snapshot_rows,
            key=lambda item: (
                str(item.target.source),
                str(item.target.location_id),
                str(item.target.instrument_id),
                item.target.balance_kind,
                item.target.target_at,
            ),
        )
    )


def _ordered_references(
    reference_rows: list[BalanceReference],
) -> tuple[BalanceReference, ...]:
    return tuple(
        sorted(
            reference_rows,
            key=lambda item: (
                str(item.target.source),
                str(item.target.location_id),
                str(item.target.instrument_id),
                item.target.balance_kind,
                item.target.target_at,
                item.support_ref,
            ),
        )
    )
