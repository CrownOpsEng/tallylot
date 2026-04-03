"""CoinTracking-specific comparison helpers."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from tallylot.domain.value_objects import parse_timestamp


def compare_transactions(
    actual_rows: list[dict[str, str]],
    expected_rows: list[dict[str, str]],
    *,
    allowed_exchanges: set[str] | None = None,
) -> dict[str, list[dict[str, str]]]:
    remaining_actual = list(actual_rows)
    matched: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    for expected in expected_rows:
        match_index = next(
            (
                index
                for index, actual in enumerate(remaining_actual)
                if _transactions_match(actual, expected, allowed_exchanges=allowed_exchanges)
            ),
            None,
        )
        if match_index is None:
            missing.append(expected)
            continue
        matched.append(expected)
        remaining_actual.pop(match_index)
    return {
        "matched": matched,
        "missing": missing,
        "extra": remaining_actual,
    }


def compare_balances(
    actual_rows: list[dict[str, str]],
    expected_rows: list[dict[str, str]],
    source: str,
) -> list[dict[str, str]]:
    actual_by_asset: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    expected_by_asset: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in actual_rows:
        if (row.get("Exchange") or "").strip() != source:
            continue
        actual_by_asset[(row.get("Currency") or "").strip()] += _decimal_or_zero(row.get("Amount", ""))
    for row in expected_rows:
        if (row.get("source") or "").strip() != source:
            continue
        if (row.get("balance_kind") or "").strip() != "asset_balance":
            continue
        expected_by_asset[(row.get("asset") or "").strip()] += _decimal_or_zero(row.get("quantity", ""))
    rows: list[dict[str, str]] = []
    for asset in sorted(set(actual_by_asset) | set(expected_by_asset)):
        actual_amount = actual_by_asset.get(asset, Decimal("0"))
        expected_amount = expected_by_asset.get(asset, Decimal("0"))
        difference = abs(actual_amount - expected_amount)
        rows.append(
            {
                "asset": asset,
                "expected_amount": _decimal_text(expected_amount),
                "actual_amount": _decimal_text(actual_amount),
                "difference": _decimal_text(difference),
                "status": "matched" if difference == Decimal("0") else "delta",
            }
        )
    return rows


def _transactions_match(
    actual: dict[str, str],
    expected: dict[str, str],
    *,
    allowed_exchanges: set[str] | None,
) -> bool:
    return all(
        (
            _type_matches(actual, expected),
            _exchange_matches(actual, expected, allowed_exchanges),
            _core_transaction_fields_match(actual, expected),
            _comment_matches(actual, expected),
            _tx_id_matches(actual, expected),
            _timestamp_matches(actual, expected),
            _fee_matches(actual, expected),
        )
    )


def _type_matches(actual: dict[str, str], expected: dict[str, str]) -> bool:
    expected_types = _allowed_types(expected)
    actual_type = (actual.get("Type") or "").strip()
    return not expected_types or actual_type in expected_types


def _core_transaction_fields_match(actual: dict[str, str], expected: dict[str, str]) -> bool:
    return all(
        (actual.get(actual_key) or "").strip() == (expected.get(expected_key) or "").strip()
        for actual_key, expected_key in (
            ("Buy", "Buy"),
            ("Buy Cur.", "Buy Cur."),
            ("Sell", "Sell"),
            ("Sell Cur.", "Sell Cur."),
            ("Group", "Group"),
        )
    )


def _comment_matches(actual: dict[str, str], expected: dict[str, str]) -> bool:
    if expected.get("render_comment_mode") != "exact":
        return True
    return (actual.get("Comment") or "").strip() == (expected.get("Comment") or "").strip()


def _allowed_types(expected: dict[str, str]) -> set[str]:
    raw_types = (expected.get("render_allowed_types") or expected.get("Type") or "").strip()
    if not raw_types:
        return set()
    return {part.strip() for part in raw_types.split(",") if part.strip()}


def _exchange_matches(
    actual: dict[str, str],
    expected: dict[str, str],
    allowed_exchanges: set[str] | None,
) -> bool:
    actual_exchange = (actual.get("Exchange") or "").strip()
    expected_exchange = (expected.get("Exchange") or "").strip()
    if (
        allowed_exchanges is not None
        and actual_exchange in allowed_exchanges
        and expected_exchange in allowed_exchanges
    ):
        return True
    return actual_exchange == expected_exchange


def _tx_id_matches(actual: dict[str, str], expected: dict[str, str]) -> bool:
    if (expected.get("render_tx_id_mode") or "").strip() == "ignore":
        return True
    return (actual.get("Tx-ID") or "").strip() == (expected.get("Tx-ID") or "").strip()


def _timestamp_matches(actual: dict[str, str], expected: dict[str, str]) -> bool:
    actual_timestamp = _parse_maybe_timestamp(actual.get("Date", ""))
    expected_timestamp = _parse_maybe_timestamp(expected.get("Date", ""))
    if actual_timestamp is None or expected_timestamp is None:
        return actual_timestamp == expected_timestamp
    tolerance_seconds = int((expected.get("render_match_window_seconds") or "0").strip() or "0")
    return abs((actual_timestamp - expected_timestamp).total_seconds()) <= tolerance_seconds


def _fee_matches(actual: dict[str, str], expected: dict[str, str]) -> bool:
    if (actual.get("Fee Cur.") or "").strip() != (expected.get("Fee Cur.") or "").strip():
        return False
    actual_fee = _decimal_or_zero(actual.get("Fee", ""))
    expected_fee = _decimal_or_zero(expected.get("Fee", ""))
    tolerance = _decimal_or_zero(expected.get("render_fee_tolerance", "0"))
    return abs(actual_fee - expected_fee) <= tolerance


def _parse_maybe_timestamp(value: str) -> datetime | None:
    stripped = value.strip()
    if not stripped:
        return None
    return parse_timestamp(stripped)


def _decimal_or_zero(value: str) -> Decimal:
    stripped = value.strip()
    return Decimal("0") if not stripped else Decimal(stripped)


def _decimal_text(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.00000000")), "f")
