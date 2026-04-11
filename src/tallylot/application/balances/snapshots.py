"""Cutoff-aware balance snapshot derivation."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from tallylot.domain.balances import BalanceSnapshot, BalanceTarget
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import TransactionFact
from tallylot.domain.value_objects import format_temporal_value


def derive_balance_snapshots(
    facts: tuple[TransactionFact, ...],
    targets: tuple[BalanceTarget, ...],
) -> tuple[tuple[BalanceSnapshot, ...], tuple[IssueRecord, ...]]:
    grouped_facts: dict[str, list[TransactionFact]] = defaultdict(list)
    for fact in facts:
        grouped_facts[str(fact.source)].append(fact)
    snapshots: list[BalanceSnapshot] = []
    issues: list[IssueRecord] = []
    for target in targets:
        source_facts = grouped_facts.get(str(target.source), [])
        quantity = Decimal("0")
        for fact in source_facts:
            if fact.timestamp > target.target_at:
                continue
            for leg in fact.legs:
                location_id = leg.location_id or fact.location_id
                if str(location_id) == str(target.location_id) and str(
                    leg.instrument_id
                ) == str(target.instrument_id):
                    quantity += leg.quantity
        snapshots.append(
            BalanceSnapshot(
                target=target,
                quantity=quantity,
                snapshot_basis="fact_cutoff",
            )
        )
        if not source_facts:
            issues.append(
                IssueRecord(
                    issue_id=":".join(
                        (
                            str(target.source),
                            str(target.location_id),
                            str(target.instrument_id),
                            target.balance_kind,
                            "missing_facts_for_balance_target",
                        )
                    ),
                    source=str(target.source),
                    adapter_id="balances",
                    severity="high",
                    kind="missing_facts_for_balance_target",
                    message="No facts were available to derive the requested balance target.",
                    context_timestamp=format_temporal_value(
                        target.target_at,
                        precision=target.target_precision,
                        label="missing facts balance target_at",
                    ),
                    raw_file="",
                )
            )
    return tuple(snapshots), tuple(issues)
