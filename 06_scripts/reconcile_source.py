#!/usr/bin/env python3

"""Reconcile canonical source events and balances against CoinTracking ledger exports."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from render_cointracking import RENDER_METADATA_HEADERS, render_cointracking_rows
from script_common import (
    decimal_or_zero,
    decimal_text,
    parse_datetime,
    read_cointracking_rows,
    read_csv_rows,
    write_cointracking_rows,
    write_csv_rows,
    write_json,
)


COINTRACKING_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class CandidateScore:
    exact_type: int
    exact_group: int
    exact_comment: int
    exact_tx_id: int
    time_delta_seconds: int
    fee_delta: Decimal


def ct_datetime(value: str) -> datetime:
    return parse_datetime(value, (COINTRACKING_TIME_FORMAT,))


def amount_key(row: dict[str, str], prefix: str) -> tuple[Decimal, str]:
    if prefix == "buy":
        return decimal_or_zero(row["Buy"]), row["Buy Cur."]
    if prefix == "sell":
        return decimal_or_zero(row["Sell"]), row["Sell Cur."]
    if prefix == "fee":
        return decimal_or_zero(row["Fee"]), row["Fee Cur."]
    raise ValueError(prefix)


def split_allowed_types(value: str) -> set[str]:
    return {item for item in value.split("|") if item}


def exchange_matches(expected_exchange: str, actual_exchange: str, allowed_exchanges: set[str]) -> bool:
    return actual_exchange in allowed_exchanges and expected_exchange in allowed_exchanges


def candidate_matches(expected: dict[str, str], actual: dict[str, str], allowed_exchanges: set[str] | None = None) -> bool:
    allowed_exchanges = allowed_exchanges or {expected["Exchange"]}
    if not exchange_matches(expected["Exchange"], actual["Exchange"], allowed_exchanges):
        return False
    if actual["Type"] not in split_allowed_types(expected["render_allowed_types"]):
        return False
    if amount_key(actual, "buy") != amount_key(expected, "buy"):
        return False
    if amount_key(actual, "sell") != amount_key(expected, "sell"):
        return False
    window = int(expected["render_match_window_seconds"] or "0")
    if abs((ct_datetime(actual["Date"]) - ct_datetime(expected["Date"])).total_seconds()) > window:
        return False
    return True


def candidate_score(expected: dict[str, str], actual: dict[str, str]) -> CandidateScore:
    return CandidateScore(
        exact_type=1 if actual["Type"] == expected["Type"] else 0,
        exact_group=1 if actual["Group"] == expected["Group"] else 0,
        exact_comment=1 if actual["Comment"] == expected["Comment"] else 0,
        exact_tx_id=1 if expected["Tx-ID"] and actual["Tx-ID"] == expected["Tx-ID"] else 0,
        time_delta_seconds=int(abs((ct_datetime(actual["Date"]) - ct_datetime(expected["Date"])).total_seconds())),
        fee_delta=abs(decimal_or_zero(actual["Fee"]) - decimal_or_zero(expected["Fee"])),
    )


def compare_expected_to_actual(expected: dict[str, str], actual: dict[str, str]) -> list[str]:
    issues: list[str] = []
    fee_tolerance = decimal_or_zero(expected["render_fee_tolerance"])
    if abs(decimal_or_zero(actual["Fee"]) - decimal_or_zero(expected["Fee"])) > fee_tolerance:
        issues.append("fee_mismatch")
    if expected["Group"] and actual["Group"] != expected["Group"]:
        issues.append("group_mismatch")
    if expected["render_comment_mode"] == "exact" and actual["Comment"] != expected["Comment"]:
        issues.append("comment_mismatch")
    if expected["render_tx_id_mode"] == "exact" and actual["Tx-ID"] != expected["Tx-ID"]:
        issues.append("tx_id_mismatch")
    return issues


def compare_transactions(
    actual_rows: list[dict[str, str]],
    expected_rows: list[dict[str, str]],
    *,
    allowed_exchanges: set[str] | None = None,
) -> dict[str, list[dict[str, str]]]:
    unmatched_actual = set(range(len(actual_rows)))
    matched_rows: list[dict[str, str]] = []
    mismatched_rows: list[dict[str, str]] = []
    missing_rows: list[dict[str, str]] = []
    ambiguous_rows: list[dict[str, str]] = []

    for expected in expected_rows:
        effective_exchanges = allowed_exchanges or {expected["Exchange"]}
        candidates = [
            index
            for index in unmatched_actual
            if candidate_matches(expected, actual_rows[index], effective_exchanges)
        ]
        if not candidates:
            missing_rows.append(expected)
            continue
        ranked = sorted(
            candidates,
            key=lambda index: (
                -candidate_score(expected, actual_rows[index]).exact_type,
                -candidate_score(expected, actual_rows[index]).exact_group,
                -candidate_score(expected, actual_rows[index]).exact_comment,
                -candidate_score(expected, actual_rows[index]).exact_tx_id,
                candidate_score(expected, actual_rows[index]).time_delta_seconds,
                candidate_score(expected, actual_rows[index]).fee_delta,
            ),
        )
        best_index = ranked[0]
        best_score = candidate_score(expected, actual_rows[best_index])
        tied = [index for index in ranked[1:] if candidate_score(expected, actual_rows[index]) == best_score]
        if tied:
            ambiguous_rows.append({**expected, "candidate_tx_ids": "|".join(actual_rows[index]["Tx-ID"] for index in [best_index, *tied])})
            continue
        actual = actual_rows[best_index]
        issues = compare_expected_to_actual(expected, actual)
        combined = {
            **expected,
            "actual_type": actual["Type"],
            "actual_buy": actual["Buy"],
            "actual_buy_currency": actual["Buy Cur."],
            "actual_sell": actual["Sell"],
            "actual_sell_currency": actual["Sell Cur."],
            "actual_fee": actual["Fee"],
            "actual_fee_currency": actual["Fee Cur."],
            "actual_group": actual["Group"],
            "actual_comment": actual["Comment"],
            "actual_date": actual["Date"],
            "actual_tx_id": actual["Tx-ID"],
            "comparison_issues": "|".join(issues),
        }
        if issues:
            mismatched_rows.append(combined)
        else:
            matched_rows.append(combined)
        unmatched_actual.remove(best_index)

    extra_rows = [actual_rows[index] for index in sorted(unmatched_actual)]
    return {
        "matched": matched_rows,
        "mismatched": mismatched_rows,
        "missing": missing_rows,
        "extra": extra_rows,
        "ambiguous": ambiguous_rows,
    }


def compare_balances(
    cointracking_balance_rows: list[dict[str, str]],
    canonical_balance_rows: list[dict[str, str]],
    source: str,
    *,
    allowed_exchanges: set[str] | None = None,
) -> list[dict[str, str]]:
    tolerance = Decimal("0.00000001")
    effective_exchanges = allowed_exchanges or {source}
    actual = {
        row["Currency"]: decimal_or_zero(row["Amount"])
        for row in cointracking_balance_rows
        if row.get("Exchange") in effective_exchanges
    }
    expected = {
        row["asset"]: decimal_or_zero(row["quantity"])
        for row in canonical_balance_rows
        if row.get("source") == source and row.get("balance_kind") in {"asset_balance", "cash_closing_balance"}
    }
    rows = []
    for asset in sorted(set(actual) | set(expected)):
        actual_amount = actual.get(asset, Decimal("0"))
        expected_amount = expected.get(asset, Decimal("0"))
        difference = actual_amount - expected_amount
        rows.append(
            {
                "asset": asset,
                "expected_amount": decimal_text(expected_amount),
                "cointracking_amount": decimal_text(actual_amount),
                "difference": decimal_text(difference),
                "status": "match" if abs(difference) <= tolerance else "delta",
            }
        )
    return rows


def reconcile_source(
    source: str,
    cointracking_ledger: Path,
    canonical_events: Path,
    *,
    out_dir: Path,
    cointracking_balance_by_exchange: Path | None = None,
    canonical_balances: Path | None = None,
    exchange_aliases: Sequence[str] | None = None,
) -> dict[str, object]:
    all_expected_events = read_csv_rows(canonical_events)
    expected_rows, _ = render_cointracking_rows(all_expected_events)
    exchange_filters = {row["Exchange"] for row in expected_rows}
    exchange_filters.update(alias for alias in (exchange_aliases or []) if alias)
    actual_rows = [row for row in read_cointracking_rows(cointracking_ledger) if row["Exchange"] in exchange_filters]
    transaction_results = compare_transactions(actual_rows, expected_rows, allowed_exchanges=exchange_filters)

    write_cointracking_rows(
        out_dir / "matched_rows.csv",
        transaction_results["matched"],
        extra_headers=(
            "actual_type",
            "actual_buy",
            "actual_buy_currency",
            "actual_sell",
            "actual_sell_currency",
            "actual_fee",
            "actual_fee_currency",
            "actual_group",
            "actual_comment",
            "actual_date",
            "actual_tx_id",
            "comparison_issues",
            *RENDER_METADATA_HEADERS,
        ),
    )
    write_cointracking_rows(out_dir / "missing_rows.csv", transaction_results["missing"], extra_headers=RENDER_METADATA_HEADERS)
    write_cointracking_rows(out_dir / "extra_rows.csv", transaction_results["extra"])
    write_cointracking_rows(
        out_dir / "mismatched_rows.csv",
        transaction_results["mismatched"],
        extra_headers=(
            "actual_type",
            "actual_buy",
            "actual_buy_currency",
            "actual_sell",
            "actual_sell_currency",
            "actual_fee",
            "actual_fee_currency",
            "actual_group",
            "actual_comment",
            "actual_date",
            "actual_tx_id",
            "comparison_issues",
            *RENDER_METADATA_HEADERS,
        ),
    )
    write_cointracking_rows(out_dir / "ambiguous_rows.csv", transaction_results["ambiguous"], extra_headers=("candidate_tx_ids", *RENDER_METADATA_HEADERS))

    balance_rows: list[dict[str, str]] = []
    if cointracking_balance_by_exchange is not None and canonical_balances is not None:
        balance_rows = compare_balances(
            read_csv_rows(cointracking_balance_by_exchange),
            read_csv_rows(canonical_balances),
            source,
            allowed_exchanges=exchange_filters,
        )
        write_csv_rows(out_dir / "balance_deltas.csv", ["asset", "expected_amount", "cointracking_amount", "difference", "status"], balance_rows)

    summary = {
        "source": source,
        "ledger_rows": len(actual_rows),
        "expected_rows": len(expected_rows),
        "matched_rows": len(transaction_results["matched"]),
        "mismatched_rows": len(transaction_results["mismatched"]),
        "missing_rows": len(transaction_results["missing"]),
        "extra_rows": len(transaction_results["extra"]),
        "ambiguous_rows": len(transaction_results["ambiguous"]),
        "mismatch_issue_counts": dict(
            Counter(
                issue
                for row in transaction_results["mismatched"]
                for issue in row["comparison_issues"].split("|")
                if issue
            )
        ),
        "balance_delta_rows": len([row for row in balance_rows if row["status"] == "delta"]),
        "status": "passed"
        if not any(
            (
                transaction_results["mismatched"],
                transaction_results["missing"],
                transaction_results["extra"],
                transaction_results["ambiguous"],
                [row for row in balance_rows if row["status"] == "delta"],
            )
        )
        else "failed",
    }
    write_json(out_dir / "summary.json", summary)
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--cointracking-ledger", required=True, type=Path)
    parser.add_argument("--canonical-events", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--cointracking-balance-by-exchange", type=Path)
    parser.add_argument("--canonical-balances", type=Path)
    parser.add_argument("--exchange-alias", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = reconcile_source(
        args.source,
        args.cointracking_ledger,
        args.canonical_events,
        out_dir=args.out_dir,
        cointracking_balance_by_exchange=args.cointracking_balance_by_exchange,
        canonical_balances=args.canonical_balances,
        exchange_aliases=args.exchange_alias,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
