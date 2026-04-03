#!/usr/bin/env python3

"""Coinbase raw-export normalization and statement-balance helpers."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from script_common import (
    COINTRACKING_HEADERS,
    coerce_datetime_to_utc_naive,
    decimal_text,
    normalize_whitespace,
    parse_datetime_to_utc_naive,
    parse_decimal,
    require_file,
)


COINTRACKING_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
COINBASE_RETAIL_TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"
COINBASE_PRO_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

COINBASE_METADATA_HEADERS = (
    "match_window_seconds",
    "fee_tolerance",
    "comment_mode",
    "tx_id_mode",
    "allowed_types",
    "raw_source",
    "raw_ref",
    "notes",
)

COINBASE_NORMALIZED_HEADERS = (*COINTRACKING_HEADERS, *COINBASE_METADATA_HEADERS)

BALANCE_HEADERS = (
    "source",
    "account",
    "wallet",
    "balance_kind",
    "asset",
    "quantity",
    "staked_quantity",
    "value_amount",
    "value_currency",
    "price_amount",
    "price_currency",
    "as_of",
    "pdf_file",
    "notes",
)

CONVERT_NOTES_PATTERN = re.compile(
    r"^Converted (?P<sell_qty>[0-9.]+) (?P<sell_asset>[A-Z0-9]+) to (?P<buy_qty>[0-9.]+) (?P<buy_asset>[A-Z0-9]+)$"
)
BUY_NOTES_PATTERN = re.compile(
    r"^Bought (?P<buy_qty>[0-9.]+) (?P<asset>[A-Z0-9]+) for (?P<total>[0-9.]+) (?P<currency>[A-Z]{3})"
)
PORTFOLIO_ROW_PATTERN = re.compile(
    r"(?P<asset>[A-Z0-9]+)\s+"
    r"(?P<quantity>[0-9.]+)\s+"
    r"(?P<staked>N/A|[0-9.]+)\s+"
    r"(?P<price>[0-9.,]+)\s+CAD/(?P=asset)\s+"
    r"(?P<value>[0-9.]+)\s+CAD"
)
PORTFOLIO_ROW_FALLBACK_PATTERN = re.compile(
    r"(?P<quantity>[0-9.]+)\s+"
    r"(?P<staked>N/A|[0-9.]+)\s+"
    r"(?P<price>[0-9.,]+)\s+CAD/(?P<asset>[A-Z0-9]+)\s+"
    r"(?P<value>[0-9.]+)\s+CAD"
)
COINBASE_CLOSING_CASH_PATTERN = re.compile(
    r"Closing Balance\s+(?P<balance>[0-9.,]+)\s+(?P<currency>[A-Z]{3})\s+as of (?P<as_of>[0-9:-]+\s+[0-9:]+\s+UTC)"
)
COINBASE_PORTFOLIO_AS_OF_PATTERN = re.compile(
    r"Portfolio summary balances are as of (?P<as_of>[0-9:-]+\s+[0-9:]+\s+UTC)"
)


def compact_decimal_text(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def ct_date_text(value: datetime) -> str:
    return coerce_datetime_to_utc_naive(value).strftime(COINTRACKING_TIME_FORMAT)


def parse_coinbase_retail_timestamp(value: str) -> datetime:
    return parse_datetime_to_utc_naive(value, (COINBASE_RETAIL_TIME_FORMAT,))


def parse_coinbase_pro_timestamp(value: str) -> datetime:
    return parse_datetime_to_utc_naive(value, (COINBASE_PRO_TIME_FORMAT,))


def format_amount(value: Decimal | None) -> str:
    if value is None:
        return ""
    return decimal_text(value)


def retail_csv_rows(path: Path) -> list[dict[str, str]]:
    path = require_file(path.resolve(), "Coinbase retail CSV")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    header_index = next(
        (index for index, row in enumerate(rows) if row[:3] == ["ID", "Timestamp", "Transaction Type"]),
        None,
    )
    if header_index is None:
        raise ValueError(f"Coinbase retail CSV header not found in {path}")
    header = rows[header_index]
    return [
        dict(zip(header, row))
        for row in rows[header_index + 1 :]
        if any(cell.strip() for cell in row)
    ]


def csv_dict_rows(path: Path, label: str) -> list[dict[str, str]]:
    path = require_file(path.resolve(), label)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def build_row(
    *,
    tx_type: str,
    buy_amount: Decimal | None = None,
    buy_currency: str = "",
    sell_amount: Decimal | None = None,
    sell_currency: str = "",
    fee_amount: Decimal | None = None,
    fee_currency: str = "",
    exchange: str,
    group: str = "",
    comment: str = "",
    date: datetime,
    tx_id: str = "",
    match_window_seconds: int,
    fee_tolerance: Decimal = Decimal("0"),
    comment_mode: str = "exact",
    tx_id_mode: str = "ignore",
    allowed_types: Iterable[str] | None = None,
    raw_source: str,
    raw_ref: str,
    notes: str = "",
) -> dict[str, str]:
    allowed = list(allowed_types or [tx_type])
    return {
        "Type": tx_type,
        "Buy": format_amount(buy_amount),
        "Buy Cur.": buy_currency,
        "Sell": format_amount(sell_amount),
        "Sell Cur.": sell_currency,
        "Fee": format_amount(fee_amount if fee_amount is not None else Decimal("0")),
        "Fee Cur.": fee_currency,
        "Exchange": exchange,
        "Group": group,
        "Comment": comment,
        "Date": ct_date_text(date),
        "Tx-ID": tx_id,
        "match_window_seconds": str(match_window_seconds),
        "fee_tolerance": decimal_text(fee_tolerance),
        "comment_mode": comment_mode,
        "tx_id_mode": tx_id_mode,
        "allowed_types": "|".join(allowed),
        "raw_source": raw_source,
        "raw_ref": raw_ref,
        "notes": notes,
    }


def build_buy_comment(quantity: Decimal, asset: str, total: Decimal, currency: str) -> str:
    return f"Bought {compact_decimal_text(quantity)} {asset} for ${total.quantize(Decimal('0.01'))} {currency}"


def send_comment_from_notes(notes: str) -> str:
    return notes.split(" (to ", 1)[0]


def find_matching_pro_statement(
    retail_row: dict[str, str],
    statement_rows: list[dict[str, str]],
) -> dict[str, str] | None:
    retail_dt = parse_coinbase_retail_timestamp(retail_row["Timestamp"])
    retail_type = retail_row["Transaction Type"]
    expected_statement_type = "deposit" if retail_type == "Pro Withdrawal" else "withdrawal"
    target_amount = abs(parse_decimal(retail_row["Quantity Transacted"]) or Decimal("0"))
    asset = retail_row["Asset"]
    matches = []
    for row in statement_rows:
        if row["type"] != expected_statement_type:
            continue
        if row["amount/balance unit"] != asset:
            continue
        amount = abs(parse_decimal(row["amount"]) or Decimal("0"))
        if amount != target_amount:
            continue
        dt = parse_coinbase_pro_timestamp(row["time"])
        if abs((dt - retail_dt).total_seconds()) > 90:
            continue
        matches.append(row)
    return sorted(matches, key=lambda row: row["time"])[0] if matches else None


def normalize_coinbase_transactions(
    retail_rows: list[dict[str, str]],
    pro_statement_rows: list[dict[str, str]],
    pro_fill_rows: list[dict[str, str]],
    *,
    retail_source: Path,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    asset_migrations: dict[str, list[dict[str, str]]] = defaultdict(list)

    for raw in retail_rows:
        tx_type = raw["Transaction Type"]
        if tx_type == "Asset Migration":
            asset_migrations[raw["Timestamp"]].append(raw)
            continue

        dt = parse_coinbase_retail_timestamp(raw["Timestamp"])
        raw_source = retail_source.name
        raw_ref = raw["ID"]
        quantity = parse_decimal(raw["Quantity Transacted"]) or Decimal("0")
        fee = parse_decimal(raw["Fees and/or Spread"]) or Decimal("0")
        total = parse_decimal(raw["Total (inclusive of fees and/or spread)"]) or Decimal("0")
        asset = raw["Asset"]
        price_currency = raw["Price Currency"]

        if tx_type == "Buy":
            rows.append(
                build_row(
                    tx_type="Trade",
                    buy_amount=quantity,
                    buy_currency=asset,
                    sell_amount=abs(total),
                    sell_currency=price_currency,
                    fee_amount=fee,
                    fee_currency=price_currency,
                    exchange="Coinbase",
                    comment=build_buy_comment(quantity, asset, abs(total), price_currency),
                    date=dt,
                    tx_id=f"coinbase-retail-{raw_ref}",
                    match_window_seconds=20,
                    fee_tolerance=Decimal("0.03000000"),
                    raw_source=raw_source,
                    raw_ref=raw_ref,
                    notes="Retail Buy row normalized from Coinbase raw export",
                )
            )
            continue

        if tx_type == "Convert":
            match = CONVERT_NOTES_PATTERN.match(raw["Notes"])
            if match is None:
                raise ValueError(f"Unable to parse Coinbase Convert notes: {raw['Notes']!r}")
            rows.append(
                build_row(
                    tx_type="Trade",
                    buy_amount=parse_decimal(match.group("buy_qty")),
                    buy_currency=match.group("buy_asset"),
                    sell_amount=abs(quantity),
                    sell_currency=asset,
                    fee_amount=fee,
                    fee_currency=price_currency,
                    exchange="Coinbase",
                    comment=raw["Notes"],
                    date=dt,
                    tx_id=f"coinbase-convert-{raw_ref}",
                    match_window_seconds=5,
                    fee_tolerance=Decimal("0.03000000"),
                    raw_source=raw_source,
                    raw_ref=raw_ref,
                    notes="Retail Convert row normalized from Coinbase raw export",
                )
            )
            continue

        if tx_type == "Send":
            rows.append(
                build_row(
                    tx_type="Withdrawal",
                    sell_amount=abs(quantity),
                    sell_currency=asset,
                    fee_amount=Decimal("0"),
                    fee_currency=asset,
                    exchange="Coinbase",
                    comment=send_comment_from_notes(raw["Notes"]),
                    date=dt,
                    tx_id=f"coinbase-send-{raw_ref}",
                    match_window_seconds=60,
                    comment_mode="ignore",
                    tx_id_mode="ignore",
                    allowed_types=("Withdrawal", "Spend"),
                    raw_source=raw_source,
                    raw_ref=raw_ref,
                    notes="Retail Send row normalized without any unsupported fee leg",
                )
            )
            continue

        if tx_type == "Reward Income":
            rows.append(
                build_row(
                    tx_type="Interest Income",
                    buy_amount=quantity,
                    buy_currency=asset,
                    fee_amount=Decimal("0"),
                    fee_currency=asset,
                    exchange="Coinbase",
                    comment="Cardano reward",
                    date=dt,
                    tx_id=f"coinbase-reward-income-{raw_ref}",
                    match_window_seconds=2,
                    raw_source=raw_source,
                    raw_ref=raw_ref,
                    notes="Coinbase Reward Income normalized to Interest Income",
                )
            )
            continue

        if tx_type == "Learning Reward":
            rows.append(
                build_row(
                    tx_type="Reward / Bonus",
                    buy_amount=quantity,
                    buy_currency=asset,
                    fee_amount=Decimal("0"),
                    fee_currency=asset,
                    exchange="Coinbase",
                    comment="Earn Task",
                    date=dt,
                    tx_id=f"coinbase-learning-reward-{raw_ref}",
                    match_window_seconds=2,
                    raw_source=raw_source,
                    raw_ref=raw_ref,
                    notes="Coinbase Learning Reward normalized to Reward / Bonus",
                )
            )
            continue

        if tx_type == "Receive":
            rows.append(
                build_row(
                    tx_type="Reward / Bonus",
                    buy_amount=quantity,
                    buy_currency=asset,
                    fee_amount=Decimal("0"),
                    fee_currency=asset,
                    exchange="Coinbase",
                    comment=raw["Notes"],
                    date=dt,
                    tx_id=f"coinbase-receive-{raw_ref}",
                    match_window_seconds=2,
                    comment_mode="ignore",
                    raw_source=raw_source,
                    raw_ref=raw_ref,
                    notes="Coinbase Receive normalized to Reward / Bonus",
                )
            )
            continue

        if tx_type == "Retail Unstaking Transfer":
            positive_leg = quantity > 0
            rows.append(
                build_row(
                    tx_type="Deposit" if positive_leg else "Withdrawal",
                    buy_amount=quantity if positive_leg else None,
                    buy_currency=asset if positive_leg else "",
                    sell_amount=abs(quantity) if not positive_leg else None,
                    sell_currency=asset if not positive_leg else "",
                    fee_amount=Decimal("0"),
                    fee_currency=asset,
                    exchange="Coinbase",
                    group="Retail Unstaking Transfer",
                    comment="Retail Unstaking Transfer",
                    date=dt,
                    tx_id=f"coinbase-retail-unstaking-{raw_ref}",
                    match_window_seconds=2,
                    comment_mode="ignore",
                    raw_source=raw_source,
                    raw_ref=raw_ref,
                    notes="Retail Unstaking Transfer normalized in CoinTracking schema",
                )
            )
            continue

        if tx_type in {"Pro Deposit", "Pro Withdrawal"}:
            statement_row = find_matching_pro_statement(raw, pro_statement_rows)
            transfer_id = statement_row["transfer id"] if statement_row else ""
            rows.append(
                build_row(
                    tx_type="Withdrawal" if tx_type == "Pro Deposit" else "Deposit",
                    buy_amount=quantity if tx_type == "Pro Withdrawal" else None,
                    buy_currency=asset if tx_type == "Pro Withdrawal" else "",
                    sell_amount=abs(quantity) if tx_type == "Pro Deposit" else None,
                    sell_currency=asset if tx_type == "Pro Deposit" else "",
                    fee_amount=Decimal("0"),
                    fee_currency=asset,
                    exchange="Coinbase",
                    comment="",
                    date=dt,
                    tx_id=transfer_id or f"coinbase-pro-transfer-{raw_ref}",
                    match_window_seconds=90,
                    comment_mode="ignore",
                    tx_id_mode="ignore",
                    raw_source=raw_source,
                    raw_ref=raw_ref if not transfer_id else f"{raw_ref}|{transfer_id}",
                    notes="Retail Coinbase/Coinbase Pro transfer normalized without trusting CoinTracking-generated comments",
                )
            )
            continue

        raise ValueError(f"Unsupported Coinbase retail transaction type: {tx_type}")

    for timestamp, migration_rows in sorted(asset_migrations.items()):
        if len(migration_rows) != 2:
            raise ValueError(f"Expected 2 asset-migration rows at {timestamp}, found {len(migration_rows)}")
        negatives = [row for row in migration_rows if (parse_decimal(row["Quantity Transacted"]) or Decimal("0")) < 0]
        positives = [row for row in migration_rows if (parse_decimal(row["Quantity Transacted"]) or Decimal("0")) > 0]
        if len(negatives) != 1 or len(positives) != 1:
            raise ValueError(f"Asset-migration rows at {timestamp} do not form one positive and one negative leg")
        sold_row = negatives[0]
        bought_row = positives[0]
        dt = parse_coinbase_retail_timestamp(timestamp)
        rows.append(
            build_row(
                tx_type="Swap (non taxable)",
                buy_amount=parse_decimal(bought_row["Quantity Transacted"]),
                buy_currency=bought_row["Asset"],
                sell_amount=abs(parse_decimal(sold_row["Quantity Transacted"]) or Decimal("0")),
                sell_currency=sold_row["Asset"],
                fee_amount=Decimal("0"),
                fee_currency=sold_row["Asset"],
                exchange="Coinbase",
                group="Asset Migration",
                comment="Coinbase Asset Migration",
                date=dt,
                tx_id=f"coinbase-asset-migration-{sold_row['ID']}-{bought_row['ID']}",
                match_window_seconds=2,
                comment_mode="ignore",
                raw_source=retail_source.name,
                raw_ref=f"{sold_row['ID']}|{bought_row['ID']}",
                notes="Paired Coinbase Asset Migration rows normalized into one CoinTracking swap",
            )
        )

    for statement_row in pro_statement_rows:
        dt = parse_coinbase_pro_timestamp(statement_row["time"])
        amount = parse_decimal(statement_row["amount"]) or Decimal("0")
        asset = statement_row["amount/balance unit"]
        row_type = statement_row["type"]
        if row_type in {"deposit", "withdrawal"}:
            rows.append(
                build_row(
                    tx_type="Deposit" if row_type == "deposit" else "Withdrawal",
                    buy_amount=abs(amount) if row_type == "deposit" else None,
                    buy_currency=asset if row_type == "deposit" else "",
                    sell_amount=abs(amount) if row_type == "withdrawal" else None,
                    sell_currency=asset if row_type == "withdrawal" else "",
                    fee_amount=Decimal("0"),
                    fee_currency=asset,
                    exchange="Coinbase Pro",
                    comment="",
                    date=dt,
                    tx_id=statement_row["transfer id"] or f"coinbase-pro-{row_type}-{asset}-{ct_date_text(dt)}",
                    match_window_seconds=90,
                    comment_mode="ignore",
                    tx_id_mode="ignore",
                    raw_source=statement_row["_file"],
                    raw_ref=statement_row["transfer id"] or statement_row["time"],
                    notes="Coinbase Pro statement transfer normalized in CoinTracking schema",
                )
            )

    for fill_row in pro_fill_rows:
        dt = parse_coinbase_pro_timestamp(fill_row["created at"])
        size = parse_decimal(fill_row["size"]) or Decimal("0")
        fee = parse_decimal(fill_row["fee"]) or Decimal("0")
        total = abs(parse_decimal(fill_row["total"]) or Decimal("0"))
        product = fill_row["product"]
        buy_asset, sell_asset = product.split("-", 1)
        side = fill_row["side"].upper()
        if side == "BUY":
            buy_amount = size
            buy_currency = fill_row["size unit"]
            sell_amount = total
            sell_currency = fill_row["price/fee/total unit"]
        else:
            buy_amount = total
            buy_currency = fill_row["price/fee/total unit"]
            sell_amount = size
            sell_currency = fill_row["size unit"]
        rows.append(
            build_row(
                tx_type="Trade",
                buy_amount=buy_amount,
                buy_currency=buy_currency,
                sell_amount=sell_amount,
                sell_currency=sell_currency,
                fee_amount=fee,
                fee_currency=fill_row["price/fee/total unit"],
                exchange="Coinbase Pro",
                comment="",
                date=dt,
                tx_id=f"{fill_row['trade id']}_{product}",
                match_window_seconds=2,
                fee_tolerance=Decimal("0.00000010"),
                comment_mode="ignore",
                tx_id_mode="ignore",
                raw_source=fill_row["_file"],
                raw_ref=fill_row["trade id"],
                notes="Coinbase Pro fills row normalized in CoinTracking schema",
            )
        )

    return sorted(rows, key=lambda row: (row["Date"], row["Exchange"], row["Type"], row["Tx-ID"]))


def coinbase_balance_rows_from_text(text: str, pdf_file: str) -> list[dict[str, str]]:
    normalized = normalize_whitespace(text)
    portfolio_match = COINBASE_PORTFOLIO_AS_OF_PATTERN.search(normalized)
    cash_match = COINBASE_CLOSING_CASH_PATTERN.search(normalized)
    rows: list[dict[str, str]] = []
    if cash_match:
        rows.append(
            {
                "source": "Coinbase",
                "account": "Coinbase",
                "wallet": "Coinbase Cash",
                "balance_kind": "cash_closing_balance",
                "asset": cash_match.group("currency"),
                "quantity": decimal_text(parse_decimal(cash_match.group("balance")) or Decimal("0")),
                "staked_quantity": "",
                "value_amount": "",
                "value_currency": "",
                "price_amount": "",
                "price_currency": "",
                "as_of": parse_datetime_to_utc_naive(
                    cash_match.group("as_of"),
                    ("%Y-%m-%d %H:%M:%S UTC",),
                    source_timezone=timezone.utc,
                ).strftime(COINTRACKING_TIME_FORMAT),
                "pdf_file": pdf_file,
                "notes": "Closing fiat balance from Coinbase statement PDF",
            }
        )
    if portfolio_match:
        as_of = parse_datetime_to_utc_naive(
            portfolio_match.group("as_of"),
            ("%Y-%m-%d %H:%M:%S UTC",),
            source_timezone=timezone.utc,
        ).strftime(COINTRACKING_TIME_FORMAT)
        seen_assets: set[str] = set()
        for pattern in (PORTFOLIO_ROW_PATTERN, PORTFOLIO_ROW_FALLBACK_PATTERN):
            for match in pattern.finditer(normalized):
                asset = match.group("asset")
                if asset in seen_assets:
                    continue
                seen_assets.add(asset)
                staked = match.group("staked")
                rows.append(
                    {
                        "source": "Coinbase",
                        "account": "Coinbase",
                        "wallet": "Coinbase",
                        "balance_kind": "asset_balance",
                        "asset": asset,
                        "quantity": decimal_text(parse_decimal(match.group("quantity")) or Decimal("0")),
                        "staked_quantity": "" if staked == "N/A" else decimal_text(parse_decimal(staked) or Decimal("0")),
                        "value_amount": decimal_text(parse_decimal(match.group("value")) or Decimal("0"), "0.00"),
                        "value_currency": "CAD",
                        "price_amount": decimal_text(parse_decimal(match.group("price")) or Decimal("0")),
                        "price_currency": "CAD",
                        "as_of": as_of,
                        "pdf_file": pdf_file,
                        "notes": "Portfolio summary asset balance from Coinbase statement PDF",
                    }
                )
    return rows
