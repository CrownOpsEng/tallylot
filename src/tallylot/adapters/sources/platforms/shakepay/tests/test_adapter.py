from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.adapters.sources.platforms.shakepay.adapter import _ShakepayAdapter
from tallylot.adapters.sources.platforms.shakepay.statement_evidence import (
    match_statement_document,
)
from tallylot.adapters.sources.platforms.shakepay.translation import translate_row
from tallylot.adapters.support import CsvRowContext
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.application.evidence.statement_extraction import (
    StatementExtractionService,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.ports.evidence import (
    StatementDocumentBalanceRow,
    StatementDocumentParseResult,
)
from tallylot.ports.source_profiles import FileInventoryEntry
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter
from tests.support.services import FakeSourceRegistry, build_source_profile


def test_shakepay_adapter_normalizes_fixture_rows() -> None:
    raw_dir = fixture_raw_dir("shakepay", "cash_crypto_mix")

    profile, adapter = profile_and_adapter("Shakepay", raw_dir)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert str(profile.adapter_id) == "shakepay"
    assert {event.economic_kind for event in facts} == {
        EconomicKind.FIAT_DEPOSIT,
        EconomicKind.CASH_EXPENSE,
        EconomicKind.CASH_WITHDRAWAL,
        EconomicKind.ASSET_WITHDRAWAL,
        EconomicKind.PLATFORM_REWARD,
        EconomicKind.SPOT_TRADE,
    }
    assert {event.projection_hint for event in facts} == {
        ProjectionHint.DEPOSIT,
        ProjectionHint.EXPENSE_NON_TAXABLE,
        ProjectionHint.REWARD_BONUS,
        ProjectionHint.TRADE,
        ProjectionHint.WITHDRAWAL,
    }
    assert {event.accounting_intent_hint for event in facts} == {
        AccountingIntentHint.FUNDING_INFLOW,
        AccountingIntentHint.EXPENSE_RECOGNITION,
        AccountingIntentHint.FUNDING_OUTFLOW,
        AccountingIntentHint.INCOME_RECOGNITION,
        AccountingIntentHint.ASSET_EXCHANGE,
    }
    assert {event.tax_treatment_hint for event in facts} == {
        TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
        TaxTreatmentHint.NON_TAXABLE_EXPENSE,
        TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
        TaxTreatmentHint.ORDINARY_INCOME,
        TaxTreatmentHint.CAPITAL_EXCHANGE,
    }
    trade_event = next(
        event for event in facts if event.projection_hint == ProjectionHint.TRADE
    )
    primary_legs = tuple(leg for leg in trade_event.legs if leg.kind.value == "primary")
    assert primary_legs[0].quantity > 0
    assert primary_legs[1].quantity < 0
    assert any(event.description.lower() == "shakingsats" for event in facts)
    assert result.balance_references == ()
    assert result.issues == ()


def test_shakepay_adapter_ignores_manifest_csv(tmp_path: Path) -> None:
    raw_dir = fixture_raw_dir("shakepay", "cash_crypto_mix")
    for source_path in raw_dir.iterdir():
        target_path = tmp_path / source_path.name
        target_path.write_bytes(source_path.read_bytes())
    (tmp_path / "manifest.csv").write_text(
        "filename,size_bytes\ncash_transactions_summary.csv,1\n",
        encoding="utf-8",
    )

    profile, adapter = profile_and_adapter("Shakepay", tmp_path)
    result = adapter.translate(profile, tmp_path)
    facts = compile_activity_drafts(result.drafts)

    assert len(facts) == 6
    assert result.issues == ()


def test_shakepay_invalid_timestamp_surfaces_issue() -> None:
    profile, _ = profile_and_adapter(
        "Shakepay", fixture_raw_dir("shakepay", "cash_crypto_mix")
    )

    parsed = translate_row(
        profile,
        CsvRowContext(
            path=Path("cash_transactions_summary.csv"),
            row_index=2,
            row={
                "Date": "",
                "Type": "E-Transfer",
                "Description": "fixture",
                "Debit": "",
                "Credit": "10.00",
            },
        ),
    )

    assert parsed is not None
    assert isinstance(parsed, IssueRecord)
    assert parsed.kind == "unsupported_row"
    assert parsed.raw_row_ref == "row:2"


def test_shakepay_statement_matching_rejects_auxiliary_reports() -> None:
    fees_score = match_statement_document(
        Path("shakepay_Fees charged_2025.pdf"),
        """
        Fees & charges report
        For the year ending on December 31, 2025
        This report summarizes the sums we directly received.
        """,
    )
    performance_score = match_statement_document(
        Path("shakepay_Performance report_2025.pdf"),
        """
        Performance report
        For the year ending on December 31, 2025
        Closing market value at year end $643.81
        """,
    )

    assert fees_score == 0
    assert performance_score == 0


def test_shakepay_statement_matching_accepts_monthly_statement_pdf() -> None:
    score = match_statement_document(
        Path("shakepay_2025-12.pdf"),
        """
        Balance summary (as of 2026-01-01 00:00 EST)
        Cash (CAD) 436.54 1.00 436.54 436.54
        Bitcoin (BTC) 0.00172289 119,827.68 206.44 257.47
        Monthly account statement 2025-12-01 to 2025-12-31
        """,
    )

    assert score == 100


def test_shakepay_statement_service_emits_latest_balance_references(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "older.pdf").write_bytes(b"older")
    (raw_dir / "latest.pdf").write_bytes(b"latest")

    older_as_of = datetime(2026, 3, 1, 5, 0, tzinfo=UTC)
    latest_as_of = datetime(2026, 4, 1, 4, 0, tzinfo=UTC)

    def fake_parse_statement_document(
        path: Path, text: str
    ) -> StatementDocumentParseResult:
        del text
        if path.name == "older.pdf":
            return StatementDocumentParseResult(
                pdf_file=path.name,
                recognized=True,
                statement_as_of_at=older_as_of,
                rows=(
                    StatementDocumentBalanceRow(
                        source="Shakepay",
                        account="Shakepay",
                        wallet="Personal",
                        balance_kind="available",
                        asset="CAD",
                        quantity=Decimal("1"),
                        as_of_at=older_as_of,
                        as_of_precision=TemporalPrecision.TIMESTAMP,
                        pdf_file=path.name,
                        raw_row_ref="page:1:Balance summary",
                        notes="older",
                    ),
                ),
            )
        return StatementDocumentParseResult(
            pdf_file=path.name,
            recognized=True,
            statement_as_of_at=latest_as_of,
            rows=(
                StatementDocumentBalanceRow(
                    source="Shakepay",
                    account="Shakepay",
                    wallet="Personal",
                    balance_kind="available",
                    asset="CAD",
                    quantity=Decimal("18.76"),
                    as_of_at=latest_as_of,
                    as_of_precision=TemporalPrecision.TIMESTAMP,
                    pdf_file=path.name,
                    raw_row_ref="page:1:Balance summary",
                    notes="latest",
                ),
                StatementDocumentBalanceRow(
                    source="Shakepay",
                    account="Shakepay",
                    wallet="Personal",
                    balance_kind="available",
                    asset="BTC",
                    quantity=Decimal("0.00186458"),
                    as_of_at=latest_as_of,
                    as_of_precision=TemporalPrecision.TIMESTAMP,
                    pdf_file=path.name,
                    raw_row_ref="page:1:Balance summary",
                    notes="latest",
                ),
            ),
        )

    def fake_extract_pdf_text(path: Path) -> str:
        del path
        return "statement"

    def fake_match_statement_document(path: Path, text: str) -> int:
        del path, text
        return 100

    monkeypatch.setattr(
        "tallylot.application.evidence.statement_extraction.service._extract_pdf_text",
        fake_extract_pdf_text,
    )
    monkeypatch.setattr(
        "tallylot.adapters.sources.platforms.shakepay.adapter._parse_statement_document",
        fake_parse_statement_document,
    )
    monkeypatch.setattr(
        "tallylot.adapters.sources.platforms.shakepay.adapter._match_statement_document",
        fake_match_statement_document,
    )

    result = StatementExtractionService(
        FakeSourceRegistry((_ShakepayAdapter(),))
    ).extract_source_balance_references(
        build_source_profile(
            adapter_id="shakepay",
            raw_dir=str(raw_dir),
            source="Shakepay",
            file_inventory=(
                FileInventoryEntry(
                    relative_path="older.pdf",
                    suffix=".pdf",
                    size_bytes=5,
                    sha256="older",
                    source_path=str(raw_dir / "older.pdf"),
                    capture_uid="capture-1",
                    source="Shakepay",
                    evidence_role="statement_source",
                    originality_class="upstream_original",
                ),
                FileInventoryEntry(
                    relative_path="latest.pdf",
                    suffix=".pdf",
                    size_bytes=6,
                    sha256="latest",
                    source_path=str(raw_dir / "latest.pdf"),
                    capture_uid="capture-1",
                    source="Shakepay",
                    evidence_role="statement_source",
                    originality_class="upstream_original",
                ),
            ),
        ),
        raw_dir,
    )

    assert [reference.instrument_id for reference in result.balance_references] == [
        "symbol:BTC@shakepay",
        "symbol:CAD@shakepay",
    ]
    assert all(
        reference.target_at == latest_as_of
        and reference.observed_at == latest_as_of
        and reference.target_precision is TemporalPrecision.TIMESTAMP
        and reference.observed_precision is TemporalPrecision.TIMESTAMP
        for reference in result.balance_references
    )
