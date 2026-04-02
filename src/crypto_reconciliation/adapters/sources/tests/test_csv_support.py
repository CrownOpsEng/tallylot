from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.sources.csv_support import (
    CsvRowContext,
    collect_row_normalization,
    matching_file_paths,
    read_csv_rows,
)
from crypto_reconciliation.domain.models import IssueRecord, NormalizedTransaction
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId


def test_matching_file_paths_returns_sorted_matches(tmp_path: Path) -> None:
    (tmp_path / "b.csv").write_text("col\n2\n", encoding="utf-8")
    (tmp_path / "a.csv").write_text("col\n1\n", encoding="utf-8")

    assert [path.name for path in matching_file_paths(tmp_path)] == ["a.csv", "b.csv"]


def test_read_csv_rows_uses_utf8_sig_and_preserves_rows(tmp_path: Path) -> None:
    path = tmp_path / "rows.csv"
    path.write_text("\ufeffkind,value\ntrade,1\n", encoding="utf-8")

    assert read_csv_rows(path) == ({"kind": "trade", "value": "1"},)


def test_collect_row_normalization_partitions_transactions_and_issues(tmp_path: Path) -> None:
    path = tmp_path / "rows.csv"
    path.write_text("kind,value\ntransaction,1\nissue,2\nskip,3\n", encoding="utf-8")

    def parse_row(row_context: CsvRowContext) -> NormalizedTransaction | IssueRecord | None:
        kind = row_context.row["kind"]
        if kind == "skip":
            return None
        if kind == "issue":
            return IssueRecord(
                issue_id=f"issue:{row_context.raw_row_ref}",
                source="fixture",
                adapter_id="fixture",
                severity="medium",
                kind="unsupported_row",
                message="fixture issue",
                raw_file=row_context.raw_file,
                raw_row_ref=row_context.raw_row_ref,
            )
        return NormalizedTransaction(
            transaction_id=TransactionId(f"tx:{row_context.raw_row_ref}"),
            source=SourceId("fixture"),
            adapter_id=AdapterId("fixture"),
            account="fixture",
            wallet="fixture",
            timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
            category="trade",
            asset_in=AssetSymbol("BTC"),
            amount_in=Decimal("1"),
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
        )

    transactions, issues = collect_row_normalization(tmp_path, parse_row)

    assert [transaction.raw_row_ref for transaction in transactions] == ["row:2"]
    assert [issue.raw_row_ref for issue in issues] == ["row:3"]
