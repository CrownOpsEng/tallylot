"""CoinTracking baseline export analysis."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from tallylot.domain.value_objects import format_timestamp
from tallylot.ports.artifacts import ArtifactStorePort
from tools.oracles.contracts import BaselineArtifacts

from .baseline_exports import find_required_baseline_exports, match_baseline_exports
from .baseline_metrics import (
    build_asset_snapshot,
    build_cad_flow_summary,
    build_exchange_reconciliation,
    build_source_activity,
    decimal_text,
    latest_trade_timestamp,
    parse_trade_table_row,
)

__all__ = [
    "BaselineExportRows",
    "build_asset_snapshot",
    "build_baseline_artifacts",
    "build_baseline_artifacts_from_rows",
    "build_cad_flow_summary",
    "build_exchange_reconciliation",
    "build_source_activity",
    "decimal_text",
    "find_required_baseline_exports",
    "latest_trade_timestamp",
    "match_baseline_exports",
    "parse_trade_table_row",
]


@dataclass(frozen=True)
class BaselineExportRows:
    trade_rows: list[dict[str, str]]
    current_rows: list[dict[str, str]]
    exchange_rows: list[dict[str, str]]
    validate_rows: list[dict[str, str]]
    missing_rows: list[dict[str, str]]
    duplicate_rows: list[dict[str, str]]


def build_baseline_artifacts(export_dir: Path, artifacts: ArtifactStorePort) -> BaselineArtifacts:
    exports = find_required_baseline_exports(export_dir)
    return build_baseline_artifacts_from_rows(
        BaselineExportRows(
            trade_rows=artifacts.read_rows(exports["Trade Table"]),
            current_rows=artifacts.read_rows(exports["Current Balance"]),
            exchange_rows=artifacts.read_rows(exports["Balance by Exchange"]),
            validate_rows=artifacts.read_rows(exports["Validate Transactions"]),
            missing_rows=artifacts.read_rows(exports["Missing Transactions"]),
            duplicate_rows=artifacts.read_rows(exports["Duplicate Transactions"]),
        )
    )


def build_baseline_artifacts_from_rows(rows: BaselineExportRows) -> BaselineArtifacts:
    latest_timestamp = latest_trade_timestamp(rows.trade_rows)
    asset_snapshot_rows, current_by_ticker, negative_balances = build_asset_snapshot(
        rows.current_rows,
        rows.exchange_rows,
    )
    reconciliation_rows, cad_balance_by_exchange_rows, max_difference, max_ticker = build_exchange_reconciliation(
        current_by_ticker,
        rows.exchange_rows,
    )
    source_activity_rows = build_source_activity(rows.trade_rows, rows.exchange_rows)
    cad_flow_rows, cad_bought_total, cad_sold_total, cad_fee_total = build_cad_flow_summary(rows.trade_rows)
    trade_sources = {row["Exchange"] for row in rows.trade_rows if row.get("Exchange")}
    balance_sources = {row["Exchange"] for row in rows.exchange_rows if row.get("Exchange")}
    return BaselineArtifacts(
        asset_snapshot_rows=asset_snapshot_rows,
        reconciliation_rows=reconciliation_rows,
        negative_balances=negative_balances,
        source_activity_rows=source_activity_rows,
        cad_flow_rows=cad_flow_rows,
        cad_balance_by_exchange_rows=cad_balance_by_exchange_rows,
        summary={
            "latest_transaction_timestamp": format_timestamp(latest_timestamp),
            "trade_count": len(rows.trade_rows),
            "current_balance_rows": len(rows.current_rows),
            "balance_by_exchange_rows": len(rows.exchange_rows),
            "validate_transactions_rows": len(rows.validate_rows),
            "missing_transactions_rows": len(rows.missing_rows),
            "duplicate_transactions_rows": len(rows.duplicate_rows),
            "negative_balance_rows": len(negative_balances),
            "max_asset_difference": decimal_text(max_difference),
            "max_asset_difference_ticker": max_ticker,
            "ending_cad_balance": decimal_text(current_by_ticker.get("CAD", Decimal("0"))),
            "cad_bought_total": decimal_text(cad_bought_total),
            "cad_sold_total": decimal_text(cad_sold_total),
            "cad_fee_total": decimal_text(cad_fee_total),
            "asset_reconciliation_assets": len(reconciliation_rows),
            "trade_table_sources": len(trade_sources),
            "balance_by_exchange_sources": len(balance_sources),
            "source_activity_rows": len(source_activity_rows),
        },
    )
