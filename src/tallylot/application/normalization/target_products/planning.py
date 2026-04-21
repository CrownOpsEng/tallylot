"""Target-product execution planning."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import cast

from tallylot.application.normalization.contracts import NormalizeUpdateMode
from tallylot.domain.types import JsonValue

from .models import (
    CheckpointExecutionCandidate,
    CheckpointExecutionDecision,
    EconomicFactsExecutionCandidate,
    EconomicFactsExecutionDecision,
    ReconciliationStateExecutionCandidate,
    ReconciliationStateExecutionDecision,
    TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION,
    TargetProductExecutionPlan,
    TargetProductExecutionSummary,
    TargetProductStageAction,
)


@dataclass(frozen=True)
class TargetProductExecutionPlanningRequest:
    summary_path: Path
    update_mode: NormalizeUpdateMode
    claim_set_fingerprint: str
    economic_facts: EconomicFactsExecutionCandidate | None
    reconciliation_states: tuple[ReconciliationStateExecutionCandidate, ...]
    checkpoints: tuple[CheckpointExecutionCandidate, ...]


def load_prior_target_product_execution(
    summary_path: Path,
) -> TargetProductExecutionPlan | None:
    if not summary_path.is_file():
        return None
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    raw_payload = cast(dict[str, JsonValue], payload)
    target_product_execution = raw_payload.get("target_product_execution")
    if not isinstance(target_product_execution, dict):
        return None
    return _plan_from_payload(target_product_execution)


def plan_target_product_execution(
    request: TargetProductExecutionPlanningRequest,
) -> TargetProductExecutionPlan:
    prior_plan = load_prior_target_product_execution(request.summary_path)
    economic_facts_decision = _plan_economic_facts(
        update_mode=request.update_mode,
        prior_plan=prior_plan,
        current=request.economic_facts,
    )
    reconciliation_state_decisions = _plan_reconciliation_states(
        update_mode=request.update_mode,
        prior_plan=prior_plan,
        current=request.reconciliation_states,
        upstream_rebuilt=(
            economic_facts_decision is not None
            and economic_facts_decision.kernel_action
            is TargetProductStageAction.REBUILT
        ),
    )
    checkpoint_decisions = _plan_checkpoints(
        update_mode=request.update_mode,
        prior_plan=prior_plan,
        current=request.checkpoints,
        upstream_rebuilt=any(
            decision.kernel_action is TargetProductStageAction.REBUILT
            for decision in reconciliation_state_decisions
        ),
    )
    current_reconciliation_refs = {
        decision.reconciliation_state_ref for decision in reconciliation_state_decisions
    }
    current_checkpoint_refs = {
        decision.checkpoint_ref for decision in checkpoint_decisions
    }
    return TargetProductExecutionPlan(
        signature_version=TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION,
        update_mode_requested=request.update_mode.value,
        update_mode_effective=request.update_mode.value,
        claim_set_fingerprint=request.claim_set_fingerprint,
        economic_facts=economic_facts_decision,
        reconciliation_states=reconciliation_state_decisions,
        checkpoints=checkpoint_decisions,
        pruned_reconciliation_state_refs=tuple(
            sorted(
                {
                    decision.reconciliation_state_ref
                    for decision in (
                        prior_plan.reconciliation_states if prior_plan else ()
                    )
                }
                - current_reconciliation_refs
            )
        ),
        pruned_checkpoint_refs=tuple(
            sorted(
                {
                    decision.checkpoint_ref
                    for decision in (prior_plan.checkpoints if prior_plan else ())
                }
                - current_checkpoint_refs
            )
        ),
    )


def summarize_target_product_execution(
    plan: TargetProductExecutionPlan,
) -> TargetProductExecutionSummary:
    reused_target_product_count = sum(
        1
        for action in _kernel_actions(plan)
        if action is TargetProductStageAction.REUSED
    )
    rebuilt_target_product_count = sum(
        1
        for action in _kernel_actions(plan)
        if action is TargetProductStageAction.REBUILT
    )
    refreshed_detail_output_count = sum(
        1
        for action in _detail_actions(plan)
        if action is TargetProductStageAction.REFRESHED
    )
    pruned_target_product_count = len(plan.pruned_reconciliation_state_refs) + len(
        plan.pruned_checkpoint_refs
    )
    return TargetProductExecutionSummary(
        reused_target_product_count=reused_target_product_count,
        rebuilt_target_product_count=rebuilt_target_product_count,
        pruned_target_product_count=pruned_target_product_count,
        refreshed_detail_output_count=refreshed_detail_output_count,
    )


def _plan_economic_facts(
    *,
    update_mode: NormalizeUpdateMode,
    prior_plan: TargetProductExecutionPlan | None,
    current: EconomicFactsExecutionCandidate | None,
) -> EconomicFactsExecutionDecision | None:
    if current is None:
        return None
    prior = prior_plan.economic_facts if prior_plan is not None else None
    kernel_action = _decide_kernel_action(
        update_mode=update_mode,
        prior_fingerprint=None if prior is None else prior.fingerprint,
        current_fingerprint=current.fingerprint,
        kernel_exists=current.kernel_path.is_file(),
        upstream_rebuilt=False,
    )
    compatibility_action = _decide_detail_action(
        update_mode=update_mode,
        kernel_action=kernel_action,
        prior_signature=None if prior is None else prior.compatibility_signature,
        current_signature=current.compatibility_signature,
        detail_paths=current.detail_paths,
    )
    return EconomicFactsExecutionDecision(
        economic_facts_id=current.economic_facts_id,
        economic_facts_ref=current.economic_facts_ref,
        fingerprint=current.fingerprint,
        kernel_action=kernel_action,
        compatibility_action=compatibility_action,
        compatibility_signature=current.compatibility_signature,
    )


def _plan_reconciliation_states(
    *,
    update_mode: NormalizeUpdateMode,
    prior_plan: TargetProductExecutionPlan | None,
    current: tuple[ReconciliationStateExecutionCandidate, ...],
    upstream_rebuilt: bool,
) -> tuple[ReconciliationStateExecutionDecision, ...]:
    prior_by_ref = {
        decision.reconciliation_state_ref: decision
        for decision in (prior_plan.reconciliation_states if prior_plan else ())
    }
    decisions: list[ReconciliationStateExecutionDecision] = []
    for candidate in current:
        prior = prior_by_ref.get(candidate.reconciliation_state_ref)
        kernel_action = _decide_kernel_action(
            update_mode=update_mode,
            prior_fingerprint=None if prior is None else prior.fingerprint,
            current_fingerprint=candidate.fingerprint,
            kernel_exists=candidate.kernel_path.is_file(),
            upstream_rebuilt=upstream_rebuilt,
        )
        snapshot_action = _decide_detail_action(
            update_mode=update_mode,
            kernel_action=kernel_action,
            prior_signature=None if prior is None else prior.snapshot_signature,
            current_signature=candidate.snapshot_signature,
            detail_paths=candidate.detail_paths,
        )
        decisions.append(
            ReconciliationStateExecutionDecision(
                reconciliation_state_id=candidate.reconciliation_state_id,
                reconciliation_state_ref=candidate.reconciliation_state_ref,
                fingerprint=candidate.fingerprint,
                kernel_action=kernel_action,
                snapshot_action=snapshot_action,
                snapshot_signature=candidate.snapshot_signature,
            )
        )
    return tuple(decisions)


def _plan_checkpoints(
    *,
    update_mode: NormalizeUpdateMode,
    prior_plan: TargetProductExecutionPlan | None,
    current: tuple[CheckpointExecutionCandidate, ...],
    upstream_rebuilt: bool,
) -> tuple[CheckpointExecutionDecision, ...]:
    prior_by_ref = {
        decision.checkpoint_ref: decision
        for decision in (prior_plan.checkpoints if prior_plan else ())
    }
    decisions: list[CheckpointExecutionDecision] = []
    for candidate in current:
        prior = prior_by_ref.get(candidate.checkpoint_ref)
        kernel_action = _decide_kernel_action(
            update_mode=update_mode,
            prior_fingerprint=None if prior is None else prior.fingerprint,
            current_fingerprint=candidate.fingerprint,
            kernel_exists=candidate.kernel_path.is_file(),
            upstream_rebuilt=upstream_rebuilt,
        )
        reference_action = _decide_detail_action(
            update_mode=update_mode,
            kernel_action=kernel_action,
            prior_signature=None if prior is None else prior.reference_signature,
            current_signature=candidate.reference_signature,
            detail_paths=candidate.detail_paths,
        )
        decisions.append(
            CheckpointExecutionDecision(
                checkpoint_id=candidate.checkpoint_id,
                checkpoint_ref=candidate.checkpoint_ref,
                fingerprint=candidate.fingerprint,
                kernel_action=kernel_action,
                reference_action=reference_action,
                reference_signature=candidate.reference_signature,
            )
        )
    return tuple(decisions)


def _decide_kernel_action(
    *,
    update_mode: NormalizeUpdateMode,
    prior_fingerprint: str | None,
    current_fingerprint: str,
    kernel_exists: bool,
    upstream_rebuilt: bool,
) -> TargetProductStageAction:
    if update_mode is NormalizeUpdateMode.REBUILD:
        return TargetProductStageAction.REBUILT
    if (
        upstream_rebuilt
        or not kernel_exists
        or prior_fingerprint != current_fingerprint
    ):
        return TargetProductStageAction.REBUILT
    return TargetProductStageAction.REUSED


def _decide_detail_action(
    *,
    update_mode: NormalizeUpdateMode,
    kernel_action: TargetProductStageAction,
    prior_signature: str | None,
    current_signature: str,
    detail_paths: tuple[Path, ...],
) -> TargetProductStageAction:
    if update_mode in {
        NormalizeUpdateMode.FULL_UPDATE,
        NormalizeUpdateMode.REBUILD,
    }:
        return TargetProductStageAction.REFRESHED
    if kernel_action is TargetProductStageAction.REBUILT:
        return TargetProductStageAction.REFRESHED
    if prior_signature != current_signature:
        return TargetProductStageAction.REFRESHED
    if detail_paths and not all(path.is_file() for path in detail_paths):
        return TargetProductStageAction.REFRESHED
    return TargetProductStageAction.REUSED


def _kernel_actions(
    plan: TargetProductExecutionPlan,
) -> tuple[TargetProductStageAction, ...]:
    actions: list[TargetProductStageAction] = []
    if plan.economic_facts is not None:
        actions.append(plan.economic_facts.kernel_action)
    actions.extend(decision.kernel_action for decision in plan.reconciliation_states)
    actions.extend(decision.kernel_action for decision in plan.checkpoints)
    return tuple(actions)


def _detail_actions(
    plan: TargetProductExecutionPlan,
) -> tuple[TargetProductStageAction, ...]:
    actions: list[TargetProductStageAction] = []
    if plan.economic_facts is not None:
        actions.append(plan.economic_facts.compatibility_action)
    actions.extend(decision.snapshot_action for decision in plan.reconciliation_states)
    actions.extend(decision.reference_action for decision in plan.checkpoints)
    return tuple(actions)


def _plan_from_payload(payload: dict[str, JsonValue]) -> TargetProductExecutionPlan:
    return TargetProductExecutionPlan(
        signature_version=str(payload.get("signature_version", "")),
        update_mode_requested=str(payload.get("update_mode_requested", "")),
        update_mode_effective=str(payload.get("update_mode_effective", "")),
        claim_set_fingerprint=str(payload.get("claim_set_fingerprint", "")),
        economic_facts=_economic_facts_from_payload(payload.get("economic_facts")),
        reconciliation_states=tuple(
            _reconciliation_state_from_payload(item)
            for item in _required_list(payload, "reconciliation_states")
        ),
        checkpoints=tuple(
            _checkpoint_from_payload(item)
            for item in _required_list(payload, "checkpoints")
        ),
        pruned_reconciliation_state_refs=_string_tuple(
            payload.get("pruned_reconciliation_state_refs")
        ),
        pruned_checkpoint_refs=_string_tuple(payload.get("pruned_checkpoint_refs")),
    )


def _economic_facts_from_payload(
    payload: object,
) -> EconomicFactsExecutionDecision | None:
    if not isinstance(payload, dict):
        return None
    raw = cast(dict[str, JsonValue], payload)
    return EconomicFactsExecutionDecision(
        economic_facts_id=str(raw.get("economic_facts_id", "")),
        economic_facts_ref=str(raw.get("economic_facts_ref", "")),
        fingerprint=str(raw.get("fingerprint", "")),
        kernel_action=TargetProductStageAction(
            str(raw.get("kernel_action", "rebuilt"))
        ),
        compatibility_action=TargetProductStageAction(
            str(raw.get("compatibility_action", "refreshed"))
        ),
        compatibility_signature=str(raw.get("compatibility_signature", "")),
    )


def _reconciliation_state_from_payload(
    payload: object,
) -> ReconciliationStateExecutionDecision:
    raw = cast(dict[str, JsonValue], payload)
    return ReconciliationStateExecutionDecision(
        reconciliation_state_id=str(raw.get("reconciliation_state_id", "")),
        reconciliation_state_ref=str(raw.get("reconciliation_state_ref", "")),
        fingerprint=str(raw.get("fingerprint", "")),
        kernel_action=TargetProductStageAction(
            str(raw.get("kernel_action", "rebuilt"))
        ),
        snapshot_action=TargetProductStageAction(
            str(raw.get("snapshot_action", "refreshed"))
        ),
        snapshot_signature=str(raw.get("snapshot_signature", "")),
    )


def _checkpoint_from_payload(payload: object) -> CheckpointExecutionDecision:
    raw = cast(dict[str, JsonValue], payload)
    return CheckpointExecutionDecision(
        checkpoint_id=str(raw.get("checkpoint_id", "")),
        checkpoint_ref=str(raw.get("checkpoint_ref", "")),
        fingerprint=str(raw.get("fingerprint", "")),
        kernel_action=TargetProductStageAction(
            str(raw.get("kernel_action", "rebuilt"))
        ),
        reference_action=TargetProductStageAction(
            str(raw.get("reference_action", "refreshed"))
        ),
        reference_signature=str(raw.get("reference_signature", "")),
    )


def _required_list(payload: dict[str, JsonValue], key: str) -> list[object]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return cast(list[object], value)


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    items = cast(list[object], value)
    string_items: list[str] = []
    for raw_item in items:
        if isinstance(raw_item, str):
            string_items.append(raw_item)
    return tuple(string_items)
