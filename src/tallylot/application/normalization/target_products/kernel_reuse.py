"""Kernel reuse and readability helpers for target-product execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from tallylot.application.capture_paths import economic_facts_ref
from tallylot.application.economics import build_economic_facts
from tallylot.application.normalization.contracts import NormalizeUpdateMode
from tallylot.domain.checkpoint import Checkpoint, checkpoint_fingerprint
from tallylot.domain.claim import ClaimSet
from tallylot.domain.economics import EconomicFacts, economic_facts_fingerprint
from tallylot.domain.evidence import EvidenceSet
from tallylot.domain.reconciliation import (
    ReconciliationState,
    reconciliation_state_fingerprint,
)

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


class _EconomicFactsRepositoryProtocol(Protocol):
    def read_economic_facts(self, path: Path) -> EconomicFacts: ...


class _ReconciliationDependenciesProtocol(Protocol):
    @property
    def reconciliation_states(self) -> _ReconciliationStateRepositoryProtocol: ...


class _CheckpointDependenciesProtocol(Protocol):
    @property
    def checkpoints(self) -> _CheckpointRepositoryProtocol: ...


class _EconomicFactsDependenciesProtocol(Protocol):
    @property
    def economic_facts(self) -> _EconomicFactsRepositoryProtocol: ...


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


class EconomicFactsKernelReuseRequestProtocol(Protocol):
    @property
    def workspace_root(self) -> Path: ...

    @property
    def update_mode(self) -> NormalizeUpdateMode: ...

    @property
    def claim_set(self) -> ClaimSet: ...

    @property
    def claim_set_fingerprint(self) -> str: ...

    @property
    def prior_plan(self) -> TargetProductExecutionPlan | None: ...

    @property
    def dependencies(self) -> _EconomicFactsDependenciesProtocol: ...


def _empty_str_set() -> set[str]:
    return set()


@dataclass
class KernelValidationState:
    unreadable_refs: set[str] = field(default_factory=_empty_str_set)
    fingerprint_mismatch_refs: set[str] = field(default_factory=_empty_str_set)
    validated_refs: set[str] = field(default_factory=_empty_str_set)

    @property
    def invalid_refs(self) -> set[str]:
        return self.unreadable_refs | self.fingerprint_mismatch_refs


@dataclass(frozen=True)
class EconomicFactsKernelResolution:
    economic_facts: EconomicFacts
    fingerprint: str
    economic_facts_ref_value: str
    existing_kernel_invalid: bool
    built_current_kernel: bool


def resolve_economic_facts_kernel(
    request: EconomicFactsKernelReuseRequestProtocol,
) -> EconomicFactsKernelResolution:
    prior_plan = request.prior_plan
    prior_economic_facts = None if prior_plan is None else prior_plan.economic_facts
    existing_kernel_invalid = False
    can_use_prior_kernel_as_current = (
        request.update_mode is not NormalizeUpdateMode.REBUILD
        and prior_plan is not None
        and prior_economic_facts is not None
        and prior_plan.claim_set_fingerprint == request.claim_set_fingerprint
        and (request.workspace_root / prior_economic_facts.economic_facts_ref).is_file()
    )
    if can_use_prior_kernel_as_current:
        assert prior_economic_facts is not None
        try:
            economic_facts = request.dependencies.economic_facts.read_economic_facts(
                request.workspace_root / prior_economic_facts.economic_facts_ref
            )
        except DETAIL_READ_EXCEPTIONS:
            existing_kernel_invalid = True
        else:
            current_fingerprint = economic_facts_fingerprint(economic_facts)
            if current_fingerprint == prior_economic_facts.fingerprint:
                return EconomicFactsKernelResolution(
                    economic_facts=economic_facts,
                    fingerprint=current_fingerprint,
                    economic_facts_ref_value=prior_economic_facts.economic_facts_ref,
                    existing_kernel_invalid=False,
                    built_current_kernel=False,
                )
            existing_kernel_invalid = True
    economic_facts = build_economic_facts(claim_set=request.claim_set)
    current_fingerprint = economic_facts_fingerprint(economic_facts)
    economic_facts_ref_value = economic_facts_ref(
        request.workspace_root,
        economic_facts.economic_facts_id,
    )
    if (
        not can_use_prior_kernel_as_current
        and (request.workspace_root / economic_facts_ref_value).is_file()
    ):
        try:
            persisted_economic_facts = (
                request.dependencies.economic_facts.read_economic_facts(
                    request.workspace_root / economic_facts_ref_value
                )
            )
        except DETAIL_READ_EXCEPTIONS:
            existing_kernel_invalid = True
        else:
            if (
                economic_facts_fingerprint(persisted_economic_facts)
                != current_fingerprint
            ):
                existing_kernel_invalid = True
    return EconomicFactsKernelResolution(
        economic_facts=economic_facts,
        fingerprint=current_fingerprint,
        economic_facts_ref_value=economic_facts_ref_value,
        existing_kernel_invalid=existing_kernel_invalid,
        built_current_kernel=True,
    )


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
            state = (
                request.dependencies.reconciliation_states.read_reconciliation_state(
                    request.workspace_root / decision.reconciliation_state_ref
                )
            )
        except DETAIL_READ_EXCEPTIONS:
            validation_state.unreadable_refs.add(decision.reconciliation_state_ref)
            continue
        if reconciliation_state_fingerprint(state) != decision.fingerprint:
            validation_state.fingerprint_mismatch_refs.add(
                decision.reconciliation_state_ref
            )
            continue
        prior_kernel_states.append(state)
    if validation_state.invalid_refs:
        return build_current(), validation_state
    validation_state.validated_refs = {
        decision.reconciliation_state_ref for decision in prior_states
    } - validation_state.invalid_refs
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
        or state_ref_value in validation_state.invalid_refs
        or state_ref_value in validation_state.validated_refs
        or not state_path.is_file()
    ):
        return
    try:
        state = request.dependencies.reconciliation_states.read_reconciliation_state(
            state_path
        )
    except DETAIL_READ_EXCEPTIONS:
        validation_state.unreadable_refs.add(state_ref_value)
        return
    if reconciliation_state_fingerprint(state) != prior_state.fingerprint:
        validation_state.fingerprint_mismatch_refs.add(state_ref_value)
        return
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
            checkpoint = request.dependencies.checkpoints.read_checkpoint(
                request.workspace_root / decision.checkpoint_ref
            )
        except DETAIL_READ_EXCEPTIONS:
            validation_state.unreadable_refs.add(decision.checkpoint_ref)
            continue
        if checkpoint_fingerprint(checkpoint) != decision.fingerprint:
            validation_state.fingerprint_mismatch_refs.add(decision.checkpoint_ref)
            continue
        prior_kernel_checkpoints.append(checkpoint)
    if validation_state.invalid_refs:
        return build_current(), validation_state
    validation_state.validated_refs = {
        decision.checkpoint_ref for decision in prior_checkpoints
    } - validation_state.invalid_refs
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
        or checkpoint_ref_value in validation_state.invalid_refs
        or checkpoint_ref_value in validation_state.validated_refs
        or not checkpoint_path.is_file()
    ):
        return
    try:
        checkpoint = request.dependencies.checkpoints.read_checkpoint(checkpoint_path)
    except DETAIL_READ_EXCEPTIONS:
        validation_state.unreadable_refs.add(checkpoint_ref_value)
        return
    if checkpoint_fingerprint(checkpoint) != prior_checkpoint.fingerprint:
        validation_state.fingerprint_mismatch_refs.add(checkpoint_ref_value)
        return
    validation_state.validated_refs.add(checkpoint_ref_value)
