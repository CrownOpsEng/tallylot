"""Balance assertion selection and comparison logic."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from tallylot.domain.issues import IssueRecord
from tallylot.domain.value_objects import format_temporal_value

from .models import (
    BalanceAssertion,
    BalanceAssertionStatus,
    BalanceReference,
    BalanceReferenceKind,
    BalanceSnapshot,
    BalanceTarget,
)

_REFERENCE_PRECEDENCE = (
    BalanceReferenceKind.SOURCE_DOCUMENT,
    BalanceReferenceKind.NETWORK_API,
    BalanceReferenceKind.OPERATOR_ASSERTION,
)


@dataclass(frozen=True)
class BalanceAssertionResult:
    assertions: tuple[BalanceAssertion, ...]
    issues: tuple[IssueRecord, ...]


def assert_balance_targets(
    snapshots: tuple[BalanceSnapshot, ...],
    references: tuple[BalanceReference, ...],
) -> BalanceAssertionResult:
    snapshot_index, snapshot_issues = _index_snapshots(snapshots)
    reference_index, reference_issues = _index_references(references)
    issues: list[IssueRecord] = [*snapshot_issues, *reference_issues]
    assertions: list[BalanceAssertion] = []
    for target in sorted(set(snapshot_index) | set(reference_index)):
        snapshot = snapshot_index.get(target)
        selected_reference, selection_status, selection_issues = _selected_reference(
            target,
            reference_index.get(target, ()),
        )
        issues.extend(selection_issues)
        assertion = _build_assertion(
            target,
            snapshot,
            selected_reference,
            selection_status,
        )
        assertions.append(assertion)
        if assertion.status is not BalanceAssertionStatus.MATCHED:
            issues.append(_assertion_issue(assertion))
    return BalanceAssertionResult(assertions=tuple(assertions), issues=tuple(issues))


def _index_snapshots(
    snapshots: tuple[BalanceSnapshot, ...],
) -> tuple[dict[BalanceTarget, BalanceSnapshot], tuple[IssueRecord, ...]]:
    indexed: dict[BalanceTarget, BalanceSnapshot] = {}
    issues: list[IssueRecord] = []
    duplicate_counts: dict[BalanceTarget, int] = defaultdict(int)
    for snapshot in snapshots:
        target = snapshot.target
        if target in indexed:
            duplicate_counts[target] += 1
            issues.append(
                _duplicate_issue(
                    target,
                    kind="duplicate_balance_snapshot",
                    duplicate_index=duplicate_counts[target],
                )
            )
            continue
        indexed[target] = snapshot
    return indexed, tuple(issues)


def _index_references(
    references: tuple[BalanceReference, ...],
) -> tuple[dict[BalanceTarget, tuple[BalanceReference, ...]], tuple[IssueRecord, ...]]:
    grouped: dict[BalanceTarget, list[BalanceReference]] = defaultdict(list)
    for reference in references:
        grouped[reference.target].append(reference)
    return {target: tuple(items) for target, items in grouped.items()}, ()


def _selected_reference(
    target: BalanceTarget,
    references: tuple[BalanceReference, ...],
) -> tuple[
    BalanceReference | None,
    BalanceAssertionStatus | None,
    tuple[IssueRecord, ...],
]:
    if not references:
        return None, None, ()
    for reference_kind in _REFERENCE_PRECEDENCE:
        matching = tuple(
            reference
            for reference in references
            if reference.reference_kind is reference_kind
        )
        if not matching:
            continue
        if len(matching) > 1:
            return (
                None,
                BalanceAssertionStatus.REFERENCE_CONFLICT,
                (
                    IssueRecord(
                        issue_id=":".join(
                            (
                                str(target.source),
                                str(target.location_id),
                                str(target.instrument_id),
                                target.balance_kind,
                                "conflicting_balance_references",
                                reference_kind.value,
                            )
                        ),
                        source=str(target.source),
                        adapter_id="balances",
                        severity="high",
                        kind="conflicting_balance_references",
                        message=(
                            "More than one balance reference with the same precedence "
                            "matched one balance target."
                        ),
                        context_timestamp=format_temporal_value(
                            target.target_at,
                            precision=target.target_precision,
                            label="conflicting balance references target_at",
                        ),
                        raw_file="",
                    ),
                ),
            )
        return next(iter(matching)), None, ()
    return None, None, ()


def _build_assertion(
    target: BalanceTarget,
    snapshot: BalanceSnapshot | None,
    reference: BalanceReference | None,
    selection_status: BalanceAssertionStatus | None,
) -> BalanceAssertion:
    snapshot_quantity = None if snapshot is None else snapshot.quantity
    reference_quantity = None if reference is None else reference.quantity
    return BalanceAssertion(
        target=target,
        snapshot_quantity=snapshot_quantity,
        reference_quantity=reference_quantity,
        difference=(snapshot_quantity or Decimal("0"))
        - (reference_quantity or Decimal("0")),
        status=_assertion_status(snapshot, reference, selection_status),
        selected_reference_kind=(
            None if reference is None else reference.reference_kind
        ),
        snapshot_basis="" if snapshot is None else snapshot.snapshot_basis,
        observed_at=None if reference is None else reference.observed_at,
        observed_precision=(
            None if reference is None else reference.observed_precision
        ),
        observation_gap=""
        if reference is None
        else _observation_gap(target, reference),
        support_ref="" if reference is None else reference.support_ref,
        provider_family="" if reference is None else reference.provider_family,
        provider_block_ref="" if reference is None else reference.provider_block_ref,
        notes="" if reference is None else reference.notes,
    )


def _assertion_status(
    snapshot: BalanceSnapshot | None,
    reference: BalanceReference | None,
    selection_status: BalanceAssertionStatus | None,
) -> BalanceAssertionStatus:
    if selection_status is BalanceAssertionStatus.REFERENCE_CONFLICT:
        return selection_status
    if snapshot is None:
        return BalanceAssertionStatus.MISSING_SNAPSHOT
    if reference is None:
        return BalanceAssertionStatus.MISSING_REFERENCE
    if snapshot.quantity != reference.quantity:
        return BalanceAssertionStatus.DRIFT
    return BalanceAssertionStatus.MATCHED


def _observation_gap(target: BalanceTarget, reference: BalanceReference) -> str:
    delta = target.target_at - reference.observed_at
    return str(int(delta.total_seconds()))


def _assertion_issue(assertion: BalanceAssertion) -> IssueRecord:
    issue_kind = f"balance_{assertion.status.value}"
    status_label = assertion.status.value.replace("_", " ")
    return IssueRecord(
        issue_id=":".join(
            (
                str(assertion.source),
                str(assertion.location_id),
                str(assertion.instrument_id),
                assertion.balance_kind,
                issue_kind,
            )
        ),
        source=str(assertion.source),
        adapter_id="balances",
        severity="high",
        kind=issue_kind,
        message=(
            f"Balance assertion {status_label} for "
            f"{assertion.location_id} {assertion.instrument_id}."
        ),
        context_timestamp=format_temporal_value(
            assertion.target_at,
            precision=assertion.target_precision,
            label="balance assertion target_at",
        ),
        raw_file=assertion.support_ref,
    )


def _duplicate_issue(
    target: BalanceTarget,
    *,
    kind: str,
    duplicate_index: int,
) -> IssueRecord:
    return IssueRecord(
        issue_id=":".join(
            (
                str(target.source),
                str(target.location_id),
                str(target.instrument_id),
                target.balance_kind,
                kind,
                str(duplicate_index),
            )
        ),
        source=str(target.source),
        adapter_id="balances",
        severity="high",
        kind=kind,
        message=(
            f"Duplicate {target.balance_kind} balance input for "
            f"{target.location_id} {target.instrument_id}."
        ),
        context_timestamp=format_temporal_value(
            target.target_at,
            precision=target.target_precision,
            label="duplicate balance target_at",
        ),
        raw_file="",
    )
