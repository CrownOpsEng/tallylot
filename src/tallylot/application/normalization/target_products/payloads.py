"""Target-product execution payload and artifact helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from tallylot.domain.balances import BalanceReference, BalanceSnapshot
from tallylot.domain.types import JsonValue

from ..annotations import FactAnnotationRecord
from .models import TargetProductExecutionPlan


def execution_plan_payload(plan: TargetProductExecutionPlan) -> JsonValue:
    payload: dict[str, JsonValue] = {
        "signature_version": plan.signature_version,
        "update_mode_requested": plan.update_mode_requested,
        "update_mode_effective": plan.update_mode_effective,
        "claim_set_fingerprint": plan.claim_set_fingerprint,
        "economic_facts": None,
        "reconciliation_states": [
            {
                "reconciliation_state_id": decision.reconciliation_state_id,
                "reconciliation_state_ref": decision.reconciliation_state_ref,
                "fingerprint": decision.fingerprint,
                "kernel_action": decision.kernel_action.value,
                "snapshot_action": decision.snapshot_action.value,
                "snapshot_signature": decision.snapshot_signature,
            }
            for decision in plan.reconciliation_states
        ],
        "checkpoints": [
            {
                "checkpoint_id": decision.checkpoint_id,
                "checkpoint_ref": decision.checkpoint_ref,
                "fingerprint": decision.fingerprint,
                "kernel_action": decision.kernel_action.value,
                "reference_action": decision.reference_action.value,
                "reference_signature": decision.reference_signature,
            }
            for decision in plan.checkpoints
        ],
        "pruned_reconciliation_state_refs": list(plan.pruned_reconciliation_state_refs),
        "pruned_checkpoint_refs": list(plan.pruned_checkpoint_refs),
    }
    if plan.economic_facts is not None:
        payload["economic_facts"] = {
            "economic_facts_id": plan.economic_facts.economic_facts_id,
            "economic_facts_ref": plan.economic_facts.economic_facts_ref,
            "fingerprint": plan.economic_facts.fingerprint,
            "kernel_action": plan.economic_facts.kernel_action.value,
            "compatibility_action": plan.economic_facts.compatibility_action.value,
            "compatibility_signature": plan.economic_facts.compatibility_signature,
        }
    return cast(JsonValue, payload)


def read_fact_annotations(path: Path) -> tuple[FactAnnotationRecord, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return ()
    raw_payload = cast(list[object], payload)
    records: list[FactAnnotationRecord] = []
    for item in raw_payload:
        if not isinstance(item, dict):
            continue
        raw_item = cast(dict[str, object], item)
        provenance_refs = tuple(
            value
            for value in cast(list[object], raw_item.get("provenance_refs", []))
            if isinstance(value, str)
        )
        review_markers = tuple(
            value
            for value in cast(list[object], raw_item.get("review_markers", []))
            if isinstance(value, str)
        )
        records.append(
            FactAnnotationRecord(
                fact_id=str(raw_item.get("fact_id", "")),
                provenance_refs=provenance_refs,
                review_markers=review_markers,
                adapter_metadata=(),
            )
        )
    return tuple(records)


def snapshot_rows_signature(snapshots: tuple[BalanceSnapshot, ...]) -> str:
    return json.dumps(
        [snapshot.to_row() for snapshot in snapshots],
        sort_keys=True,
        separators=(",", ":"),
    )


def reference_rows_signature(references: tuple[BalanceReference, ...]) -> str:
    return json.dumps(
        [reference.to_row() for reference in references],
        sort_keys=True,
        separators=(",", ":"),
    )
