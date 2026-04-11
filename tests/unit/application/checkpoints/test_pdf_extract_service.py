from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import override

import pytest
from reportlab.pdfgen import canvas

from tallylot.application.checkpoints import (
    ExtractPdfBalancesUseCase,
    PdfBalanceExtractRequest,
)
from tallylot.application.evidence.statement_extraction import (
    StatementExtractionService,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.issues import IssueRecord
from tallylot.domain.instruments import InstrumentIdentityClaim
from tallylot.domain.types import AdapterId, JsonValue, SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.adapter_contracts import AdapterManifest
from tallylot.domain.temporal import TemporalPrecision
from tallylot.ports.evidence import (
    LocationInventoryRecord,
    StatementDocumentBalanceRow,
    StatementDocumentParseResult,
)
from tallylot.ports.intake_routing import (
    IntakeFileFacts,
    IntakeRoute,
    IntakeRoutingRequest,
)
from tallylot.ports.source_adapters import SourceAdapter
from tallylot.ports.source_profiles import (
    FileFamilyClaim,
    FileInventoryEntry,
    SourceProfile,
)
from tallylot.ports.source_translation import SourceTranslationBatch


class StubPdfAdapter:
    def __init__(
        self,
        adapter_id: str,
        match_score: int,
        rows: tuple[StatementDocumentBalanceRow, ...],
        recognized: bool = True,
    ) -> None:
        self.manifest = AdapterManifest(
            adapter_id=AdapterId(adapter_id),
            display_name=adapter_id.title(),
            version="1.0.0",
            capabilities=frozenset(),
        )
        self._match_score = match_score
        self._rows = rows
        self._recognized = recognized
        self.statement_as_of_at: datetime | None = None
        self.document_effective_at: datetime | None = None
        self.parse_calls = 0

    def match(
        self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]
    ) -> int:
        del source, raw_dir, inventory
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        del relative_path, facts
        return 0

    def classify_profile_families(
        self,
        source: str,
        raw_dir: Path,
        inventory: tuple[FileInventoryEntry, ...],
    ) -> tuple[FileFamilyClaim, ...]:
        del source, raw_dir, inventory
        return ()

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        del request
        route: IntakeRoute | None = None
        return route

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        del profile
        return {}, ()

    def extract_location_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def match_statement_document(self, pdf_path: Path, text: str) -> int:
        del pdf_path, text
        return self._match_score

    def parse_statement_document(
        self, pdf_path: Path, text: str
    ) -> StatementDocumentParseResult:
        del text
        self.parse_calls += 1
        return StatementDocumentParseResult(
            pdf_file=pdf_path.name,
            recognized=self._recognized,
            statement_as_of_at=self.statement_as_of_at,
            rows=self._rows,
            document_effective_at=self.document_effective_at,
        )

    def resolve_statement_instrument_claims(
        self, row: StatementDocumentBalanceRow
    ) -> tuple[InstrumentIdentityClaim, ...]:
        del row
        return ()

    def translate(
        self, profile: SourceProfile, raw_dir: Path
    ) -> SourceTranslationBatch:
        del profile, raw_dir
        return SourceTranslationBatch(
            drafts=(),
            balance_evidence=(),
            issues=(),
            reviews=(),
            location_inventory=(),
        )


class StubRegistry:
    def __init__(self, adapters: list[SourceAdapter]) -> None:
        self._adapters = tuple(adapters)

    @property
    def source_adapters(self) -> tuple[SourceAdapter, ...]:
        return self._adapters

    def source_adapter(self, adapter_id: str) -> SourceAdapter:
        for adapter in self._adapters:
            if str(adapter.manifest.adapter_id) == adapter_id:
                return adapter
        raise KeyError(adapter_id)


def _make_pdf(path: Path, *lines: str) -> None:
    pdf = canvas.Canvas(str(path))
    y = 750
    for line in lines:
        pdf.drawString(72, y, line)
        y -= 15
    pdf.save()


