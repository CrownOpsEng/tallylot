"""Binance export adapter."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.sources.mapped_event_support import (
    MappedEventSpec,
    NormalizationIssueSpec,
    mapped_event,
    normalization_issue,
)
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    CanonicalEvent,
    FileInventoryEntry,
    IssueRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, JsonValue
from crypto_reconciliation.domain.value_objects import parse_decimal
from crypto_reconciliation.ports.adapters import NormalizationResult

FILENAME_OFFSET_PATTERN = re.compile(r"UTC-(?P<sign>[+-])(?P<hours>\d+)")
SPOT_HEADER = ("Time", "Pair", "Side", "Price", "Executed", "Amount", "Fee")
DEPOSIT_HEADER = ("Time", "Coin", "Network", "Amount", "Address", "TXID", "Status")
WITHDRAW_HEADER = ("Time", "Coin", "Network", "Amount", "Fee", "Address", "TXID", "Status")
TRANSACTION_HEADER = ("User ID", "Time", "Account", "Operation", "Coin", "Change", "Remark")


class BinanceAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("binance"),
        display_name="Binance",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE}),
        description="Normalizes Binance deposit, withdrawal, spot, and transaction-history exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "binance" in source.lower():
            return 100
        headers = {item.header for item in inventory}
        if any(header in headers for header in (SPOT_HEADER, DEPOSIT_HEADER, WITHDRAW_HEADER, TRANSACTION_HEADER)):
            return 100
        return 0

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        rows_with_dates = sum(1 for item in profile.file_inventory if item.date_field)
        return {
            "status": "passed",
            "issue_count": 0,
            "rows_with_dates": rows_with_dates,
            "mode_counts": {"binance_export": rows_with_dates} if rows_with_dates else {},
        }, ()

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        events: list[CanonicalEvent] = []
        issues: list[IssueRecord] = []
        for path in sorted(raw_dir.glob("*.csv")):
            if path.name.startswith("Binance-Spot-Trade-History-"):
                events.extend(_normalize_spot_rows(profile, path))
            elif path.name.startswith("Binance-Deposit-History-"):
                events.extend(_normalize_deposit_rows(profile, path))
            elif path.name.startswith("Binance-Withdraw-History-"):
                events.extend(_normalize_withdraw_rows(profile, path))
            elif path.name.startswith("Binance-Transaction-History-"):
                parsed_events, parsed_issues = _normalize_transaction_rows(profile, path)
                events.extend(parsed_events)
                issues.extend(parsed_issues)
        return NormalizationResult(
            canonical_events=tuple(events),
            canonical_balances=(),
            issues=tuple(issues),
            reviews=(),
            wallet_inventory=(),
        )


def _read_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(csv.DictReader(handle))


def _normalize_spot_rows(profile: SourceProfile, path: Path) -> list[CanonicalEvent]:
    events: list[CanonicalEvent] = []
    for index, row in enumerate(_read_rows(path), start=2):
        side = (row.get("Side") or "").strip().upper()
        pair = (row.get("Pair") or "").strip().upper()
        base_asset, quote_asset = _split_pair(pair)
        executed_amount, executed_asset = _amount_with_asset(row.get("Executed", ""))
        quote_amount, _ = _amount_with_asset(row.get("Amount", ""))
        fee_amount, fee_asset = _amount_with_asset(row.get("Fee", ""))
        timestamp = _parse_offset_timestamp((row.get("Time") or "").strip(), path.name)
        if side == "SELL":
            events.append(
                mapped_event(
                    MappedEventSpec(
                        event_id=f"binance:{path.name}:row:{index}",
                        source=str(profile.source),
                        adapter_id="binance",
                        account="Spot",
                        wallet="Spot",
                        timestamp=timestamp,
                        event_kind="Trade",
                        description=f"Binance spot sell {pair}",
                        raw_file=path.name,
                        raw_row_ref=f"row:{index}",
                        render_exchange=str(profile.source),
                        asset_in=quote_asset,
                        amount_in=quote_amount,
                        asset_out=base_asset or executed_asset,
                        amount_out=executed_amount,
                        fee_asset=fee_asset,
                        fee_amount=fee_amount,
                        render_group="Spot",
                        render_notes=pair,
                    )
                )
            )
        elif side == "BUY":
            events.append(
                mapped_event(
                    MappedEventSpec(
                        event_id=f"binance:{path.name}:row:{index}",
                        source=str(profile.source),
                        adapter_id="binance",
                        account="Spot",
                        wallet="Spot",
                        timestamp=timestamp,
                        event_kind="Trade",
                        description=f"Binance spot buy {pair}",
                        raw_file=path.name,
                        raw_row_ref=f"row:{index}",
                        render_exchange=str(profile.source),
                        asset_in=base_asset or executed_asset,
                        amount_in=executed_amount,
                        asset_out=quote_asset,
                        amount_out=quote_amount,
                        fee_asset=fee_asset,
                        fee_amount=fee_amount,
                        render_group="Spot",
                        render_notes=pair,
                    )
                )
            )
    return events


def _normalize_deposit_rows(profile: SourceProfile, path: Path) -> list[CanonicalEvent]:
    events: list[CanonicalEvent] = []
    for index, row in enumerate(_read_rows(path), start=2):
        if (row.get("Status") or "").strip().lower() != "completed":
            continue
        amount = parse_decimal((row.get("Amount") or "").strip())
        if amount is None:
            continue
        events.append(
            mapped_event(
                MappedEventSpec(
                    event_id=f"binance:{path.name}:row:{index}",
                    source=str(profile.source),
                    adapter_id="binance",
                    account="Binance",
                    wallet="Funding",
                    timestamp=_parse_offset_timestamp((row.get("Time") or "").strip(), path.name),
                    event_kind="Deposit",
                    description=f"Binance deposit via {(row.get('Network') or '').strip()}",
                    raw_file=path.name,
                    raw_row_ref=f"row:{index}",
                    render_exchange=str(profile.source),
                    asset_in=(row.get("Coin") or "").strip().upper(),
                    amount_in=amount,
                    tx_hash=(row.get("TXID") or "").strip(),
                    render_group="Funding",
                    render_tx_id=(row.get("TXID") or "").strip(),
                    render_tx_id_mode="exact",
                    render_notes=(row.get("Address") or "").strip(),
                )
            )
        )
    return events


def _normalize_withdraw_rows(profile: SourceProfile, path: Path) -> list[CanonicalEvent]:
    events: list[CanonicalEvent] = []
    for index, row in enumerate(_read_rows(path), start=2):
        if (row.get("Status") or "").strip().lower() != "completed":
            continue
        amount = parse_decimal((row.get("Amount") or "").strip())
        fee = parse_decimal((row.get("Fee") or "").strip())
        if amount is None:
            continue
        coin = (row.get("Coin") or "").strip().upper()
        events.append(
            mapped_event(
                MappedEventSpec(
                    event_id=f"binance:{path.name}:row:{index}",
                    source=str(profile.source),
                    adapter_id="binance",
                    account="Binance",
                    wallet="Funding",
                    timestamp=_parse_offset_timestamp((row.get("Time") or "").strip(), path.name),
                    event_kind="Withdrawal",
                    description=f"Binance withdrawal via {(row.get('Network') or '').strip()}",
                    raw_file=path.name,
                    raw_row_ref=f"row:{index}",
                    render_exchange=str(profile.source),
                    asset_out=coin,
                    amount_out=amount,
                    fee_asset=coin if fee is not None and fee > Decimal("0") else "",
                    fee_amount=fee if fee is not None and fee > Decimal("0") else None,
                    tx_hash=(row.get("TXID") or "").strip(),
                    render_group="Funding",
                    render_tx_id=(row.get("TXID") or "").strip(),
                    render_tx_id_mode="exact",
                    render_notes=(row.get("Address") or "").strip(),
                )
            )
        )
    return events


def _normalize_transaction_rows(
    profile: SourceProfile,
    path: Path,
) -> tuple[list[CanonicalEvent], list[IssueRecord]]:
    events: list[CanonicalEvent] = []
    issues: list[IssueRecord] = []
    grouped_rows: dict[tuple[str, str, str], list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for index, row in enumerate(_read_rows(path), start=2):
        key = (
            (row.get("Time") or "").strip(),
            (row.get("Account") or "").strip(),
            (row.get("Operation") or "").strip(),
        )
        grouped_rows[key].append((index, row))
    for (time_value, account, operation), group in sorted(grouped_rows.items()):
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
                        timestamp=_parse_transaction_history_timestamp(time_value),
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
            negative_row = next((item for item in group if _row_change(item[1]) < Decimal("0")), None)
            positive_row = next((item for item in group if _row_change(item[1]) > Decimal("0")), None)
            if negative_row is None or positive_row is None:
                continue
            neg_index, neg = negative_row
            _, pos = positive_row
            neg_change = _row_change(neg)
            pos_change = _row_change(pos)
            events.append(
                mapped_event(
                    MappedEventSpec(
                        event_id=f"binance:{path.name}:small_assets:{(neg.get('Coin') or '').strip().upper()}",
                        source=str(profile.source),
                        adapter_id="binance",
                        account=account,
                        wallet=account,
                        timestamp=_parse_transaction_history_timestamp(time_value),
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


def _split_pair(pair: str) -> tuple[str, str]:
    quote_candidates = ("USDT", "USDC", "BUSD", "BTC", "ETH", "BNB", "EUR", "USD", "CAD")
    for quote in quote_candidates:
        if pair.endswith(quote) and len(pair) > len(quote):
            return pair[: -len(quote)], quote
    return "", ""


def _amount_with_asset(value: str) -> tuple[Decimal | None, str]:
    match = re.fullmatch(r"\s*([+-]?[0-9]*\.?[0-9]+)([A-Za-z0-9]+)\s*", value or "")
    if match is None:
        return parse_decimal((value or "").strip()), ""
    amount = parse_decimal(match.group(1))
    return amount, match.group(2).upper()


def _parse_offset_timestamp(value: str, filename: str) -> datetime:
    parsed = datetime.strptime(value, "%y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    match = FILENAME_OFFSET_PATTERN.search(filename)
    if match is None:
        return parsed.replace(tzinfo=None)
    hours = int(match.group("hours"))
    direction = 1 if match.group("sign") == "-" else -1
    return (parsed + timedelta(hours=hours * direction)).replace(tzinfo=None)


def _parse_transaction_history_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%y-%m-%d %H:%M:%S").replace(tzinfo=UTC).replace(tzinfo=None)


def _row_change(row: dict[str, str]) -> Decimal:
    return parse_decimal((row.get("Change") or "").strip()) or Decimal("0")


ADAPTER = BinanceAdapter()
