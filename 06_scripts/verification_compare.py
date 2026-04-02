#!/usr/bin/env python3

"""Compare two verification export folders and summarize the drift."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from script_common import decimal_text, find_required_csv_exports, read_csv_rows, write_csv_rows, write_json


REQUIRED_FILES = {
    "validate_transactions": "Validate Transactions",
    "missing_transactions": "Missing Transactions",
    "duplicate_transactions": "Duplicate Transactions",
    "current_balance": "Current Balance",
    "balance_by_exchange": "Balance by Exchange",
}

def find_required_files(export_dir: Path) -> dict[str, Path]:
    return find_required_csv_exports(export_dir, REQUIRED_FILES, "Verification directory")


def row_counter(rows: list[dict[str, str]]) -> Counter[tuple[tuple[str, str], ...]]:
    return Counter(tuple(sorted((key, value or "") for key, value in row.items())) for row in rows)


def expand_counter_delta(
    counter: Counter[tuple[tuple[str, str], ...]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for signature, count in sorted(counter.items()):
        row = dict(signature)
        for _ in range(count):
            rows.append(row)
    return rows


def subtract_counters(
    current: Counter[tuple[tuple[str, str], ...]],
    reference: Counter[tuple[tuple[str, str], ...]],
) -> Counter[tuple[tuple[str, str], ...]]:
    delta = current.copy()
    delta.subtract(reference)
    return Counter({key: count for key, count in delta.items() if count > 0})


def build_balance_map(rows: list[dict[str, str]]) -> dict[str, Decimal]:
    amounts: dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        ticker = row["Ticker"]
        amounts[ticker] += Decimal(row["Amount"])
    return dict(amounts)


def build_exchange_balance_map(rows: list[dict[str, str]]) -> dict[tuple[str, str], Decimal]:
    amounts: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for row in rows:
        key = (row["Exchange"], row["Currency"])
        amounts[key] += Decimal(row["Amount"])
    return dict(amounts)


def compare_balance_maps(
    reference: dict[str, Decimal],
    current: dict[str, Decimal],
) -> list[dict[str, str]]:
    rows = []
    keys = sorted(set(reference) | set(current))
    for key in keys:
        reference_amount = reference.get(key, Decimal("0"))
        current_amount = current.get(key, Decimal("0"))
        difference = current_amount - reference_amount
        if difference == 0:
            continue
        rows.append(
            {
                "ticker": key,
                "reference_amount": decimal_text(reference_amount),
                "current_amount": decimal_text(current_amount),
                "difference": decimal_text(difference),
            }
        )
    return rows


def compare_exchange_balance_maps(
    reference: dict[tuple[str, str], Decimal],
    current: dict[tuple[str, str], Decimal],
) -> list[dict[str, str]]:
    rows = []
    keys = sorted(set(reference) | set(current))
    for exchange, currency in keys:
        reference_amount = reference.get((exchange, currency), Decimal("0"))
        current_amount = current.get((exchange, currency), Decimal("0"))
        difference = current_amount - reference_amount
        if difference == 0:
            continue
        rows.append(
            {
                "exchange": exchange,
                "currency": currency,
                "reference_amount": decimal_text(reference_amount),
                "current_amount": decimal_text(current_amount),
                "difference": decimal_text(difference),
            }
        )
    return rows


def summarize_verification(reference_dir: Path, current_dir: Path) -> dict[str, object]:
    reference_files = find_required_files(reference_dir)
    current_files = find_required_files(current_dir)

    reference_validate = read_csv_rows(reference_files["validate_transactions"])
    current_validate = read_csv_rows(current_files["validate_transactions"])
    reference_missing = read_csv_rows(reference_files["missing_transactions"])
    current_missing = read_csv_rows(current_files["missing_transactions"])
    current_duplicates = read_csv_rows(current_files["duplicate_transactions"])
    reference_current_balance = read_csv_rows(reference_files["current_balance"])
    current_current_balance = read_csv_rows(current_files["current_balance"])
    reference_exchange_balance = read_csv_rows(reference_files["balance_by_exchange"])
    current_exchange_balance = read_csv_rows(current_files["balance_by_exchange"])

    new_validate_rows = expand_counter_delta(
        subtract_counters(row_counter(current_validate), row_counter(reference_validate))
    )
    resolved_validate_rows = expand_counter_delta(
        subtract_counters(row_counter(reference_validate), row_counter(current_validate))
    )
    new_missing_rows = expand_counter_delta(
        subtract_counters(row_counter(current_missing), row_counter(reference_missing))
    )
    resolved_missing_rows = expand_counter_delta(
        subtract_counters(row_counter(reference_missing), row_counter(current_missing))
    )

    current_balance_deltas = compare_balance_maps(
        build_balance_map(reference_current_balance),
        build_balance_map(current_current_balance),
    )
    exchange_balance_deltas = compare_exchange_balance_maps(
        build_exchange_balance_map(reference_exchange_balance),
        build_exchange_balance_map(current_exchange_balance),
    )

    current_negative_balances = [
        {
            "ticker": row["Ticker"],
            "amount": decimal_text(Decimal(row["Amount"])),
            "value_cad": row.get("Value in CAD", ""),
        }
        for row in current_current_balance
        if Decimal(row["Amount"]) < 0
    ]

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "reference_dir": str(reference_dir.resolve()),
        "current_dir": str(current_dir.resolve()),
        "reference_validate_rows": len(reference_validate),
        "current_validate_rows": len(current_validate),
        "new_validate_rows": len(new_validate_rows),
        "resolved_validate_rows": len(resolved_validate_rows),
        "reference_missing_rows": len(reference_missing),
        "current_missing_rows": len(current_missing),
        "new_missing_rows": len(new_missing_rows),
        "resolved_missing_rows": len(resolved_missing_rows),
        "current_duplicate_rows": len(current_duplicates),
        "current_balance_delta_rows": len(current_balance_deltas),
        "exchange_balance_delta_rows": len(exchange_balance_deltas),
        "current_negative_balance_rows": len(current_negative_balances),
        "gate_flags": {
            "has_duplicate_rows": len(current_duplicates) > 0,
            "has_new_validate_rows": len(new_validate_rows) > 0,
            "has_new_missing_rows": len(new_missing_rows) > 0,
            "has_balance_changes": len(current_balance_deltas) > 0,
            "has_exchange_balance_changes": len(exchange_balance_deltas) > 0,
        },
        "gate_suggestion": (
            "hold"
            if len(current_duplicates) > 0 or len(new_validate_rows) > 0 or len(new_missing_rows) > 0
            else "review_balance_changes"
        ),
        "current_negative_balances": current_negative_balances,
        "new_validate_issue_rows": new_validate_rows,
        "resolved_validate_issue_rows": resolved_validate_rows,
        "new_missing_transaction_rows": new_missing_rows,
        "resolved_missing_transaction_rows": resolved_missing_rows,
        "current_balance_deltas": current_balance_deltas,
        "exchange_balance_deltas": exchange_balance_deltas,
        "current_duplicate_transaction_rows": current_duplicates,
    }
    return summary


def write_verification_artifacts(out_dir: Path, summary: dict[str, object]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "verification_summary.json", summary)

    write_csv_rows(
        out_dir / "new_validate_issue_rows.csv",
        sorted({key for row in summary["new_validate_issue_rows"] for key in row}) or ["Issue"],
        summary["new_validate_issue_rows"],
    )
    write_csv_rows(
        out_dir / "resolved_validate_issue_rows.csv",
        sorted({key for row in summary["resolved_validate_issue_rows"] for key in row}) or ["Issue"],
        summary["resolved_validate_issue_rows"],
    )
    write_csv_rows(
        out_dir / "new_missing_transaction_rows.csv",
        sorted({key for row in summary["new_missing_transaction_rows"] for key in row}) or ["Type"],
        summary["new_missing_transaction_rows"],
    )
    write_csv_rows(
        out_dir / "resolved_missing_transaction_rows.csv",
        sorted({key for row in summary["resolved_missing_transaction_rows"] for key in row}) or ["Type"],
        summary["resolved_missing_transaction_rows"],
    )
    write_csv_rows(
        out_dir / "current_balance_deltas.csv",
        ["ticker", "reference_amount", "current_amount", "difference"],
        summary["current_balance_deltas"],
    )
    write_csv_rows(
        out_dir / "exchange_balance_deltas.csv",
        ["exchange", "currency", "reference_amount", "current_amount", "difference"],
        summary["exchange_balance_deltas"],
    )
    write_csv_rows(
        out_dir / "current_duplicate_transaction_rows.csv",
        sorted({key for row in summary["current_duplicate_transaction_rows"] for key in row}) or [""],
        summary["current_duplicate_transaction_rows"],
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", required=True, type=Path)
    parser.add_argument("--current-dir", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = summarize_verification(args.reference_dir, args.current_dir)
    if args.out_dir is not None:
        write_verification_artifacts(args.out_dir.resolve(), summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
