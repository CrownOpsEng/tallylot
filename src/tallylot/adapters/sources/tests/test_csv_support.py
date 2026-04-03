from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    EconomicActivityDraft,
    classification,
    economic_leg,
)
from tallylot.adapters.support.rows import (
    CsvRowContext,
    collect_csv_row_results,
    matching_file_paths,
    read_csv_rows,
    skip_files_outside_profile_families,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import AccountingIntentHint, EconomicKind, LegKind, ProjectionHint, TaxTreatmentHint
from tallylot.domain.types import AdapterId, LocationId, SourceId
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile


def test_matching_file_paths_returns_sorted_matches(tmp_path: Path) -> None:
    (tmp_path / "b.csv").write_text("col\n2\n", encoding="utf-8")
    (tmp_path / "a.csv").write_text("col\n1\n", encoding="utf-8")

    assert [path.name for path in matching_file_paths(tmp_path)] == ["a.csv", "b.csv"]


def test_read_csv_rows_uses_utf8_sig_and_preserves_rows(tmp_path: Path) -> None:
    path = tmp_path / "rows.csv"
    path.write_text("\ufeffkind,value\ntrade,1\n", encoding="utf-8")

    assert read_csv_rows(path) == ({"kind": "trade", "value": "1"},)


def test_collect_csv_row_results_partitions_drafts_and_issues(tmp_path: Path) -> None:
    path = tmp_path / "rows.csv"
    path.write_text("kind,value\ntransaction,1\nissue,2\nskip,3\n", encoding="utf-8")

    def parse_row(row_context: CsvRowContext) -> EconomicActivityDraft | IssueRecord | None:
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
        return EconomicActivityDraft(
            activity_id=f"tx:{row_context.raw_row_ref}",
            source="fixture",
            adapter_id="fixture",
            location_id=LocationId("fixture:fixture"),
            timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
            classification=classification(
                economic_kind=EconomicKind.SPOT_TRADE,
                projection_hint=ProjectionHint.TRADE,
                accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
            ),
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            legs=(economic_leg(leg_id="primary_in", kind=LegKind.PRIMARY, instrument="BTC", quantity=Decimal("1")),),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        )

    drafts, issues = collect_csv_row_results(tmp_path, parse_row)

    assert [draft.raw_row_ref for draft in drafts] == ["row:2"]
    assert [issue.raw_row_ref for issue in issues] == ["row:3"]


def test_skip_files_outside_profile_families_excludes_manifest_rows(tmp_path: Path) -> None:
    transactions_path = tmp_path / "transactions.csv"
    transactions_path.write_text("kind,value\ntransaction,1\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.csv"
    manifest_path.write_text("filename,size_bytes\ntransactions.csv,27\n", encoding="utf-8")
    profile = SourceProfile(
        source=SourceId("fixture"),
        raw_dir=str(tmp_path),
        adapter_id=AdapterId("fixture"),
        manifest_fingerprint="fixture",
        supported=True,
        file_inventory=(
            FileInventoryEntry(
                relative_path="transactions.csv",
                suffix=".csv",
                size_bytes=transactions_path.stat().st_size,
                sha256="transactions",
                family="fixture:transactions",
            ),
            FileInventoryEntry(
                relative_path="manifest.csv",
                suffix=".csv",
                size_bytes=manifest_path.stat().st_size,
                sha256="manifest",
            ),
        ),
    )

    seen_files: list[str] = []

    def parse_row(row_context: CsvRowContext) -> None:
        seen_files.append(row_context.raw_file)

    collect_csv_row_results(
        tmp_path,
        parse_row,
        skip_file=skip_files_outside_profile_families(
            tmp_path,
            profile,
            family_ids=("transactions",),
        ),
    )

    assert seen_files == ["transactions.csv"]
