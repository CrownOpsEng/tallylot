"""Verification comparison summary assembly."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

REQUIRED_FILES = {
    "validate_transactions": "Validate Transactions.csv",
    "missing_transactions": "Missing Transactions.csv",
    "duplicate_transactions": "Duplicate Transactions.csv",
    "current_balance": "Current Balance.csv",
    "balance_by_exchange": "Balance by Exchange.csv",
}


def summarize_verification_exports(
    previous_dir: Path,
    current_dir: Path,
    artifacts: ArtifactStorePort,
) -> dict[str, JsonValue]:
    previous = required_verification_paths(previous_dir)
    current = required_verification_paths(current_dir)

    previous_validate = artifacts.read_rows(previous["validate_transactions"])
    current_validate = artifacts.read_rows(current["validate_transactions"])
    previous_missing = artifacts.read_rows(previous["missing_transactions"])
    current_missing = artifacts.read_rows(current["missing_transactions"])
    current_duplicates = artifacts.read_rows(current["duplicate_transactions"])
    previous_current_balance = artifacts.read_rows(previous["current_balance"])
    current_current_balance = artifacts.read_rows(current["current_balance"])
    previous_exchange_balance = artifacts.read_rows(previous["balance_by_exchange"])
    current_exchange_balance = artifacts.read_rows(current["balance_by_exchange"])

    new_validate_rows = expand_counter_delta(
        subtract_counters(row_counter(current_validate), row_counter(previous_validate))
    )
    resolved_validate_rows = expand_counter_delta(
        subtract_counters(row_counter(previous_validate), row_counter(current_validate))
    )
    new_missing_rows = expand_counter_delta(
        subtract_counters(row_counter(current_missing), row_counter(previous_missing))
    )
    resolved_missing_rows = expand_counter_delta(
        subtract_counters(row_counter(previous_missing), row_counter(current_missing))
    )

    current_balance_deltas = compare_balance_maps(
        build_balance_map(previous_current_balance),
        build_balance_map(current_current_balance),
    )
    exchange_balance_deltas = compare_exchange_balance_maps(
        build_exchange_balance_map(previous_exchange_balance),
        build_exchange_balance_map(current_exchange_balance),
    )
    current_negative_balances = [
        {
            "ticker": row["Ticker"],
            "amount": decimal_text(Decimal(row["Amount"])),
            "value_cad": row.get("Value in CAD", ""),
        }
        for row in current_current_balance
        if Decimal(row["Amount"]) < Decimal("0")
    ]

    gate_flags = {
        "has_duplicate_rows": bool(current_duplicates),
        "has_new_validate_rows": bool(new_validate_rows),
        "has_new_missing_rows": bool(new_missing_rows),
        "has_balance_changes": bool(current_balance_deltas),
        "has_exchange_balance_changes": bool(exchange_balance_deltas),
    }
    gate_suggestion = (
        "hold"
        if gate_flags["has_duplicate_rows"] or gate_flags["has_new_validate_rows"] or gate_flags["has_new_missing_rows"]
        else "review_balance_changes"
    )
    changed_reports = sum(
        (
            bool(new_validate_rows or resolved_validate_rows),
            bool(new_missing_rows or resolved_missing_rows),
            bool(current_duplicates),
            bool(current_balance_deltas),
            bool(exchange_balance_deltas),
        )
    )

    return {
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_dir": str(previous_dir.resolve()),
        "current_dir": str(current_dir.resolve()),
        "reference_validate_rows": len(previous_validate),
        "current_validate_rows": len(current_validate),
        "new_validate_rows": len(new_validate_rows),
        "resolved_validate_rows": len(resolved_validate_rows),
        "reference_missing_rows": len(previous_missing),
        "current_missing_rows": len(current_missing),
        "new_missing_rows": len(new_missing_rows),
        "resolved_missing_rows": len(resolved_missing_rows),
        "current_duplicate_rows": len(current_duplicates),
        "current_balance_delta_rows": len(current_balance_deltas),
        "exchange_balance_delta_rows": len(exchange_balance_deltas),
        "current_negative_balance_rows": len(current_negative_balances),
        "changed_reports": changed_reports,
        "gate_flags": cast(JsonValue, gate_flags),
        "gate_suggestion": gate_suggestion,
        "current_negative_balances": cast(JsonValue, current_negative_balances),
        "new_validate_issue_rows": cast(JsonValue, new_validate_rows),
        "resolved_validate_issue_rows": cast(JsonValue, resolved_validate_rows),
        "new_missing_transaction_rows": cast(JsonValue, new_missing_rows),
        "resolved_missing_transaction_rows": cast(JsonValue, resolved_missing_rows),
        "current_balance_deltas": cast(JsonValue, current_balance_deltas),
        "exchange_balance_deltas": cast(JsonValue, exchange_balance_deltas),
        "current_duplicate_transaction_rows": cast(JsonValue, current_duplicates),
    }


def required_verification_paths(directory: Path) -> dict[str, Path]:
    if not directory.exists():
        raise FileNotFoundError(f"verification directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"verification path is not a directory: {directory}")
    resolved: dict[str, Path] = {}
    for key, filename in REQUIRED_FILES.items():
        path = directory / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing required export {filename!r} in {directory}")
        if not path.is_file():
            raise FileNotFoundError(f"Required export is not a file: {path}")
        resolved[key] = path
    return resolved


def row_counter(rows: list[dict[str, str]]) -> Counter[tuple[tuple[str, str], ...]]:
    return Counter(tuple(sorted((key, value or "") for key, value in row.items())) for row in rows)


def expand_counter_delta(counter: Counter[tuple[tuple[str, str], ...]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for signature, count in sorted(counter.items()):
        row = dict(signature)
        for _ in range(count):
            rows.append(row)
    return rows


def subtract_counters(
    current: Counter[tuple[tuple[str, str], ...]],
    previous: Counter[tuple[tuple[str, str], ...]],
) -> Counter[tuple[tuple[str, str], ...]]:
    delta = current.copy()
    delta.subtract(previous)
    return Counter({key: count for key, count in delta.items() if count > 0})


def build_balance_map(rows: list[dict[str, str]]) -> dict[str, Decimal]:
    amounts: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in rows:
        amounts[row["Ticker"]] += Decimal(row["Amount"])
    return dict(amounts)


def build_exchange_balance_map(rows: list[dict[str, str]]) -> dict[tuple[str, str], Decimal]:
    amounts: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in rows:
        amounts[(row["Exchange"], row["Currency"])] += Decimal(row["Amount"])
    return dict(amounts)


def compare_balance_maps(
    previous: dict[str, Decimal],
    current: dict[str, Decimal],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for ticker in sorted(set(previous) | set(current)):
        previous_amount = previous.get(ticker, Decimal("0"))
        current_amount = current.get(ticker, Decimal("0"))
        difference = current_amount - previous_amount
        if difference == Decimal("0"):
            continue
        rows.append(
            {
                "ticker": ticker,
                "reference_amount": decimal_text(previous_amount),
                "current_amount": decimal_text(current_amount),
                "difference": decimal_text(difference),
            }
        )
    return rows


def compare_exchange_balance_maps(
    previous: dict[tuple[str, str], Decimal],
    current: dict[tuple[str, str], Decimal],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for exchange, currency in sorted(set(previous) | set(current)):
        previous_amount = previous.get((exchange, currency), Decimal("0"))
        current_amount = current.get((exchange, currency), Decimal("0"))
        difference = current_amount - previous_amount
        if difference == Decimal("0"):
            continue
        rows.append(
            {
                "exchange": exchange,
                "currency": currency,
                "reference_amount": decimal_text(previous_amount),
                "current_amount": decimal_text(current_amount),
                "difference": decimal_text(difference),
            }
        )
    return rows


def decimal_text(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.00000000")), "f")
