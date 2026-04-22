"""Typed target-product execution planning models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION = "normalization-target-products-v1"


class TargetProductStageAction(StrEnum):
    REUSED = "reused"
    REBUILT = "rebuilt"
    REFRESHED = "refreshed"
    PRUNED = "pruned"


@dataclass(frozen=True)
class EconomicFactsExecutionCandidate:
    economic_facts_id: str
    economic_facts_ref: str
    fingerprint: str
    compatibility_signature: str
    kernel_path: Path
    detail_paths: tuple[Path, ...]
    kernel_valid: bool = True


@dataclass(frozen=True)
class ReconciliationStateExecutionCandidate:
    reconciliation_state_id: str
    reconciliation_state_ref: str
    fingerprint: str
    snapshot_signature: str
    kernel_path: Path
    detail_paths: tuple[Path, ...]
    kernel_valid: bool = True


@dataclass(frozen=True)
class CheckpointExecutionCandidate:
    checkpoint_id: str
    checkpoint_ref: str
    fingerprint: str
    reference_signature: str
    kernel_path: Path
    detail_paths: tuple[Path, ...]
    kernel_valid: bool = True


@dataclass(frozen=True)
class EconomicFactsExecutionDecision:
    economic_facts_id: str
    economic_facts_ref: str
    fingerprint: str
    kernel_action: TargetProductStageAction
    compatibility_action: TargetProductStageAction
    compatibility_signature: str


@dataclass(frozen=True)
class ReconciliationStateExecutionDecision:
    reconciliation_state_id: str
    reconciliation_state_ref: str
    fingerprint: str
    kernel_action: TargetProductStageAction
    snapshot_action: TargetProductStageAction
    snapshot_signature: str


@dataclass(frozen=True)
class CheckpointExecutionDecision:
    checkpoint_id: str
    checkpoint_ref: str
    fingerprint: str
    kernel_action: TargetProductStageAction
    reference_action: TargetProductStageAction
    reference_signature: str


@dataclass(frozen=True)
class TargetProductExecutionPlan:
    signature_version: str
    update_mode_requested: str
    update_mode_effective: str
    claim_set_fingerprint: str
    economic_facts: EconomicFactsExecutionDecision | None
    reconciliation_states: tuple[ReconciliationStateExecutionDecision, ...]
    checkpoints: tuple[CheckpointExecutionDecision, ...]
    pruned_reconciliation_state_refs: tuple[str, ...] = ()
    pruned_checkpoint_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class TargetProductExecutionSummary:
    reused_target_product_count: int
    rebuilt_target_product_count: int
    pruned_target_product_count: int
    refreshed_detail_output_count: int
