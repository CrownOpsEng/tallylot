from __future__ import annotations

import json
from pathlib import Path

from tallylot.application.normalization.contracts import NormalizeUpdateMode
from tallylot.application.normalization.target_products import (
    CheckpointExecutionCandidate,
    EconomicFactsExecutionCandidate,
    ReconciliationStateExecutionCandidate,
    TargetProductExecutionPlan,
    TargetProductExecutionPlanningRequest,
    TargetProductStageAction,
    plan_target_product_execution,
)
from tallylot.application.normalization.target_products.payloads import (
    read_fact_annotations,
)


def test_auto_mode_marks_stage_for_reuse_when_signature_matches_and_persisted_root_exists(
    tmp_path: Path,
) -> None:
    kernel_path = (
        tmp_path
        / "working"
        / "products"
        / "economic_facts"
        / "facts-1"
        / "economic_facts.json"
    )
    detail_path = (
        tmp_path
        / "working"
        / "products"
        / "economic_facts"
        / "facts-1"
        / "compatibility"
        / "facts.csv"
    )
    _touch(kernel_path)
    _touch(detail_path)
    summary_path = tmp_path / "normalized" / "normalization_summary.json"
    _write_summary(
        summary_path,
        economic_facts={
            "economic_facts_id": "facts-1",
            "economic_facts_ref": "working/products/economic_facts/facts-1/economic_facts.json",
            "fingerprint": "facts-fingerprint",
            "kernel_action": "rebuilt",
            "compatibility_action": "refreshed",
            "compatibility_signature": "compatibility-signature",
        },
    )

    plan = _plan_execution(
        summary_path=summary_path,
        update_mode=NormalizeUpdateMode.AUTO,
        claim_set_fingerprint="claim-set-fingerprint",
        economic_facts=EconomicFactsExecutionCandidate(
            economic_facts_id="facts-1",
            economic_facts_ref="working/products/economic_facts/facts-1/economic_facts.json",
            fingerprint="facts-fingerprint",
            compatibility_signature="compatibility-signature",
            kernel_path=kernel_path,
            detail_paths=(detail_path,),
        ),
        reconciliation_states=(),
        checkpoints=(),
    )

    assert plan.economic_facts is not None
    assert plan.economic_facts.kernel_action is TargetProductStageAction.REUSED


def test_auto_mode_marks_stage_for_rebuild_when_signature_changes(
    tmp_path: Path,
) -> None:
    facts_kernel = tmp_path / "facts.json"
    facts_detail = tmp_path / "facts.csv"
    state_kernel = tmp_path / "state.json"
    state_detail = tmp_path / "snapshots.csv"
    _touch(facts_kernel)
    _touch(facts_detail)
    _touch(state_kernel)
    _touch(state_detail)
    summary_path = tmp_path / "normalization_summary.json"
    _write_summary(
        summary_path,
        economic_facts={
            "economic_facts_id": "facts-1",
            "economic_facts_ref": "facts.json",
            "fingerprint": "old-facts",
            "kernel_action": "rebuilt",
            "compatibility_action": "refreshed",
            "compatibility_signature": "same-detail",
        },
        reconciliation_states=[
            {
                "reconciliation_state_id": "state-1",
                "reconciliation_state_ref": "state.json",
                "fingerprint": "state-fingerprint",
                "kernel_action": "rebuilt",
                "snapshot_action": "refreshed",
                "snapshot_signature": "snapshot-signature",
            }
        ],
    )

    plan = _plan_execution(
        summary_path=summary_path,
        update_mode=NormalizeUpdateMode.AUTO,
        claim_set_fingerprint="claim-set-fingerprint",
        economic_facts=EconomicFactsExecutionCandidate(
            economic_facts_id="facts-1",
            economic_facts_ref="facts.json",
            fingerprint="new-facts",
            compatibility_signature="same-detail",
            kernel_path=facts_kernel,
            detail_paths=(facts_detail,),
        ),
        reconciliation_states=(
            ReconciliationStateExecutionCandidate(
                reconciliation_state_id="state-1",
                reconciliation_state_ref="state.json",
                fingerprint="state-fingerprint",
                snapshot_signature="snapshot-signature",
                kernel_path=state_kernel,
                detail_paths=(state_detail,),
            ),
        ),
        checkpoints=(),
    )

    assert plan.economic_facts is not None
    assert plan.economic_facts.kernel_action is TargetProductStageAction.REBUILT
    assert (
        plan.reconciliation_states[0].kernel_action is TargetProductStageAction.REBUILT
    )


