"""Kernel reuse and readability helpers for target-product execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from tallylot.application.normalization.contracts import NormalizeUpdateMode
from tallylot.domain.checkpoint import Checkpoint
from tallylot.domain.evidence import EvidenceSet
from tallylot.domain.reconciliation import ReconciliationState

from .detail_outputs import DETAIL_READ_EXCEPTIONS
from .models import (
    CheckpointExecutionDecision,
    ReconciliationStateExecutionDecision,
    TargetProductExecutionPlan,
)


class _ReconciliationStateRepositoryProtocol(Protocol):
    def read_reconciliation_state(self, path: Path) -> ReconciliationState: ...


class _CheckpointRepositoryProtocol(Protocol):
    def read_checkpoint(self, path: Path) -> Checkpoint: ...


class _ReconciliationDependenciesProtocol(Protocol):
    @property
    def reconciliation_states(self) -> _ReconciliationStateRepositoryProtocol: ...


class _CheckpointDependenciesProtocol(Protocol):
    @property
    def checkpoints(self) -> _CheckpointRepositoryProtocol: ...


class ReconciliationKernelReuseRequestProtocol(Protocol):
    @property
    def workspace_root(self) -> Path: ...

    @property
    def update_mode(self) -> NormalizeUpdateMode: ...

    @property
    def prior_plan(self) -> TargetProductExecutionPlan | None: ...

    @property
    def claim_set_fingerprint(self) -> str: ...

    @property
    def prior_evidence_set_id(self) -> str | None: ...

    @property
    def evidence_set(self) -> EvidenceSet: ...

    @property
    def economic_facts_reused(self) -> bool: ...

    @property
    def dependencies(self) -> _ReconciliationDependenciesProtocol: ...


class CheckpointKernelReuseRequestProtocol(Protocol):
    @property
    def workspace_root(self) -> Path: ...

    @property
    def update_mode(self) -> NormalizeUpdateMode: ...

    @property
    def prior_plan(self) -> TargetProductExecutionPlan | None: ...

    @property
    def claim_set_fingerprint(self) -> str: ...

    @property
    def reconciliation_states_reused(self) -> bool: ...

    @property
    def dependencies(self) -> _CheckpointDependenciesProtocol: ...


def _empty_str_set() -> set[str]:
    return set()


@dataclass
class KernelValidationState:
    unreadable_refs: set[str] = field(default_factory=_empty_str_set)
    validated_refs: set[str] = field(default_factory=_empty_str_set)


def resolve_reconciliation_state_kernels(
    *,
    request: ReconciliationKernelReuseRequestProtocol,
    prior_states: tuple[ReconciliationStateExecutionDecision, ...],
    build_current: Callable[[], tuple[ReconciliationState, ...]],
) -> tuple[tuple[ReconciliationState, ...], KernelValidationState]:
    validation_state = KernelValidationState()
    can_use_prior_kernels_as_current = (
        request.update_mode is not NormalizeUpdateMode.REBUILD
        and request.prior_plan is not None
        and request.prior_plan.claim_set_fingerprint == request.claim_set_fingerprint
        and request.prior_evidence_set_id == request.evidence_set.evidence_set_id
        and request.economic_facts_reused
        and bool(prior_states)
        and all(
            (request.workspace_root / decision.reconciliation_state_ref).is_file()
            for decision in prior_states
        )
    )
    if not can_use_prior_kernels_as_current:
        return build_current(), validation_state
    prior_kernel_states: list[ReconciliationState] = []
    for decision in prior_states:
        try:
            prior_kernel_states.append(
                request.dependencies.reconciliation_states.read_reconciliation_state(
                    request.workspace_root / decision.reconciliation_state_ref
                )
            )
        except DETAIL_READ_EXCEPTIONS:
            validation_state.unreadable_refs.add(decision.reconciliation_state_ref)
    if validation_state.unreadable_refs:
        return build_current(), validation_state
    validation_state.validated_refs = {
        decision.reconciliation_state_ref for decision in prior_states
    }
    return tuple(prior_kernel_states), validation_state


def validate_reconciliation_state_kernel_ref(
    *,
    request: ReconciliationKernelReuseRequestProtocol,
    state_ref_value: str,
    state_path: Path,
    prior_state: ReconciliationStateExecutionDecision | None,
    validation_state: KernelValidationState,
) -> None:
    if (
        prior_state is None
        or state_ref_value in validation_state.unreadable_refs
        or state_ref_value in validation_state.validated_refs
        or not state_path.is_file()
    ):
        return
    try:
        request.dependencies.reconciliation_states.read_reconciliation_state(state_path)
    except DETAIL_READ_EXCEPTIONS:
        validation_state.unreadable_refs.add(state_ref_value)
    else:
        validation_state.validated_refs.add(state_ref_value)


def resolve_checkpoint_kernels(
    *,
    request: CheckpointKernelReuseRequestProtocol,
    prior_checkpoints: tuple[CheckpointExecutionDecision, ...],
    build_current: Callable[[], tuple[Checkpoint, ...]],
) -> tuple[tuple[Checkpoint, ...], KernelValidationState]:
    validation_state = KernelValidationState()
    can_use_prior_kernels_as_current = (
        request.update_mode is not NormalizeUpdateMode.REBUILD
        and request.prior_plan is not None
        and request.prior_plan.claim_set_fingerprint == request.claim_set_fingerprint
        and request.reconciliation_states_reused
        and all(
            (request.workspace_root / decision.checkpoint_ref).is_file()
            for decision in prior_checkpoints
        )
    )
    if not can_use_prior_kernels_as_current:
        return build_current(), validation_state
    prior_kernel_checkpoints: list[Checkpoint] = []
    for decision in prior_checkpoints:
        try:
            prior_kernel_checkpoints.append(
                request.dependencies.checkpoints.read_checkpoint(
                    request.workspace_root / decision.checkpoint_ref
                )
            )
        except DETAIL_READ_EXCEPTIONS:
            validation_state.unreadable_refs.add(decision.checkpoint_ref)
    if validation_state.unreadable_refs:
        return build_current(), validation_state
    validation_state.validated_refs = {
        decision.checkpoint_ref for decision in prior_checkpoints
    }
    return tuple(prior_kernel_checkpoints), validation_state


def validate_checkpoint_kernel_ref(
    *,
    request: CheckpointKernelReuseRequestProtocol,
    checkpoint_ref_value: str,
    checkpoint_path: Path,
    prior_checkpoint: CheckpointExecutionDecision | None,
    validation_state: KernelValidationState,
) -> None:
    if (
        prior_checkpoint is None
        or checkpoint_ref_value in validation_state.unreadable_refs
        or checkpoint_ref_value in validation_state.validated_refs
        or not checkpoint_path.is_file()
    ):
        return
    try:
        request.dependencies.checkpoints.read_checkpoint(checkpoint_path)
    except DETAIL_READ_EXCEPTIONS:
        validation_state.unreadable_refs.add(checkpoint_ref_value)
    else:
        validation_state.validated_refs.add(checkpoint_ref_value)
