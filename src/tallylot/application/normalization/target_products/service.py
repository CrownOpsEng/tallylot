"""Target-product execution orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tallylot.application.normalization.contracts import NormalizeUpdateMode
from tallylot.application.normalization.translation import TranslationExecutionResult
from tallylot.domain.balances import BalanceReference, BalanceSnapshot
from tallylot.domain.transactions import TransactionFact
from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.checkpoints import CheckpointRepositoryPort
from tallylot.ports.economic_facts import EconomicFactsRepositoryPort
from tallylot.ports.evidence import EvidenceRepositoryPort
from tallylot.ports.facts import FactRepositoryPort
from tallylot.ports.reconciliation_states import ReconciliationStateRepositoryPort

from ..annotations import FactAnnotationRecord
from .cleanup import prune_product_roots, pruned_refs
from .models import (
    TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION,
    TargetProductExecutionPlan,
    TargetProductExecutionSummary,
)
from .planning import (
    load_prior_target_product_execution,
    summarize_target_product_execution,
)
from .payloads import execution_plan_payload
from .runtime import (
    CheckpointResolutionRequest,
    EconomicFactsResolutionRequest,
    ReconciliationStateResolutionRequest,
    resolve_checkpoints,
    resolve_economic_facts,
    resolve_reconciliation_states,
)
from .signatures import claim_set_execution_fingerprint


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
    execution_plan_payload: JsonValue | None = None
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
    normalization_output_dir: Path,
    update_mode: NormalizeUpdateMode,
    translation_result: TranslationExecutionResult,
    dependencies: TargetProductDependencies,
) -> TargetProductExecutionResult:
    summary_path = normalization_output_dir / "normalization_summary.json"
    prior_plan = load_prior_target_product_execution(summary_path)
    pruned_economic_facts_refs = _pruned_economic_facts_refs(prior_plan, "")
    claim_set = translation_result.claim_set
    evidence_set = translation_result.evidence_set
    if (
        claim_set is None
        or evidence_set is None
        or translation_result.claim_set_ref == ""
    ):
        if prior_plan is None:
            return TargetProductExecutionResult(
                update_mode_requested=update_mode.value,
                update_mode_effective=update_mode.value,
            )
        pruned_reconciliation_state_refs = tuple(
            decision.reconciliation_state_ref
            for decision in prior_plan.reconciliation_states
        )
        pruned_checkpoint_refs = tuple(
            decision.checkpoint_ref for decision in prior_plan.checkpoints
        )
        prune_product_roots(workspace_root, pruned_economic_facts_refs)
        prune_product_roots(workspace_root, pruned_reconciliation_state_refs)
        prune_product_roots(workspace_root, pruned_checkpoint_refs)
        execution_plan = TargetProductExecutionPlan(
            signature_version=TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION,
            update_mode_requested=update_mode.value,
            update_mode_effective=update_mode.value,
            claim_set_fingerprint="",
            economic_facts=None,
            reconciliation_states=(),
            checkpoints=(),
            pruned_reconciliation_state_refs=pruned_reconciliation_state_refs,
            pruned_checkpoint_refs=pruned_checkpoint_refs,
        )
        return TargetProductExecutionResult(
            execution_summary=_execution_summary_with_economic_fact_prunes(
                summarize_target_product_execution(execution_plan),
                pruned_economic_facts_refs,
            ),
            execution_plan_payload=execution_plan_payload(execution_plan),
            update_mode_requested=update_mode.value,
            update_mode_effective=update_mode.value,
        )

    claim_set_fingerprint = claim_set_execution_fingerprint(claim_set)

    (
        economic_facts,
        economic_facts_decision,
        economic_facts_compatibility,
    ) = resolve_economic_facts(
        EconomicFactsResolutionRequest(
            workspace_root=workspace_root,
            update_mode=update_mode,
            claim_set=claim_set,
            claim_set_fingerprint=claim_set_fingerprint,
            evidence_set=evidence_set,
            translation_result=translation_result,
            prior_plan=prior_plan,
            dependencies=dependencies,
        )
    )
    (
        reconciliation_states,
        reconciliation_state_decisions,
        balance_snapshots,
    ) = resolve_reconciliation_states(
        ReconciliationStateResolutionRequest(
            workspace_root=workspace_root,
            update_mode=update_mode,
            claim_set=claim_set,
            claim_set_fingerprint=claim_set_fingerprint,
            evidence_set=evidence_set,
            economic_facts=economic_facts,
            economic_facts_reused=(
                economic_facts_decision.kernel_action.value == "reused"
            ),
            prior_plan=prior_plan,
            dependencies=dependencies,
        )
    )
    checkpoints, checkpoint_decisions, balance_references = resolve_checkpoints(
        CheckpointResolutionRequest(
            workspace_root=workspace_root,
            update_mode=update_mode,
            claim_set_fingerprint=claim_set_fingerprint,
            evidence_set=evidence_set,
            reconciliation_states=reconciliation_states,
            reconciliation_states_reused=all(
                decision.kernel_action.value == "reused"
                for decision in reconciliation_state_decisions
            ),
            prior_plan=prior_plan,
            dependencies=dependencies,
        )
    )

    pruned_reconciliation_state_refs = pruned_refs(
        prior_refs=(
            ()
            if prior_plan is None
            else tuple(
                decision.reconciliation_state_ref
                for decision in prior_plan.reconciliation_states
            )
        ),
        current_refs=tuple(
            decision.reconciliation_state_ref
            for decision in reconciliation_state_decisions
        ),
    )
    pruned_checkpoint_refs = pruned_refs(
        prior_refs=(
            ()
            if prior_plan is None
            else tuple(decision.checkpoint_ref for decision in prior_plan.checkpoints)
        ),
        current_refs=tuple(
            decision.checkpoint_ref for decision in checkpoint_decisions
        ),
    )
    pruned_economic_facts_refs = _pruned_economic_facts_refs(
        prior_plan,
        economic_facts_decision.economic_facts_ref,
    )
    prune_product_roots(workspace_root, pruned_economic_facts_refs)
    prune_product_roots(workspace_root, pruned_reconciliation_state_refs)
    prune_product_roots(workspace_root, pruned_checkpoint_refs)

    execution_plan = TargetProductExecutionPlan(
        signature_version=TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION,
        update_mode_requested=update_mode.value,
        update_mode_effective=update_mode.value,
        claim_set_fingerprint=claim_set_fingerprint,
        economic_facts=economic_facts_decision,
        reconciliation_states=reconciliation_state_decisions,
        checkpoints=checkpoint_decisions,
        pruned_reconciliation_state_refs=pruned_reconciliation_state_refs,
        pruned_checkpoint_refs=pruned_checkpoint_refs,
    )
    execution_summary = _execution_summary_with_economic_fact_prunes(
        summarize_target_product_execution(execution_plan),
        pruned_economic_facts_refs,
    )
    return TargetProductExecutionResult(
        economic_facts_id=economic_facts.economic_facts_id,
        economic_facts_ref=economic_facts_decision.economic_facts_ref,
        reconciliation_state_ids=tuple(
            state.reconciliation_state_id for state in reconciliation_states
        ),
        reconciliation_state_refs=tuple(
            decision.reconciliation_state_ref
            for decision in reconciliation_state_decisions
        ),
        checkpoint_ids=tuple(checkpoint.checkpoint_id for checkpoint in checkpoints),
        checkpoint_refs=tuple(
            decision.checkpoint_ref for decision in checkpoint_decisions
        ),
        facts=economic_facts_compatibility.facts,
        fact_annotations=economic_facts_compatibility.fact_annotations,
        balance_snapshots=_ordered_snapshots(list(balance_snapshots)),
        balance_references=_ordered_references(list(balance_references)),
        execution_summary=execution_summary,
        execution_plan_payload=execution_plan_payload(execution_plan),
        update_mode_requested=update_mode.value,
        update_mode_effective=update_mode.value,
    )


def _execution_summary_with_economic_fact_prunes(
    summary: TargetProductExecutionSummary,
    pruned_economic_facts_refs: tuple[str, ...],
) -> TargetProductExecutionSummary:
    if not pruned_economic_facts_refs:
        return summary
    return TargetProductExecutionSummary(
        reused_target_product_count=summary.reused_target_product_count,
        rebuilt_target_product_count=summary.rebuilt_target_product_count,
        pruned_target_product_count=(
            summary.pruned_target_product_count + len(pruned_economic_facts_refs)
        ),
        refreshed_detail_output_count=summary.refreshed_detail_output_count,
    )


def _pruned_economic_facts_refs(
    prior_plan: TargetProductExecutionPlan | None,
    current_economic_facts_ref: str,
) -> tuple[str, ...]:
    if prior_plan is None or prior_plan.economic_facts is None:
        return ()
    prior_ref = prior_plan.economic_facts.economic_facts_ref
    if prior_ref in {"", current_economic_facts_ref}:
        return ()
    return (prior_ref,)


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
