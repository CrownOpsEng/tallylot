#!/usr/bin/env python3

"""Adapter registry for universal source profiling and normalization."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Sequence
import csv
import json
import re

from coinbase_common import (
    coinbase_balance_rows_from_text,
    csv_dict_rows,
    normalize_coinbase_transactions,
    retail_csv_rows,
)
from pdf_balance_extract import binance_balance_rows_from_text
from pipeline_common import CANONICAL_BALANCE_HEADERS, CANONICAL_EVENT_HEADERS, EXCEPTION_HEADERS, SourceProfile
from script_common import (
    decimal_or_zero,
    decimal_text,
    extract_pdf_text,
    parse_datetime,
    read_cointracking_rows,
    read_csv_rows,
)


DECISION_HEADERS = (
    "manifest_fingerprint",
    "event_id",
    "resolution_status",
    "resolution_note",
)

BINANCE_NUMBER_ASSET_PATTERN = re.compile(r"^\s*([-+]?[0-9]+(?:\.[0-9]+)?)\s*([A-Z0-9]+)\s*$")
BINANCE_TRADE_ID_PATTERN = re.compile(r"TradeID\s*-\s*(?P<trade_id>[A-Za-z0-9_-]+)")
BINANCE_SMALL_ASSET_PATTERN = re.compile(r"^(?P<asset>[A-Z0-9]+)\s+to\s+BNB$", re.IGNORECASE)
BINANCE_TIME_FORMATS = ("%y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")
WEALTHSIMPLE_TIME_FORMATS = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S")


@dataclass(frozen=True)
class AdapterNormalizationResult:
    canonical_events: list[dict[str, str]]
    canonical_balances: list[dict[str, str]]
    exceptions: list[dict[str, str]]


def default_exception_row(
    *,
    manifest_fingerprint: str,
    source: str,
    adapter: str,
    event_id: str,
    raw_file: str,
    raw_row_ref: str,
    exception_kind: str,
    message: str,
    resolution_status: str = "",
    resolution_note: str = "",
) -> dict[str, str]:
    return {
        "manifest_fingerprint": manifest_fingerprint,
        "event_id": event_id,
        "source": source,
        "adapter": adapter,
        "raw_file": raw_file,
        "raw_row_ref": raw_row_ref,
        "exception_kind": exception_kind,
        "message": message,
        "status": "needs_review",
        "resolution_status": resolution_status,
        "resolution_note": resolution_note,
    }


def ct_row_to_canonical_event(row: dict[str, str], adapter_name: str, source_name: str) -> dict[str, str]:
    return {
        "event_id": row["Tx-ID"] or f"{adapter_name}:{row['raw_file']}:{row['raw_row_ref']}",
        "source": source_name,
        "adapter": adapter_name,
        "account": row["Exchange"],
        "wallet": row["Exchange"],
        "raw_file": row["raw_source"],
        "raw_row_ref": row["raw_ref"],
        "timestamp": row["Date"],
        "event_kind": row["Type"],
        "asset_in": row["Buy Cur."],
        "amount_in": row["Buy"],
        "asset_out": row["Sell Cur."],
        "amount_out": row["Sell"],
        "fee_asset": row["Fee Cur."],
        "fee_amount": row["Fee"],
        "tx_hash": row["Tx-ID"],
        "description": row["Comment"],
        "confidence": "high",
        "status": "mapped",
        "render_type": row["Type"],
        "render_exchange": row["Exchange"],
        "render_group": row["Group"],
        "render_comment": row["Comment"],
        "render_comment_mode": row["comment_mode"],
        "render_tx_id": row["Tx-ID"],
        "render_tx_id_mode": row["tx_id_mode"],
        "render_allowed_types": row["allowed_types"],
        "render_match_window_seconds": row["match_window_seconds"],
        "render_fee_tolerance": row["fee_tolerance"],
        "render_notes": row["notes"],
    }


def load_exception_decisions(path: Path | None, manifest_fingerprint: str) -> dict[str, dict[str, str]]:
    if path is None or not path.exists():
        return {}
    rows = read_cointracking_rows(path) if path.suffix.lower() == ".csv" and path.name.endswith("_ct.csv") else []
    if rows:
        return {}

    decisions: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("manifest_fingerprint") != manifest_fingerprint:
                continue
            event_id = row.get("event_id", "")
            if not event_id:
                continue
            decisions[event_id] = {
                "resolution_status": row.get("resolution_status", ""),
                "resolution_note": row.get("resolution_note", ""),
            }
    return decisions


def decisions_fingerprint(decisions: dict[str, dict[str, str]]) -> str:
    payload = [
        {
            "event_id": event_id,
            "resolution_status": values.get("resolution_status", ""),
            "resolution_note": values.get("resolution_note", ""),
        }
        for event_id, values in sorted(decisions.items())
    ]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def normalized_timestamp(value: str, formats: Sequence[str]) -> str:
    return parse_datetime(value.strip(), formats).strftime("%Y-%m-%d %H:%M:%S")


def event_id_for(adapter: str, raw_file: str, raw_row_ref: str) -> str:
    return f"{adapter}:{raw_file}:{raw_row_ref}"


def canonical_event(
    *,
    event_id: str,
    source: str,
    adapter: str,
    account: str,
    wallet: str,
    raw_file: str,
    raw_row_ref: str,
    timestamp: str,
    event_kind: str,
    description: str,
    amount_in: str = "",
    asset_in: str = "",
    amount_out: str = "",
    asset_out: str = "",
    fee_amount: str = "",
    fee_asset: str = "",
    tx_hash: str = "",
    render_group: str = "",
    render_notes: str = "",
) -> dict[str, str]:
    return {
        "event_id": event_id,
        "source": source,
        "adapter": adapter,
        "account": account,
        "wallet": wallet,
        "raw_file": raw_file,
        "raw_row_ref": raw_row_ref,
        "timestamp": timestamp,
        "event_kind": event_kind,
        "asset_in": asset_in,
        "amount_in": amount_in,
        "asset_out": asset_out,
        "amount_out": amount_out,
        "fee_asset": fee_asset,
        "fee_amount": fee_amount,
        "tx_hash": tx_hash,
        "description": description,
        "confidence": "high",
        "status": "mapped",
        "render_type": event_kind,
        "render_exchange": source,
        "render_group": render_group,
        "render_comment": description,
        "render_comment_mode": "exact",
        "render_tx_id": tx_hash,
        "render_tx_id_mode": "exact" if tx_hash else "ignore",
        "render_allowed_types": event_kind,
        "render_match_window_seconds": "0",
        "render_fee_tolerance": "0.00000000",
        "render_notes": render_notes,
    }


def maybe_append_exception(
    exceptions: list[dict[str, str]],
    decisions: dict[str, dict[str, str]],
    *,
    manifest_fingerprint: str,
    source: str,
    adapter: str,
    event_id: str,
    raw_file: str,
    raw_row_ref: str,
    exception_kind: str,
    message: str,
) -> None:
    decision = decisions.get(event_id, {})
    exception = default_exception_row(
        manifest_fingerprint=manifest_fingerprint,
        source=source,
        adapter=adapter,
        event_id=event_id,
        raw_file=raw_file,
        raw_row_ref=raw_row_ref,
        exception_kind=exception_kind,
        message=message,
        resolution_status=decision.get("resolution_status", ""),
        resolution_note=decision.get("resolution_note", ""),
    )
    if exception["resolution_status"] != "accepted":
        exceptions.append(exception)


def parse_number_asset(text: str) -> tuple[str, str]:
    match = BINANCE_NUMBER_ASSET_PATTERN.match(text.strip())
    if match is None:
        raise ValueError(f"Unable to parse amount/asset value: {text!r}")
    amount = decimal_text(decimal_or_zero(match.group(1)))
    asset = match.group(2).upper()
    return amount, asset


def extract_trade_id(text: str) -> str:
    match = BINANCE_TRADE_ID_PATTERN.search(text)
    return match.group("trade_id") if match is not None else ""


def sum_changes(rows: Iterable[dict[str, str]]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        totals[row["Coin"].upper()] += decimal_or_zero(row["Change"])
    return totals


class SourceAdapter:
    name = "base"
    aliases: tuple[str, ...] = ()
    supported = False

    def matches(self, source: str) -> bool:
        slug = source.strip().lower()
        return slug == self.name or slug in self.aliases

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        exception = default_exception_row(
            manifest_fingerprint=profile.manifest_fingerprint,
            source=profile.source,
            adapter=self.name,
            event_id=f"{self.name}:adapter_not_implemented",
            raw_file="",
            raw_row_ref="",
            exception_kind="adapter_not_implemented",
            message=f"No deterministic normalization adapter has been implemented for {profile.source}.",
            resolution_status=exception_decisions.get(f"{self.name}:adapter_not_implemented", {}).get("resolution_status", ""),
            resolution_note=exception_decisions.get(f"{self.name}:adapter_not_implemented", {}).get("resolution_note", ""),
        )
        exceptions = [] if exception["resolution_status"] == "accepted" else [exception]
        return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)


class CoinbaseAdapter(SourceAdapter):
    name = "coinbase"
    aliases = ("coinbase",)
    supported = True

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        retail_path = None
        pro_statement_paths: list[Path] = []
        pro_fill_paths: list[Path] = []
        pdf_paths: list[Path] = []

        for path in sorted(raw_dir.iterdir()):
            if not path.is_file():
                continue
            name = path.name
            if "Statement - All Time" in name and path.suffix.lower() == ".csv":
                retail_path = path
            elif "Coinbase Pro - Statement" in name and path.suffix.lower() == ".csv":
                pro_statement_paths.append(path)
            elif "Coinbase Pro - Fills" in name and path.suffix.lower() == ".csv":
                pro_fill_paths.append(path)
            elif path.suffix.lower() == ".pdf":
                pdf_paths.append(path)

        exceptions: list[dict[str, str]] = []
        if retail_path is None:
            maybe_append_exception(
                exceptions,
                exception_decisions,
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id="coinbase:missing_retail_csv",
                raw_file="",
                raw_row_ref="",
                exception_kind="missing_required_input",
                message="Coinbase retail all-time CSV is required for deterministic normalization.",
            )
            return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)

        normalized_rows = normalize_coinbase_transactions(
            retail_csv_rows(retail_path),
            [dict(row, _file=path.name) for path in pro_statement_paths for row in csv_dict_rows(path, "Coinbase Pro statement CSV")],
            [dict(row, _file=path.name) for path in pro_fill_paths for row in csv_dict_rows(path, "Coinbase Pro fills CSV")],
            retail_source=retail_path,
        )

        events = [ct_row_to_canonical_event(row, self.name, profile.source) for row in normalized_rows]
        balances: list[dict[str, str]] = []
        for pdf_path in pdf_paths:
            balances.extend(coinbase_balance_rows_from_text(extract_pdf_text(pdf_path), pdf_path.name))
        return AdapterNormalizationResult(canonical_events=events, canonical_balances=balances, exceptions=exceptions)


class WealthsimpleAdapter(SourceAdapter):
    name = "wealthsimple"
    aliases = ("wealthsimple", "wealthsimple crypto")
    supported = True

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        activity_paths = sorted(path for path in raw_dir.glob("activities-export*.csv") if path.is_file())
        exceptions: list[dict[str, str]] = []
        if not activity_paths:
            maybe_append_exception(
                exceptions,
                exception_decisions,
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id="wealthsimple:missing_activities_export",
                raw_file="",
                raw_row_ref="",
                exception_kind="missing_required_input",
                message="Wealthsimple activities export CSV is required for deterministic crypto normalization.",
            )
            return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)

        events: list[dict[str, str]] = []
        for path in activity_paths:
            for index, row in enumerate(read_csv_rows(path), start=2):
                if not any((value or "").strip() for value in row.values()):
                    continue
                transaction_date = (row.get("transaction_date") or "").strip()
                if not transaction_date or transaction_date.lower().startswith("as of "):
                    continue
                if (row.get("account_type") or "").strip().lower() != "crypto":
                    continue
                timestamp_source = (row.get("settlement_date") or "").strip() or transaction_date
                timestamp = normalized_timestamp(timestamp_source, WEALTHSIMPLE_TIME_FORMATS)
                raw_row_ref = f"row:{index}"
                event_id = event_id_for(self.name, path.name, raw_row_ref)
                activity_type = (row.get("activity_type") or "").strip()
                activity_sub_type = (row.get("activity_sub_type") or "").strip()
                description = f"{activity_type}:{activity_sub_type or 'base'}"
                account = (row.get("account_id") or "").strip() or "Wealthsimple Crypto"
                quantity = decimal_or_zero(row.get("quantity"))
                currency = (row.get("currency") or "").strip().upper()
                symbol = (row.get("symbol") or "").strip().upper()
                commission = decimal_or_zero(row.get("commission"))
                net_cash = decimal_or_zero(row.get("net_cash_amount"))

                if activity_type == "Trade" and symbol and currency:
                    if activity_sub_type == "BUY":
                        events.append(
                            canonical_event(
                                event_id=event_id,
                                source=profile.source,
                                adapter=self.name,
                                account=account,
                                wallet=account,
                                raw_file=path.name,
                                raw_row_ref=raw_row_ref,
                                timestamp=timestamp,
                                event_kind="Trade",
                                description="Wealthsimple Crypto buy",
                                amount_in=decimal_text(abs(quantity)),
                                asset_in=symbol,
                                amount_out=decimal_text(abs(net_cash)),
                                asset_out=currency,
                                fee_amount=decimal_text(commission),
                                fee_asset=currency,
                                render_notes=description,
                            )
                        )
                        continue
                    if activity_sub_type == "SELL":
                        events.append(
                            canonical_event(
                                event_id=event_id,
                                source=profile.source,
                                adapter=self.name,
                                account=account,
                                wallet=account,
                                raw_file=path.name,
                                raw_row_ref=raw_row_ref,
                                timestamp=timestamp,
                                event_kind="Trade",
                                description="Wealthsimple Crypto sell",
                                amount_in=decimal_text(abs(net_cash)),
                                asset_in=currency,
                                amount_out=decimal_text(abs(quantity)),
                                asset_out=symbol,
                                fee_amount=decimal_text(commission),
                                fee_asset=currency,
                                render_notes=description,
                            )
                        )
                        continue

                if activity_type == "MoneyMovement" and currency:
                    if quantity >= 0:
                        events.append(
                            canonical_event(
                                event_id=event_id,
                                source=profile.source,
                                adapter=self.name,
                                account=account,
                                wallet=account,
                                raw_file=path.name,
                                raw_row_ref=raw_row_ref,
                                timestamp=timestamp,
                                event_kind="Deposit",
                                description=f"Wealthsimple money movement {activity_sub_type or 'credit'}",
                                amount_in=decimal_text(abs(quantity)),
                                asset_in=currency,
                                render_notes=description,
                            )
                        )
                    else:
                        events.append(
                            canonical_event(
                                event_id=event_id,
                                source=profile.source,
                                adapter=self.name,
                                account=account,
                                wallet=account,
                                raw_file=path.name,
                                raw_row_ref=raw_row_ref,
                                timestamp=timestamp,
                                event_kind="Withdrawal",
                                description=f"Wealthsimple money movement {activity_sub_type or 'debit'}",
                                amount_out=decimal_text(abs(quantity)),
                                asset_out=currency,
                                render_notes=description,
                            )
                        )
                    continue

                maybe_append_exception(
                    exceptions,
                    exception_decisions,
                    manifest_fingerprint=profile.manifest_fingerprint,
                    source=profile.source,
                    adapter=self.name,
                    event_id=event_id,
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    exception_kind="unsupported_row",
                    message=f"Unsupported Wealthsimple crypto activity: {activity_type}/{activity_sub_type}",
                )

        return AdapterNormalizationResult(canonical_events=events, canonical_balances=[], exceptions=exceptions)


class BinanceAdapter(SourceAdapter):
    name = "binance"
    aliases = ("binance",)
    supported = True

    _trade_operations = {
        "Buy",
        "Sell",
        "Fee",
        "Transaction Buy",
        "Transaction Spend",
        "Transaction Fee",
        "Transaction Revenue",
        "Transaction Sold",
        "Transaction Related",
        "Binance Convert",
        "Small Assets Exchange BNB",
        "ETH 2.0 Staking",
        "Token Swap - Redenomination/Rebranding",
        "BETH to WBETH Wrapping",
    }
    _ignored_operations = {
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
    _income_type_by_operation = {
        "Staking Rewards": "Staking",
        "ETH 2.0 Staking Rewards": "Staking",
        "Simple Earn Flexible Interest": "Interest Income",
        "Launchpool Airdrop - User Claim Distribution": "Interest Income",
        "Airdrop Assets": "Airdrop",
        "Token Swap - Distribution": "Reward / Bonus",
    }

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        events: list[dict[str, str]] = []
        exceptions: list[dict[str, str]] = []
        balances: list[dict[str, str]] = []
        covered_timestamps: set[str] = set()
        has_c2c_history = any(path.name.startswith("Binance-C2C-Order-History-") for path in raw_dir.glob("*.csv"))

        for pdf_path in sorted(raw_dir.glob("AccountStatementPeriod_*.pdf")):
            balances.extend(binance_balance_rows_from_text(extract_pdf_text(pdf_path), pdf_path.name))

        for path in sorted(raw_dir.glob("*.csv")):
            name = path.name
            if name.startswith("Binance-Spot-Trade-History-"):
                events.extend(self._spot_trade_events(path, profile.source))
                covered_timestamps.update(self._timestamps_for_file(path, "Time", status_field=None, allowed_statuses=None))
            elif name.startswith("Binance-Convert-Order-History-"):
                events.extend(self._convert_order_events(path, profile.source))
                covered_timestamps.update(self._convert_covered_timestamps(path))
            elif name.startswith("Binance-Deposit-History-"):
                events.extend(self._deposit_history_events(path, profile.source))
                covered_timestamps.update(self._timestamps_for_file(path, "Time", status_field="Status", allowed_statuses={"Completed"}))
            elif name.startswith("Binance-Withdraw-History-"):
                events.extend(self._withdraw_history_events(path, profile.source))
                covered_timestamps.update(self._timestamps_for_file(path, "Time", status_field="Status", allowed_statuses={"Completed"}))
            elif name.startswith("Binance-Fiat-Buy-History-"):
                events.extend(self._fiat_buy_history_events(path, profile.source))
                covered_timestamps.update(self._timestamps_for_file(path, "Time", status_field="Status", allowed_statuses={"Successful"}))
            elif name.startswith("Binance-Fiat-Sell-History-"):
                events.extend(self._fiat_sell_history_events(path, profile.source))
                covered_timestamps.update(self._timestamps_for_file(path, "Time", status_field="Status", allowed_statuses={"Successful"}))
            elif name.startswith("Binance-C2C-Order-History-"):
                events.extend(self._c2c_order_events(path, profile.source))
                covered_timestamps.update(self._timestamps_for_file(path, "Created Time", status_field="Status", allowed_statuses={"Completed"}))
            elif name.startswith("Binance-Transaction-History-") or re.match(r"^Binance Transactions \d{4}\.csv$", name):
                events.extend(
                    self._transaction_history_events(
                        path,
                        profile,
                        exception_decisions=exception_decisions,
                        covered_timestamps=covered_timestamps,
                        has_c2c_history=has_c2c_history,
                        exceptions=exceptions,
                    )
                )

        return AdapterNormalizationResult(canonical_events=events, canonical_balances=balances, exceptions=exceptions)

    def _timestamps_for_file(
        self,
        path: Path,
        field: str,
        *,
        status_field: str | None,
        allowed_statuses: set[str] | None,
    ) -> set[str]:
        timestamps: set[str] = set()
        for row in read_csv_rows(path):
            values = [str(value).strip() for value in row.values() if value not in (None, "")]
            if values == ["No data matches the criteria."] or not any(values):
                continue
            if status_field is not None and allowed_statuses is not None:
                if (row.get(status_field) or "").strip() not in allowed_statuses:
                    continue
            timestamp = (row.get(field) or "").strip()
            if timestamp:
                timestamps.add(timestamp)
        return timestamps

    def _convert_covered_timestamps(self, path: Path) -> set[str]:
        timestamps = self._timestamps_for_file(path, "Time", status_field="Status", allowed_statuses={"Successful"})
        timestamps.update(self._timestamps_for_file(path, "Date Updated", status_field="Status", allowed_statuses={"Successful"}))
        return timestamps

    def _spot_trade_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            executed_amount, executed_asset = parse_number_asset(row["Executed"])
            quote_amount, quote_asset = parse_number_asset(row["Amount"])
            fee_amount, fee_asset = parse_number_asset(row["Fee"])
            timestamp = normalized_timestamp(row["Time"], BINANCE_TIME_FORMATS)
            side = (row.get("Side") or "").strip().upper()
            raw_row_ref = f"row:{index}"
            event_id = event_id_for(self.name, path.name, raw_row_ref)
            if side == "BUY":
                amount_in, asset_in = executed_amount, executed_asset
                amount_out, asset_out = quote_amount, quote_asset
            else:
                amount_in, asset_in = quote_amount, quote_asset
                amount_out, asset_out = executed_amount, executed_asset
            events.append(
                canonical_event(
                    event_id=event_id,
                    source=source,
                    adapter=self.name,
                    account="Spot",
                    wallet="Spot",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=timestamp,
                    event_kind="Trade",
                    description=f"Binance spot {side.lower()} {row['Pair']}",
                    amount_in=amount_in,
                    asset_in=asset_in,
                    amount_out=amount_out,
                    asset_out=asset_out,
                    fee_amount=fee_amount,
                    fee_asset=fee_asset,
                    render_group="Spot",
                    render_notes=row["Pair"],
                )
            )
        return events

    def _convert_order_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            if (row.get("Status") or "").strip() != "Successful":
                continue
            sell_amount, sell_asset = parse_number_asset(row["Sell"])
            buy_amount, buy_asset = parse_number_asset(row["Buy"])
            timestamp = normalized_timestamp(row["Time"], BINANCE_TIME_FORMATS)
            raw_row_ref = f"row:{index}"
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account=(row.get("Wallet") or "Spot").strip() or "Spot",
                    wallet=(row.get("Wallet") or "Spot").strip() or "Spot",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=timestamp,
                    event_kind="Trade",
                    description=f"Binance convert {row['Pair']}",
                    amount_in=buy_amount,
                    asset_in=buy_asset,
                    amount_out=sell_amount,
                    asset_out=sell_asset,
                    render_group=(row.get("Wallet") or "Spot").strip().title() or "Spot",
                    render_notes="Binance Convert",
                )
            )
        return events

    def _deposit_history_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            if (row.get("Status") or "").strip() != "Completed":
                continue
            raw_row_ref = f"row:{index}"
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account="Binance",
                    wallet="Funding",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(row["Time"], BINANCE_TIME_FORMATS),
                    event_kind="Deposit",
                    description=f"Binance deposit via {row['Network']}",
                    amount_in=decimal_text(decimal_or_zero(row["Amount"])),
                    asset_in=(row.get("Coin") or "").strip().upper(),
                    tx_hash=(row.get("TXID") or "").strip(),
                    render_group="Funding",
                    render_notes=row.get("Address", ""),
                )
            )
        return events

    def _withdraw_history_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            if (row.get("Status") or "").strip() != "Completed":
                continue
            asset = (row.get("Coin") or "").strip().upper()
            raw_row_ref = f"row:{index}"
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account="Binance",
                    wallet="Funding",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(row["Time"], BINANCE_TIME_FORMATS),
                    event_kind="Withdrawal",
                    description=f"Binance withdrawal via {row['Network']}",
                    amount_out=decimal_text(decimal_or_zero(row["Amount"])),
                    asset_out=asset,
                    fee_amount=decimal_text(decimal_or_zero(row.get("Fee"))),
                    fee_asset=asset,
                    tx_hash=(row.get("TXID") or "").strip(),
                    render_group="Funding",
                    render_notes=row.get("Address", ""),
                )
            )
        return events

    def _fiat_buy_history_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            if (row.get("Status") or "").strip() != "Successful":
                continue
            spend_amount, spend_asset = parse_number_asset(row["Spend Amount"])
            receive_amount, receive_asset = parse_number_asset(row["Receive Amount"])
            fee_amount, fee_asset = parse_number_asset(row["Fee"])
            raw_row_ref = f"row:{index}"
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account="Funding",
                    wallet="Funding",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(row["Time"], BINANCE_TIME_FORMATS),
                    event_kind="Trade",
                    description=f"Binance fiat buy via {row['Method']}",
                    amount_in=receive_amount,
                    asset_in=receive_asset,
                    amount_out=spend_amount,
                    asset_out=spend_asset,
                    fee_amount=fee_amount,
                    fee_asset=fee_asset,
                    tx_hash=(row.get("Transaction ID") or "").strip(),
                    render_group="Funding",
                    render_notes=row.get("Price", ""),
                )
            )
        return events

    def _fiat_sell_history_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            values = [str(value).strip() for value in row.values() if value not in (None, "")]
            if values == ["No data matches the criteria."] or (row.get("Status") or "").strip() != "Successful":
                continue
            spend_amount, spend_asset = parse_number_asset(row["Spend Amount"])
            receive_amount, receive_asset = parse_number_asset(row["Receive Amount"])
            fee_amount, fee_asset = parse_number_asset(row["Fee"])
            raw_row_ref = f"row:{index}"
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account="Funding",
                    wallet="Funding",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(row["Time"], BINANCE_TIME_FORMATS),
                    event_kind="Trade",
                    description=f"Binance fiat sell via {row['Method']}",
                    amount_in=receive_amount,
                    asset_in=receive_asset,
                    amount_out=spend_amount,
                    asset_out=spend_asset,
                    fee_amount=fee_amount,
                    fee_asset=fee_asset,
                    tx_hash=(row.get("Transaction ID") or "").strip(),
                    render_group="Funding",
                    render_notes=row.get("Price", ""),
                )
            )
        return events

    def _c2c_order_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            if (row.get("Status") or "").strip() != "Completed":
                continue
            raw_row_ref = f"row:{index}"
            order_type = (row.get("Order Type") or "").strip().lower()
            fiat_asset = (row.get("Fiat Type") or "").strip().upper()
            crypto_asset = (row.get("Asset") or "").strip().upper()
            fiat_amount = decimal_text(decimal_or_zero(row["Total Price"]))
            crypto_amount = decimal_text(decimal_or_zero(row["Quantity"]))
            amount_in, asset_in = (fiat_amount, fiat_asset) if order_type == "sell" else (crypto_amount, crypto_asset)
            amount_out, asset_out = (crypto_amount, crypto_asset) if order_type == "sell" else (fiat_amount, fiat_asset)
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account="Funding",
                    wallet="Funding",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(row["Created Time"], BINANCE_TIME_FORMATS),
                    event_kind="Trade",
                    description=f"Binance P2P {order_type} {crypto_asset}/{fiat_asset}",
                    amount_in=amount_in,
                    asset_in=asset_in,
                    amount_out=amount_out,
                    asset_out=asset_out,
                    tx_hash=(row.get("Order Number") or "").strip(),
                    render_group="Funding",
                    render_notes=row.get("Counterparty", ""),
                )
            )
        return events

    def _transaction_history_events(
        self,
        path: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
        covered_timestamps: set[str],
        has_c2c_history: bool,
        exceptions: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        groups: dict[tuple[str, str], list[tuple[int, dict[str, str]]]] = defaultdict(list)
        for index, row in enumerate(read_csv_rows(path), start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            groups[((row.get("Time") or "").strip(), (row.get("Account") or "").strip())].append((index, row))

        events: list[dict[str, str]] = []
        for (timestamp_text, account), indexed_rows in sorted(groups.items()):
            if not timestamp_text:
                continue
            if timestamp_text in covered_timestamps:
                continue

            active_rows = [(index, row) for index, row in indexed_rows if (row.get("Operation") or "").strip() not in self._ignored_operations]
            if not active_rows:
                continue

            filtered_rows = list(active_rows)
            operations = {(row.get("Operation") or "").strip() for _, row in filtered_rows}
            if operations & self._trade_operations and operations & {"Deposit", "Withdraw"}:
                filtered_rows = [
                    (index, row)
                    for index, row in filtered_rows
                    if (row.get("Operation") or "").strip() not in {"Deposit", "Withdraw"}
                ]
            active_rows = filtered_rows
            operations = {(row.get("Operation") or "").strip() for _, row in active_rows}
            if operations == {"P2P Trading"} and has_c2c_history:
                continue

            if operations <= self._income_type_by_operation.keys() | {"Distribution", "Realized Profit and Loss", "Funding Fee", "Asset Recovery", "Deposit", "Withdraw", "Fee"}:
                events.extend(self._single_row_events(path, profile.source, account, active_rows))
                continue

            if operations <= self._trade_operations:
                parsed = self._grouped_trade_events(
                    path,
                    profile,
                    account,
                    timestamp_text,
                    active_rows,
                    exception_decisions=exception_decisions,
                )
                events.extend(parsed[0])
                if parsed[1] is not None and parsed[1].get("resolution_status") != "accepted":
                    exceptions.append(parsed[1])
                continue

            raw_row_ref = f"group:{timestamp_text}:{account or 'unknown'}"
            event_id = event_id_for(self.name, path.name, raw_row_ref)
            maybe_append_exception(
                exceptions,
                exception_decisions,
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id=event_id,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                exception_kind="unsupported_group",
                message=f"Unsupported Binance transaction-history operations: {', '.join(sorted(operations))}",
            )
        return events

    def _single_row_events(
        self,
        path: Path,
        source: str,
        account: str,
        indexed_rows: list[tuple[int, dict[str, str]]],
    ) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in indexed_rows:
            operation = (row.get("Operation") or "").strip()
            amount = decimal_text(abs(decimal_or_zero(row.get("Change"))))
            asset = (row.get("Coin") or "").strip().upper()
            timestamp = normalized_timestamp(row["Time"], BINANCE_TIME_FORMATS)
            raw_row_ref = f"row:{index}"
            event_id = event_id_for(self.name, path.name, raw_row_ref)
            description = row.get("Remark", "") or operation
            tx_hash = extract_trade_id(row.get("Remark", ""))

            if operation in self._income_type_by_operation:
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=source,
                        adapter=self.name,
                        account=account or "Spot",
                        wallet=account or "Spot",
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind=self._income_type_by_operation[operation],
                        description=description,
                        amount_in=amount,
                        asset_in=asset,
                        tx_hash=tx_hash,
                        render_group=account or "Spot",
                        render_notes=operation,
                    )
                )
            elif operation == "Deposit":
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=source,
                        adapter=self.name,
                        account=account or "Spot",
                        wallet=account or "Spot",
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind="Deposit",
                        description=description,
                        amount_in=amount,
                        asset_in=asset,
                        tx_hash=tx_hash,
                        render_group=account or "Spot",
                        render_notes=operation,
                    )
                )
            elif operation == "Withdraw":
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=source,
                        adapter=self.name,
                        account=account or "Spot",
                        wallet=account or "Spot",
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind="Withdrawal",
                        description=description,
                        amount_out=amount,
                        asset_out=asset,
                        tx_hash=tx_hash,
                        render_group=account or "Spot",
                        render_notes=operation,
                    )
                )
            elif operation == "Fee":
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=source,
                        adapter=self.name,
                        account=account or "Spot",
                        wallet=account or "Spot",
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind="Other Fee",
                        description=description,
                        amount_out=amount,
                        asset_out=asset,
                        tx_hash=tx_hash,
                        render_group=account or "Spot",
                        render_notes=operation,
                    )
                )
            elif operation == "Distribution":
                event_kind = "Airdrop" if "airdrop" in description.lower() else "Reward / Bonus"
                if decimal_or_zero(row.get("Change")) >= 0:
                    events.append(
                        canonical_event(
                            event_id=event_id,
                            source=source,
                            adapter=self.name,
                            account=account or "Spot",
                            wallet=account or "Spot",
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            timestamp=timestamp,
                            event_kind=event_kind,
                            description=description,
                            amount_in=amount,
                            asset_in=asset,
                            render_group=account or "Spot",
                            render_notes=operation,
                        )
                    )
                else:
                    events.append(
                        canonical_event(
                            event_id=event_id,
                            source=source,
                            adapter=self.name,
                            account=account or "Spot",
                            wallet=account or "Spot",
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            timestamp=timestamp,
                            event_kind="Other Expense",
                            description=description,
                            amount_out=amount,
                            asset_out=asset,
                            render_group=account or "Spot",
                            render_notes=operation,
                        )
                    )
            elif operation == "Asset Recovery":
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=source,
                        adapter=self.name,
                        account=account or "Spot",
                        wallet=account or "Spot",
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind="Other Expense",
                        description=description,
                        amount_out=amount,
                        asset_out=asset,
                        render_group=account or "Spot",
                        render_notes=operation,
                    )
                )
            elif operation in {"Realized Profit and Loss", "Funding Fee"}:
                event_kind = "Derivatives / Futures Profit" if decimal_or_zero(row.get("Change")) >= 0 else "Derivatives / Futures Loss"
                payload = {
                    "event_id": event_id,
                    "source": source,
                    "adapter": self.name,
                    "account": account or "USD-M Futures",
                    "wallet": account or "USD-M Futures",
                    "raw_file": path.name,
                    "raw_row_ref": raw_row_ref,
                    "timestamp": timestamp,
                    "event_kind": event_kind,
                    "description": description,
                    "render_group": account or "USD-M Futures",
                    "render_notes": operation,
                    "tx_hash": tx_hash,
                }
                if decimal_or_zero(row.get("Change")) >= 0:
                    payload.update({"amount_in": amount, "asset_in": asset})
                else:
                    payload.update({"amount_out": amount, "asset_out": asset})
                events.append(canonical_event(**payload))
        return events

    def _grouped_trade_events(
        self,
        path: Path,
        profile: SourceProfile,
        account: str,
        timestamp_text: str,
        indexed_rows: list[tuple[int, dict[str, str]]],
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> tuple[list[dict[str, str]], dict[str, str] | None]:
        rows = [row for _, row in indexed_rows]
        operations = {(row.get("Operation") or "").strip() for row in rows}
        raw_row_ref = f"group:{timestamp_text}:{account or 'unknown'}"
        timestamp = normalized_timestamp(timestamp_text, BINANCE_TIME_FORMATS)

        if operations == {"Small Assets Exchange BNB"}:
            events, message = self._small_asset_exchange_events(path, profile.source, account, timestamp, indexed_rows)
            if message is None:
                return events, None
            event_id = event_id_for(self.name, path.name, raw_row_ref)
            return [], default_exception_row(
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id=event_id,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                exception_kind="ambiguous_group",
                message=message,
                resolution_status=exception_decisions.get(event_id, {}).get("resolution_status", ""),
                resolution_note=exception_decisions.get(event_id, {}).get("resolution_note", ""),
            )

        fee_rows = [row for row in rows if (row.get("Operation") or "").strip() in {"Fee", "Transaction Fee"}]
        non_fee_rows = [row for row in rows if row not in fee_rows]
        positive = {asset: total for asset, total in sum_changes(non_fee_rows).items() if total > 0}
        negative = {asset: abs(total) for asset, total in sum_changes(non_fee_rows).items() if total < 0}
        fee_totals = {asset: abs(total) for asset, total in sum_changes(fee_rows).items() if total != 0}

        if not positive and not negative and len(fee_totals) == 1:
            fee_asset, fee_amount = next(iter(fee_totals.items()))
            event = canonical_event(
                event_id=event_id_for(self.name, path.name, raw_row_ref),
                source=profile.source,
                adapter=self.name,
                account=account or "Spot",
                wallet=account or "Spot",
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Other Fee",
                description=rows[0].get("Remark", "") or "Binance fee row",
                amount_out=decimal_text(fee_amount),
                asset_out=fee_asset,
                render_group=account or "Spot",
                render_notes=", ".join(sorted(operations)),
            )
            return [event], None

        if len(positive) == 1 and len(negative) == 1 and len(fee_totals) <= 1:
            asset_in, amount_in = next(iter(positive.items()))
            asset_out, amount_out = next(iter(negative.items()))
            fee_asset = ""
            fee_amount = ""
            if fee_totals:
                fee_asset, fee_total = next(iter(fee_totals.items()))
                fee_amount = decimal_text(fee_total)
            trade_id = next((extract_trade_id(row.get("Remark", "")) for row in rows if extract_trade_id(row.get("Remark", ""))), "")
            event = canonical_event(
                event_id=event_id_for(self.name, path.name, raw_row_ref),
                source=profile.source,
                adapter=self.name,
                account=account or "Spot",
                wallet=account or "Spot",
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Trade",
                description=rows[0].get("Remark", "") or "Binance grouped trade",
                amount_in=decimal_text(amount_in),
                asset_in=asset_in,
                amount_out=decimal_text(amount_out),
                asset_out=asset_out,
                fee_amount=fee_amount,
                fee_asset=fee_asset,
                tx_hash=trade_id,
                render_group=account or "Spot",
                render_notes=", ".join(sorted(operations)),
            )
            return [event], None

        event_id = event_id_for(self.name, path.name, raw_row_ref)
        decision = exception_decisions.get(event_id, {})
        return [], default_exception_row(
            manifest_fingerprint=profile.manifest_fingerprint,
            source=profile.source,
            adapter=self.name,
            event_id=event_id,
            raw_file=path.name,
            raw_row_ref=raw_row_ref,
            exception_kind="ambiguous_group",
            message=f"Unable to safely collapse Binance grouped rows with operations: {', '.join(sorted(operations))}",
            resolution_status=decision.get("resolution_status", ""),
            resolution_note=decision.get("resolution_note", ""),
        )

    def _small_asset_exchange_events(
        self,
        path: Path,
        source: str,
        account: str,
        timestamp: str,
        indexed_rows: list[tuple[int, dict[str, str]]],
    ) -> tuple[list[dict[str, str]], str | None]:
        buy_by_asset: dict[str, Decimal] = defaultdict(Decimal)
        sell_by_asset: dict[str, Decimal] = defaultdict(Decimal)
        raw_refs: dict[str, list[str]] = defaultdict(list)
        unresolved = False

        for index, row in indexed_rows:
            coin = (row.get("Coin") or "").strip().upper()
            change = decimal_or_zero(row.get("Change"))
            raw_refs[coin].append(f"row:{index}")
            remark_match = BINANCE_SMALL_ASSET_PATTERN.match((row.get("Remark") or "").strip())
            mapped_asset = (remark_match.group("asset") if remark_match is not None else coin).upper()
            if change < 0 and coin != "BNB":
                sell_by_asset[mapped_asset] += abs(change)
            elif change > 0 and coin == "BNB":
                buy_by_asset[mapped_asset] += change
            else:
                unresolved = True

        if unresolved or set(buy_by_asset) != set(sell_by_asset):
            return [], "Unable to safely pair Binance Small Assets Exchange rows into asset-specific BNB trades."

        events: list[dict[str, str]] = []
        for asset in sorted(sell_by_asset):
            raw_row_ref = f"small_assets:{asset}"
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account=account or "Spot",
                    wallet=account or "Spot",
                    raw_file=path.name,
                    raw_row_ref=";".join(sorted(raw_refs.get(asset, []))),
                    timestamp=timestamp,
                    event_kind="Trade",
                    description=f"Binance dust conversion {asset} to BNB",
                    amount_in=decimal_text(buy_by_asset[asset]),
                    asset_in="BNB",
                    amount_out=decimal_text(sell_by_asset[asset]),
                    asset_out=asset,
                    render_group=account or "Spot",
                    render_notes="Small Assets Exchange BNB",
                )
            )
        return events, None


class MetamaskAdapter(SourceAdapter):
    name = "metamask"
    aliases = ("metamask", "bsc metamask wallet", "eth metamask wallet", "metamask - polygon")


class ShakepayAdapter(SourceAdapter):
    name = "shakepay"
    aliases = ("shakepay",)


class LedgerLiveAdapter(SourceAdapter):
    name = "ledger_live"
    aliases = ("ledger live", "ada ledger")


class NearAdapter(SourceAdapter):
    name = "near"
    aliases = ("near", "near wallet", "near wallet - staking")


ADAPTERS: tuple[SourceAdapter, ...] = (
    CoinbaseAdapter(),
    WealthsimpleAdapter(),
    BinanceAdapter(),
    MetamaskAdapter(),
    ShakepayAdapter(),
    LedgerLiveAdapter(),
    NearAdapter(),
)


def get_adapter(source: str) -> SourceAdapter:
    for adapter in ADAPTERS:
        if adapter.matches(source):
            return adapter
    fallback = SourceAdapter()
    fallback.name = "generic"
    fallback.aliases = ()
    return fallback


def available_adapter_rows() -> list[dict[str, str]]:
    return [
        {
            "adapter": adapter.name,
            "supported": "yes" if adapter.supported else "no",
            "aliases": ", ".join(adapter.aliases),
        }
        for adapter in ADAPTERS
    ]
