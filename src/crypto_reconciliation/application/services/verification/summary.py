"""Verification comparison summary assembly."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

from .balances import (
    build_balance_map,
    build_exchange_balance_map,
    compare_balance_maps,
    compare_exchange_balance_maps,
    decimal_text,
)
from .paths import required_verification_paths
from .rows import expand_counter_delta, row_counter, subtract_counters


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
