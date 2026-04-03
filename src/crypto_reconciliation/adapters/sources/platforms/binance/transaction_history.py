"""Binance transaction-history normalization."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.sources.mapped_event_support import (
    MappedEventSpec,
    NormalizationIssueSpec,
    mapped_event,
    normalization_issue,
)
from crypto_reconciliation.domain.models import CanonicalEvent, IssueRecord, SourceProfile
from crypto_reconciliation.domain.value_objects import parse_decimal, parse_timestamp

from .csv_rows import is_no_data_row, read_rows
from .field_parsing import row_change
from .timestamps import parse_transaction_history_timestamp

HISTORICAL_ONLY_IGNORED_OPERATIONS = frozenset(
    {
        "Isolated Margin Loan",
        "Isolated Margin Repayment",
        "Launchpool Subscription/Redemption",
        "Staking Purchase",
        "Staking Redemption",
        "Simple Earn Flexible Subscription",
        "Simple Earn Flexible Redemption",
        "Transfer Between Main Account/Futures and Margin Account",
        "Transfer Between Main and Funding Wallet",
        "Transfer Between UM Futures and Funding Account",
        "Transfer Between Spot Account and UM Futures Account",
        "Transfer Between Futures Contract Accounts",
        "Send/Recieve",
        "P2P Trading",
        "BNB Fee Deduction",
    }
)


def normalize_transaction_rows(
    profile: SourceProfile,
    path: Path,
    *,
    convert_match_times: frozenset[datetime] | None = None,
    p2p_match_times: frozenset[datetime] | None = None,
) -> tuple[list[CanonicalEvent], list[IssueRecord]]:
    events: list[CanonicalEvent] = []
    issues: list[IssueRecord] = []
    resolved_convert_match_times = convert_match_times or frozenset()
    resolved_p2p_match_times = p2p_match_times or frozenset()
    grouped_rows: dict[tuple[str, str, str], list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for index, row in enumerate(read_rows(path), start=2):
        if is_no_data_row(row):
            continue
        key = (
            (row.get("Time") or "").strip(),
            (row.get("Account") or "").strip(),
            (row.get("Operation") or "").strip(),
        )
        grouped_rows[key].append((index, row))
    for (time_value, account, operation), group in sorted(grouped_rows.items()):
        parsed_time = parse_transaction_history_timestamp(time_value)
        if _should_ignore_historical_operation(profile, parsed_time, operation):
            continue
        if operation == "ETH 2.0 Staking Rewards":
            index, row = group[0]
            change = parse_decimal((row.get("Change") or "").strip())
            coin = (row.get("Coin") or "").strip().upper()
            if change is None or change <= Decimal("0"):
                continue
            events.append(
                mapped_event(
                    MappedEventSpec(
                        event_id=f"binance:{path.name}:row:{index}",
                        source=str(profile.source),
                        adapter_id="binance",
                        account=account,
                        wallet=account,
                        timestamp=parsed_time,
                        event_kind="Staking",
                        description=operation,
                        raw_file=path.name,
                        raw_row_ref=f"row:{index}",
                        render_exchange=str(profile.source),
                        asset_in=coin,
                        amount_in=change,
                        render_group=account,
                        render_notes=operation,
                    )
                )
            )
            continue
        if operation == "Small Assets Exchange BNB" and len(group) >= 2:
            negative_row = next((item for item in group if row_change(item[1]) < Decimal("0")), None)
            positive_row = next((item for item in group if row_change(item[1]) > Decimal("0")), None)
            if negative_row is None or positive_row is None:
                continue
            neg_index, neg = negative_row
            _, pos = positive_row
            neg_change = row_change(neg)
            pos_change = row_change(pos)
            events.append(
                mapped_event(
                    MappedEventSpec(
                        event_id=f"binance:{path.name}:small_assets:{(neg.get('Coin') or '').strip().upper()}",
                        source=str(profile.source),
                        adapter_id="binance",
                        account=account,
                        wallet=account,
                        timestamp=parsed_time,
                        event_kind="Trade",
                        description=f"Binance dust conversion {(neg.get('Remark') or '').strip()}",
                        raw_file=path.name,
                        raw_row_ref=f"row:{neg_index}",
                        render_exchange=str(profile.source),
                        asset_in=(pos.get("Coin") or "").strip().upper(),
                        amount_in=pos_change,
                        asset_out=(neg.get("Coin") or "").strip().upper(),
                        amount_out=abs(neg_change),
                        render_group=account,
                        render_notes=operation,
                    )
                )
            )
            continue
        if operation == "Binance Convert" and parsed_time in resolved_convert_match_times:
            continue
        if operation == "P2P Trading" and parsed_time in resolved_p2p_match_times:
            continue
        issue_kind = "ambiguous_group" if operation == "Binance Convert" else "unsupported_group"
        message_prefix = (
            "Unable to safely collapse Binance grouped rows with operations"
            if issue_kind == "ambiguous_group"
            else "Unsupported Binance transaction-history operations"
        )
        issues.append(
            normalization_issue(
                NormalizationIssueSpec(
                    source=str(profile.source),
                    adapter_id="binance",
                    issue_id=f"binance:{path.name}:group:{time_value}:{account}",
                    kind=issue_kind,
                    message=f"{message_prefix}: {operation}",
                    raw_file=path.name,
                    raw_row_ref=f"group:{time_value}:{account}",
                )
            )
        )
    return events, issues


def _should_ignore_historical_operation(
    profile: SourceProfile,
    parsed_time: datetime,
    operation: str,
) -> bool:
    cutoff_value = profile.normalization_hints.get("project_baseline_cutoff_timestamp")
    if not isinstance(cutoff_value, str) or operation not in HISTORICAL_ONLY_IGNORED_OPERATIONS:
        return False
    return parsed_time <= parse_timestamp(cutoff_value).replace(tzinfo=None)