def test_auto_mode_downgrades_reuse_to_rebuild_when_persisted_file_is_missing(
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "normalization_summary.json"
    _write_summary(
        summary_path,
        economic_facts={
            "economic_facts_id": "facts-1",
            "economic_facts_ref": "facts.json",
            "fingerprint": "facts-fingerprint",
            "kernel_action": "rebuilt",
            "compatibility_action": "refreshed",
            "compatibility_signature": "compatibility-signature",
        },
    )

    plan = _plan_execution(
        summary_path=summary_path,
        update_mode=NormalizeUpdateMode.AUTO,
        claim_set_fingerprint="claim-set-fingerprint",
        economic_facts=EconomicFactsExecutionCandidate(
            economic_facts_id="facts-1",
            economic_facts_ref="facts.json",
            fingerprint="facts-fingerprint",
            compatibility_signature="compatibility-signature",
            kernel_path=tmp_path / "missing-facts.json",
            detail_paths=(),
        ),
        reconciliation_states=(),
        checkpoints=(),
    )

    assert plan.economic_facts is not None
    assert plan.economic_facts.kernel_action is TargetProductStageAction.REBUILT


def test_full_update_reuses_kernel_but_marks_detail_outputs_for_refresh(
    tmp_path: Path,
) -> None:
    kernel_path = tmp_path / "facts.json"
    detail_path = tmp_path / "facts.csv"
    _touch(kernel_path)
    _touch(detail_path)
    summary_path = tmp_path / "normalization_summary.json"
    _write_summary(
        summary_path,
        economic_facts={
            "economic_facts_id": "facts-1",
            "economic_facts_ref": "facts.json",
            "fingerprint": "facts-fingerprint",
            "kernel_action": "rebuilt",
            "compatibility_action": "reused",
            "compatibility_signature": "compatibility-signature",
        },
    )

    plan = _plan_execution(
        summary_path=summary_path,
        update_mode=NormalizeUpdateMode.FULL_UPDATE,
        claim_set_fingerprint="claim-set-fingerprint",
        economic_facts=EconomicFactsExecutionCandidate(
            economic_facts_id="facts-1",
            economic_facts_ref="facts.json",
            fingerprint="facts-fingerprint",
            compatibility_signature="compatibility-signature",
            kernel_path=kernel_path,
            detail_paths=(detail_path,),
        ),
        reconciliation_states=(),
        checkpoints=(),
    )

    assert plan.economic_facts is not None
    assert plan.economic_facts.kernel_action is TargetProductStageAction.REUSED
    assert (
        plan.economic_facts.compatibility_action is TargetProductStageAction.REFRESHED
    )


def test_rebuild_mode_marks_all_authoritative_and_detail_stages_for_rebuild(
    tmp_path: Path,
) -> None:
    facts_kernel = tmp_path / "facts.json"
    facts_detail = tmp_path / "facts.csv"
    state_kernel = tmp_path / "state.json"
    state_detail = tmp_path / "snapshots.csv"
    checkpoint_kernel = tmp_path / "checkpoint.json"
    checkpoint_detail = tmp_path / "references.csv"
    for path in (
        facts_kernel,
        facts_detail,
        state_kernel,
        state_detail,
        checkpoint_kernel,
        checkpoint_detail,
    ):
        _touch(path)

    plan = _plan_execution(
        summary_path=tmp_path / "normalization_summary.json",
        update_mode=NormalizeUpdateMode.REBUILD,
        claim_set_fingerprint="claim-set-fingerprint",
        economic_facts=EconomicFactsExecutionCandidate(
            economic_facts_id="facts-1",
            economic_facts_ref="facts.json",
            fingerprint="facts-fingerprint",
            compatibility_signature="compatibility-signature",
            kernel_path=facts_kernel,
            detail_paths=(facts_detail,),
        ),
        reconciliation_states=(
            ReconciliationStateExecutionCandidate(
                reconciliation_state_id="state-1",
                reconciliation_state_ref="state.json",
                fingerprint="state-fingerprint",
                snapshot_signature="snapshot-signature",
                kernel_path=state_kernel,
                detail_paths=(state_detail,),
            ),
        ),
        checkpoints=(
            CheckpointExecutionCandidate(
                checkpoint_id="checkpoint-1",
                checkpoint_ref="checkpoint.json",
                fingerprint="checkpoint-fingerprint",
                reference_signature="reference-signature",
                kernel_path=checkpoint_kernel,
                detail_paths=(checkpoint_detail,),
            ),
        ),
    )

    assert plan.economic_facts is not None
    assert plan.economic_facts.kernel_action is TargetProductStageAction.REBUILT
    assert all(
        decision.kernel_action is TargetProductStageAction.REBUILT
        for decision in plan.reconciliation_states
    )
    assert all(
        decision.kernel_action is TargetProductStageAction.REBUILT
        for decision in plan.checkpoints
    )
    assert (
        plan.economic_facts.compatibility_action is TargetProductStageAction.REFRESHED
    )
    assert (
        plan.reconciliation_states[0].snapshot_action
        is TargetProductStageAction.REFRESHED
    )
    assert plan.checkpoints[0].reference_action is TargetProductStageAction.REFRESHED


def test_planner_marks_stale_reconciliation_state_refs_for_prune(
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "normalization_summary.json"
    _write_summary(
        summary_path,
        reconciliation_states=[
            {
                "reconciliation_state_id": "state-1",
                "reconciliation_state_ref": "state-1.json",
                "fingerprint": "one",
                "kernel_action": "rebuilt",
                "snapshot_action": "refreshed",
                "snapshot_signature": "one",
            },
            {
                "reconciliation_state_id": "state-2",
                "reconciliation_state_ref": "state-2.json",
                "fingerprint": "two",
                "kernel_action": "rebuilt",
                "snapshot_action": "refreshed",
                "snapshot_signature": "two",
            },
        ],
    )
    state_kernel = tmp_path / "state-2.json"
    _touch(state_kernel)

    plan = _plan_execution(
        summary_path=summary_path,
        update_mode=NormalizeUpdateMode.AUTO,
        claim_set_fingerprint="claim-set-fingerprint",
        economic_facts=None,
        reconciliation_states=(
            ReconciliationStateExecutionCandidate(
                reconciliation_state_id="state-2",
                reconciliation_state_ref="state-2.json",
                fingerprint="two",
                snapshot_signature="two",
                kernel_path=state_kernel,
                detail_paths=(),
            ),
        ),
        checkpoints=(),
    )

    assert plan.pruned_reconciliation_state_refs == ("state-1.json",)


def test_planner_marks_stale_checkpoint_refs_for_prune(tmp_path: Path) -> None:
    summary_path = tmp_path / "normalization_summary.json"
    _write_summary(
        summary_path,
        checkpoints=[
            {
                "checkpoint_id": "checkpoint-1",
                "checkpoint_ref": "checkpoint-1.json",
                "fingerprint": "one",
                "kernel_action": "rebuilt",
                "reference_action": "refreshed",
                "reference_signature": "one",
            },
            {
                "checkpoint_id": "checkpoint-2",
                "checkpoint_ref": "checkpoint-2.json",
                "fingerprint": "two",
                "kernel_action": "rebuilt",
                "reference_action": "refreshed",
                "reference_signature": "two",
            },
        ],
    )
    checkpoint_kernel = tmp_path / "checkpoint-2.json"
    _touch(checkpoint_kernel)

    plan = _plan_execution(
        summary_path=summary_path,
        update_mode=NormalizeUpdateMode.AUTO,
        claim_set_fingerprint="claim-set-fingerprint",
        economic_facts=None,
        reconciliation_states=(),
        checkpoints=(
            CheckpointExecutionCandidate(
                checkpoint_id="checkpoint-2",
                checkpoint_ref="checkpoint-2.json",
                fingerprint="two",
                reference_signature="two",
                kernel_path=checkpoint_kernel,
                detail_paths=(),
            ),
        ),
    )

    assert plan.pruned_checkpoint_refs == ("checkpoint-1.json",)


def test_planner_ignores_prior_execution_with_unknown_signature_version(
    tmp_path: Path,
) -> None:
    kernel_path = tmp_path / "facts.json"
    _touch(kernel_path)
    summary_path = tmp_path / "normalization_summary.json"
    _write_summary(
        summary_path,
        signature_version="normalization-target-products-v2",
        economic_facts={
            "economic_facts_id": "facts-1",
            "economic_facts_ref": "facts.json",
            "fingerprint": "facts-fingerprint",
            "kernel_action": "rebuilt",
            "compatibility_action": "refreshed",
            "compatibility_signature": "compatibility-signature",
        },
    )

    plan = _plan_execution(
        summary_path=summary_path,
        update_mode=NormalizeUpdateMode.AUTO,
        claim_set_fingerprint="claim-set-fingerprint",
        economic_facts=EconomicFactsExecutionCandidate(
            economic_facts_id="facts-1",
            economic_facts_ref="facts.json",
            fingerprint="facts-fingerprint",
            compatibility_signature="compatibility-signature",
            kernel_path=kernel_path,
            detail_paths=(),
        ),
        reconciliation_states=(),
        checkpoints=(),
    )

    assert plan.economic_facts is not None
    assert plan.economic_facts.kernel_action is TargetProductStageAction.REBUILT


def test_read_fact_annotations_preserves_adapter_metadata(tmp_path: Path) -> None:
    path = tmp_path / "fact_annotations.json"
    path.write_text(
        json.dumps(
            [
                {
                    "fact_id": "fact-1",
                    "provenance_refs": ["prov-1"],
                    "review_markers": ["review-1"],
                    "adapter_metadata": [
                        {
                            "namespace": "coinbase",
                            "values": {"note": "keep-me"},
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    records = read_fact_annotations(path)

    assert len(records) == 1
    assert records[0].to_json() == {
        "fact_id": "fact-1",
        "provenance_refs": ["prov-1"],
        "review_markers": ["review-1"],
        "adapter_metadata": [
            {
                "namespace": "coinbase",
                "values": {"note": "keep-me"},
            }
        ],
    }


def _write_summary(
    path: Path,
    *,
    signature_version: str = "normalization-target-products-v1",
    economic_facts: dict[str, object] | None = None,
    reconciliation_states: list[dict[str, object]] | None = None,
    checkpoints: list[dict[str, object]] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "target_product_execution": {
                    "signature_version": signature_version,
                    "update_mode_requested": "auto",
                    "update_mode_effective": "auto",
                    "claim_set_fingerprint": "claim-set-fingerprint",
                    "economic_facts": economic_facts,
                    "reconciliation_states": reconciliation_states or [],
                    "checkpoints": checkpoints or [],
                    "pruned_reconciliation_state_refs": [],
                    "pruned_checkpoint_refs": [],
                }
            }
        ),
        encoding="utf-8",
    )


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")


def _plan_execution(
    *,
    summary_path: Path,
    update_mode: NormalizeUpdateMode,
    claim_set_fingerprint: str,
    economic_facts: EconomicFactsExecutionCandidate | None,
    reconciliation_states: tuple[ReconciliationStateExecutionCandidate, ...],
    checkpoints: tuple[CheckpointExecutionCandidate, ...],
) -> TargetProductExecutionPlan:
    return plan_target_product_execution(
        TargetProductExecutionPlanningRequest(
            summary_path=summary_path,
            update_mode=update_mode,
            claim_set_fingerprint=claim_set_fingerprint,
            economic_facts=economic_facts,
            reconciliation_states=reconciliation_states,
            checkpoints=checkpoints,
        )
    )
