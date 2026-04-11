"""Shared helpers for balance target planning and source-gap detection."""

from __future__ import annotations

from datetime import datetime

from tallylot.domain.balances import BalanceTarget
from tallylot.domain.issues import IssueRecord
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import TransactionFact
from tallylot.domain.value_objects import format_temporal_value


def select_targets_for_requested_times(
    targets: tuple[BalanceTarget, ...],
    requested_times: tuple[tuple[datetime, TemporalPrecision], ...],
) -> tuple[BalanceTarget, ...]:
    selected: list[BalanceTarget] = []
    for target in targets:
        if any(
            target.target_at == target_at for target_at, _precision in requested_times
        ):
            selected.append(target)
    return tuple(selected)


def missing_fact_coverage_issues(
    facts: tuple[TransactionFact, ...],
    targets: tuple[BalanceTarget, ...],
) -> tuple[IssueRecord, ...]:
    issues: list[IssueRecord] = []
    for target in targets:
        if _has_fact_coverage_for_target(facts, target):
            continue
        issues.append(
            IssueRecord(
                issue_id=":".join(
                    (
                        str(target.source),
                        str(target.location_id),
                        str(target.instrument_id),
                        target.balance_kind,
                        "missing_fact_coverage_for_reference_target",
                    )
                ),
                source=str(target.source),
                adapter_id="balances",
                severity="high",
                kind="missing_fact_coverage_for_reference_target",
                message=(
                    "A statement-backed balance target was selected, but no exact fact "
                    "coverage exists for that source, location, instrument, and target_at. "
                    "This source gap must be resolved explicitly rather than inferred."
                ),
                context_timestamp=format_temporal_value(
                    target.target_at,
                    precision=target.target_precision,
                    label="missing fact coverage balance target_at",
                ),
                raw_file="",
            )
        )
    return tuple(issues)


def _has_fact_coverage_for_target(
    facts: tuple[TransactionFact, ...],
    target: BalanceTarget,
) -> bool:
    for fact in facts:
        if fact.source != target.source or fact.timestamp > target.target_at:
            continue
        for leg in fact.legs:
            location_id = leg.location_id or fact.location_id
            if str(location_id) == str(target.location_id) and str(
                leg.instrument_id
            ) == str(target.instrument_id):
                return True
    return False