def test_pdf_balance_extraction_service_uses_requested_supported_adapter(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "statement.pdf"
    output_path = tmp_path / "balances.csv"
    _make_pdf(pdf_path, "Account statement")
    artifacts = FilesystemArtifactStore()
    rows = (
        StatementDocumentBalanceRow(
            source="Example",
            account="Example",
            wallet="Example",
            balance_kind="asset_balance",
            asset="BTC",
            quantity=Decimal("1.0"),
            as_of_at=None,
            as_of_precision=TemporalPrecision.TIMESTAMP,
            pdf_file=pdf_path.name,
            notes="stub",
        ),
    )
    registry = StubRegistry([StubPdfAdapter("example", 0, rows)])

    response = ExtractPdfBalancesUseCase(registry, artifacts).execute(
        PdfBalanceExtractRequest(
            pdf_artifact_ref=to_resource_ref(pdf_path),
            output_ref=to_resource_ref(output_path),
            statement_kind="example",
        )
    )

    assert response.statement_kind == "example"
    assert response.row_count == 1
    written_rows = artifacts.read_rows(output_path)
    service_rows = StatementExtractionService(registry).extract_pdf_balance_rows(
        pdf_path,
        requested_statement_kind="example",
    )
    assert written_rows[0]["asset"] == "BTC"
    assert list(service_rows.rows) == written_rows


def test_pdf_balance_extraction_service_rejects_unknown_requested_kind(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "statement.pdf"
    _make_pdf(pdf_path, "Account statement")
    artifacts = FilesystemArtifactStore()

    with pytest.raises(ValueError, match="unsupported statement kind"):
        ExtractPdfBalancesUseCase(StubRegistry([]), artifacts).execute(
            PdfBalanceExtractRequest(
                pdf_artifact_ref=to_resource_ref(pdf_path),
                output_ref=to_resource_ref(tmp_path / "balances.csv"),
                statement_kind="kraken",
            )
        )


def test_pdf_balance_extraction_service_rejects_unrecognized_requested_kind_result(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "statement.pdf"
    _make_pdf(pdf_path, "Account statement")
    artifacts = FilesystemArtifactStore()
    registry = StubRegistry([StubPdfAdapter("example", 100, (), recognized=False)])

    with pytest.raises(
        ValueError, match="statement kind example did not recognize statement.pdf"
    ):
        ExtractPdfBalancesUseCase(registry, artifacts).execute(
            PdfBalanceExtractRequest(
                pdf_artifact_ref=to_resource_ref(pdf_path),
                output_ref=to_resource_ref(tmp_path / "balances.csv"),
                statement_kind="example",
            )
        )


def test_pdf_balance_extraction_service_rejects_empty_recognized_result(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "statement.pdf"
    _make_pdf(pdf_path, "Account statement")
    artifacts = FilesystemArtifactStore()
    registry = StubRegistry([StubPdfAdapter("example", 100, (), recognized=True)])

    with pytest.raises(
        ValueError,
        match=(
            "statement kind example recognized statement.pdf but produced no balance rows"
        ),
    ):
        ExtractPdfBalancesUseCase(registry, artifacts).execute(
            PdfBalanceExtractRequest(
                pdf_artifact_ref=to_resource_ref(pdf_path),
                output_ref=to_resource_ref(tmp_path / "balances.csv"),
                statement_kind="example",
            )
        )


def test_pdf_balance_extraction_service_rejects_unknown_pdf_text(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "statement.pdf"
    _make_pdf(pdf_path, "Generic account export")
    artifacts = FilesystemArtifactStore()

    with pytest.raises(ValueError, match="unable to detect supported statement kind"):
        ExtractPdfBalancesUseCase(
            StubRegistry([StubPdfAdapter("example", 0, ())]),
            artifacts,
        ).execute(
            PdfBalanceExtractRequest(
                pdf_artifact_ref=to_resource_ref(pdf_path),
                output_ref=to_resource_ref(tmp_path / "balances.csv"),
            )
        )


def test_pdf_balance_extraction_service_keeps_non_quantity_statement_rows(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "statement.pdf"
    output_path = tmp_path / "balances.csv"
    _make_pdf(pdf_path, "Performance report")
    artifacts = FilesystemArtifactStore()
    rows = (
        StatementDocumentBalanceRow(
            source="Example",
            account="Example",
            wallet="Example",
            balance_kind="closing_market_value",
            asset="",
            quantity=None,
            as_of_at=None,
            as_of_precision=TemporalPrecision.TIMESTAMP,
            pdf_file=pdf_path.name,
            as_of_text="2026-03-31 23:59 EDT",
            value_amount="123.45",
            value_currency="CAD",
            notes="valuation-only row",
        ),
    )
    registry = StubRegistry([StubPdfAdapter("example", 100, rows)])

    response = ExtractPdfBalancesUseCase(registry, artifacts).execute(
        PdfBalanceExtractRequest(
            pdf_artifact_ref=to_resource_ref(pdf_path),
            output_ref=to_resource_ref(output_path),
            statement_kind="example",
        )
    )

    assert response.row_count == 1
    assert artifacts.read_rows(output_path) == [
        {
            "source": "Example",
            "account": "Example",
            "wallet": "Example",
            "balance_kind": "closing_market_value",
            "asset": "",
            "quantity": "",
            "staked_quantity": "",
            "value_amount": "123.45",
            "value_currency": "CAD",
            "price_amount": "",
            "price_currency": "",
            "as_of": "2026-03-31 23:59 EDT",
            "pdf_file": "statement.pdf",
            "notes": "valuation-only row",
        }
    ]


def test_pdf_balance_extraction_service_rejects_ambiguous_detection(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "statement.pdf"
    _make_pdf(pdf_path, "Ambiguous statement")
    artifacts = FilesystemArtifactStore()
    registry = StubRegistry(
        [
            StubPdfAdapter("alpha", 100, ()),
            StubPdfAdapter("beta", 100, ()),
        ]
    )

    with pytest.raises(ValueError, match="ambiguous PDF statement kind: alpha, beta"):
        ExtractPdfBalancesUseCase(registry, artifacts).execute(
            PdfBalanceExtractRequest(
                pdf_artifact_ref=to_resource_ref(pdf_path),
                output_ref=to_resource_ref(tmp_path / "balances.csv"),
            )
        )


def test_source_statement_extraction_skips_unmatched_inventory_pdf(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "statement.pdf"
    _make_pdf(pdf_path, "Unrecognized statement")
    adapter = StubPdfAdapter("example", 0, (), recognized=False)
    registry = StubRegistry([adapter])
    profile = SourceProfile(
        source=SourceId("Example"),
        raw_dir=str(tmp_path),
        adapter_id=AdapterId("example"),
        manifest_fingerprint="fixture",
        file_inventory=(
            FileInventoryEntry(
                relative_path=pdf_path.name,
                suffix=".pdf",
                size_bytes=pdf_path.stat().st_size,
                sha256="fixture",
                source_path=str(pdf_path),
                capture_uid="capture-1",
                source="Example",
                evidence_role="statement_source",
                originality_class="upstream_original",
            ),
        ),
        supported=True,
    )

    result = StatementExtractionService(registry).extract_source_balance_evidence(
        profile, tmp_path
    )

    assert not result.balance_evidence
    assert not result.issues
    assert not result.reviews
    assert adapter.parse_calls == 0


def test_source_statement_extraction_reports_unrecognized_matched_inventory_pdf(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "statement.pdf"
    _make_pdf(pdf_path, "Unrecognized statement")
    registry = StubRegistry([StubPdfAdapter("example", 100, (), recognized=False)])
    profile = SourceProfile(
        source=SourceId("Example"),
        raw_dir=str(tmp_path),
        adapter_id=AdapterId("example"),
        manifest_fingerprint="fixture",
        file_inventory=(
            FileInventoryEntry(
                relative_path=pdf_path.name,
                suffix=".pdf",
                size_bytes=pdf_path.stat().st_size,
                sha256="fixture",
                source_path=str(pdf_path),
                capture_uid="capture-1",
                source="Example",
                evidence_role="statement_source",
                originality_class="upstream_original",
            ),
        ),
        supported=True,
    )

    result = StatementExtractionService(registry).extract_source_balance_evidence(
        profile, tmp_path
    )

    assert not result.balance_evidence
    assert not result.reviews
    assert [issue.kind for issue in result.issues] == [
        "statement_document_unrecognized"
    ]
    assert result.issues[0].to_row() | {"message": ""} == {
        "issue_id": "Example:statement.pdf:statement_document_unrecognized",
        "source": "Example",
        "adapter_id": "example",
        "severity": "medium",
        "kind": "statement_document_unrecognized",
        "message": "",
        "context_timestamp": "",
        "raw_file": "statement.pdf",
        "raw_row_ref": "",
        "raw_capture_uid": "capture-1",
        "raw_relative_path": "statement.pdf",
        "raw_archive_member_path": "",
        "raw_locator_kind": "raw_file",
        "raw_anchor": "",
        "status": "open",
    }


def test_source_statement_extraction_prefers_document_effective_at(
    tmp_path: Path,
) -> None:
    first_pdf = tmp_path / "first.pdf"
    second_pdf = tmp_path / "second.pdf"
    _make_pdf(first_pdf, "Statement one")
    _make_pdf(second_pdf, "Statement two")
    statement_as_of = datetime(2026, 3, 23, 0, 0, tzinfo=UTC)
    rows_by_pdf = {
        first_pdf.name: (
            StatementDocumentBalanceRow(
                source="Example",
                account="Example",
                wallet="Example",
                balance_kind="available",
                asset="BTC",
                quantity=Decimal("1.0"),
                as_of_at=statement_as_of,
                as_of_precision=TemporalPrecision.DATE,
                pdf_file=first_pdf.name,
                raw_row_ref="page=1",
            ),
        ),
        second_pdf.name: (
            StatementDocumentBalanceRow(
                source="Example",
                account="Example",
                wallet="Example",
                balance_kind="available",
                asset="BTC",
                quantity=Decimal("2.0"),
                as_of_at=statement_as_of,
                as_of_precision=TemporalPrecision.DATE,
                pdf_file=second_pdf.name,
                raw_row_ref="page=1",
            ),
        ),
    }

    class EffectiveDateAdapter(StubPdfAdapter):
        @override
        def parse_statement_document(
            self, pdf_path: Path, text: str
        ) -> StatementDocumentParseResult:
            del text
            self.parse_calls += 1
            return StatementDocumentParseResult(
                pdf_file=pdf_path.name,
                recognized=True,
                statement_as_of_at=statement_as_of,
                rows=rows_by_pdf[pdf_path.name],
                document_effective_at=(
                    datetime(2026, 3, 20, 0, 0, tzinfo=UTC)
                    if pdf_path.name == first_pdf.name
                    else datetime(2026, 3, 23, 0, 0, tzinfo=UTC)
                ),
            )

        @override
        def resolve_statement_instrument_claims(
            self, row: StatementDocumentBalanceRow
        ) -> tuple[InstrumentIdentityClaim, ...]:
            del row
            return (InstrumentIdentityClaim("symbol", "BTC"),)

    adapter = EffectiveDateAdapter("example", 100, ())
    registry = StubRegistry([adapter])
    profile = SourceProfile(
        source=SourceId("Example"),
        raw_dir=str(tmp_path),
        adapter_id=AdapterId("example"),
        manifest_fingerprint="fixture",
        file_inventory=(
            FileInventoryEntry(
                relative_path=first_pdf.name,
                suffix=".pdf",
                size_bytes=first_pdf.stat().st_size,
                sha256="first",
                source_path=str(first_pdf),
                capture_uid="capture-1",
                source="Example",
                evidence_role="statement_source",
                originality_class="upstream_original",
            ),
            FileInventoryEntry(
                relative_path=second_pdf.name,
                suffix=".pdf",
                size_bytes=second_pdf.stat().st_size,
                sha256="second",
                source_path=str(second_pdf),
                capture_uid="capture-1",
                source="Example",
                evidence_role="statement_source",
                originality_class="upstream_original",
            ),
        ),
        supported=True,
    )

    result = StatementExtractionService(registry).extract_source_balance_evidence(
        profile, tmp_path
    )

    assert not result.issues
    assert [row.provenance.relative_path for row in result.balance_evidence] == [
        "second.pdf"
    ]


def test_source_statement_extraction_keeps_older_unique_rows_for_same_snapshot(
    tmp_path: Path,
) -> None:
    first_pdf = tmp_path / "first.pdf"
    second_pdf = tmp_path / "second.pdf"
    _make_pdf(first_pdf, "Statement one")
    _make_pdf(second_pdf, "Statement two")
    statement_as_of = datetime(2026, 3, 23, 0, 0, tzinfo=UTC)
    rows_by_pdf = {
        first_pdf.name: (
            StatementDocumentBalanceRow(
                source="Example",
                account="Example",
                wallet="Example",
                balance_kind="available",
                asset="BTC",
                quantity=Decimal("1.0"),
                as_of_at=statement_as_of,
                as_of_precision=TemporalPrecision.DATE,
                pdf_file=first_pdf.name,
                raw_row_ref="page=1",
            ),
            StatementDocumentBalanceRow(
                source="Example",
                account="Example",
                wallet="Example",
                balance_kind="available",
                asset="ETH",
                quantity=Decimal("3.0"),
                as_of_at=statement_as_of,
                as_of_precision=TemporalPrecision.DATE,
                pdf_file=first_pdf.name,
                raw_row_ref="page=2",
            ),
        ),
        second_pdf.name: (
            StatementDocumentBalanceRow(
                source="Example",
                account="Example",
                wallet="Example",
                balance_kind="available",
                asset="BTC",
                quantity=Decimal("2.0"),
                as_of_at=statement_as_of,
                as_of_precision=TemporalPrecision.DATE,
                pdf_file=second_pdf.name,
                raw_row_ref="page=1",
            ),
        ),
    }

    class EffectiveDateAdapter(StubPdfAdapter):
        @override
        def parse_statement_document(
            self, pdf_path: Path, text: str
        ) -> StatementDocumentParseResult:
            del text
            self.parse_calls += 1
            return StatementDocumentParseResult(
                pdf_file=pdf_path.name,
                recognized=True,
                statement_as_of_at=statement_as_of,
                rows=rows_by_pdf[pdf_path.name],
                document_effective_at=(
                    datetime(2026, 3, 20, 0, 0, tzinfo=UTC)
                    if pdf_path.name == first_pdf.name
                    else datetime(2026, 3, 23, 0, 0, tzinfo=UTC)
                ),
            )

        @override
        def resolve_statement_instrument_claims(
            self, row: StatementDocumentBalanceRow
        ) -> tuple[InstrumentIdentityClaim, ...]:
            return (InstrumentIdentityClaim("symbol", row.asset),)

    adapter = EffectiveDateAdapter("example", 100, ())
    registry = StubRegistry([adapter])
    profile = SourceProfile(
        source=SourceId("Example"),
        raw_dir=str(tmp_path),
        adapter_id=AdapterId("example"),
        manifest_fingerprint="fixture",
        file_inventory=(
            FileInventoryEntry(
                relative_path=first_pdf.name,
                suffix=".pdf",
                size_bytes=first_pdf.stat().st_size,
                sha256="first",
                source_path=str(first_pdf),
                capture_uid="capture-1",
                source="Example",
                evidence_role="statement_source",
                originality_class="upstream_original",
            ),
            FileInventoryEntry(
                relative_path=second_pdf.name,
                suffix=".pdf",
                size_bytes=second_pdf.stat().st_size,
                sha256="second",
                source_path=str(second_pdf),
                capture_uid="capture-1",
                source="Example",
                evidence_role="statement_source",
                originality_class="upstream_original",
            ),
        ),
        supported=True,
    )

    result = StatementExtractionService(registry).extract_source_balance_evidence(
        profile, tmp_path
    )

    assert not result.issues
    assert [(row.instrument_id, row.quantity) for row in result.balance_evidence] == [
        ("symbol:BTC", Decimal("2.0")),
        ("symbol:ETH", Decimal("3.0")),
    ]
    assert [row.provenance.relative_path for row in result.balance_evidence] == [
        "second.pdf",
        "first.pdf",
    ]


def test_source_statement_extraction_reports_ambiguous_latest_inventory_pdfs(
    tmp_path: Path,
) -> None:
    first_pdf = tmp_path / "first.pdf"
    second_pdf = tmp_path / "second.pdf"
    _make_pdf(first_pdf, "Statement one")
    _make_pdf(second_pdf, "Statement two")
    latest_as_of = datetime(2026, 3, 23, 0, 0)
    rows = (
        StatementDocumentBalanceRow(
            source="Example",
            account="Example",
            wallet="Example",
            balance_kind="available",
            asset="BTC",
            quantity=Decimal("1.0"),
            as_of_at=latest_as_of,
            as_of_precision=TemporalPrecision.DATE,
            pdf_file=first_pdf.name,
            raw_row_ref="page=1",
        ),
    )
    adapter = StubPdfAdapter("example", 100, rows)
    adapter.statement_as_of_at = latest_as_of
    registry = StubRegistry([adapter])
    profile = SourceProfile(
        source=SourceId("Example"),
        raw_dir=str(tmp_path),
        adapter_id=AdapterId("example"),
        manifest_fingerprint="fixture",
        file_inventory=(
            FileInventoryEntry(
                relative_path=first_pdf.name,
                suffix=".pdf",
                size_bytes=first_pdf.stat().st_size,
                sha256="first",
                source_path=str(first_pdf),
                capture_uid="capture-1",
                source="Example",
                evidence_role="statement_source",
                originality_class="upstream_original",
            ),
            FileInventoryEntry(
                relative_path=second_pdf.name,
                suffix=".pdf",
                size_bytes=second_pdf.stat().st_size,
                sha256="second",
                source_path=str(second_pdf),
                capture_uid="capture-1",
                source="Example",
                evidence_role="statement_source",
                originality_class="upstream_original",
            ),
        ),
        supported=True,
    )

    result = StatementExtractionService(registry).extract_source_balance_evidence(
        profile, tmp_path
    )

    assert not result.balance_evidence
    assert not result.reviews
    assert [issue.kind for issue in result.issues] == [
        "statement_document_ambiguous",
        "statement_document_ambiguous",
    ]
    assert {issue.raw_file for issue in result.issues} == {"first.pdf", "second.pdf"}
    assert all("first.pdf, second.pdf" in issue.message for issue in result.issues)
