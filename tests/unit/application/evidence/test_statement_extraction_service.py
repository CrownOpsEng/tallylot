from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import override

from reportlab.pdfgen import canvas

from tallylot.application.evidence.statement_extraction import (
    StatementExtractionService,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.instruments import InstrumentIdentityClaim
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import AdapterId, JsonValue, SourceId
from tallylot.ports.adapter_contracts import AdapterManifest
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
        rows: tuple[StatementDocumentBalanceRow, ...],
    ) -> None:
        self.manifest = AdapterManifest(
            adapter_id=AdapterId(adapter_id),
            display_name=adapter_id.title(),
            version="1.0.0",
            capabilities=frozenset(),
        )
        self._rows = rows
        self.statement_as_of_at: datetime | None = None

    def match(self, source: str, raw_dir: Path, inventory: tuple[object, ...]) -> int:
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
        return 100

    def parse_statement_document(
        self, pdf_path: Path, text: str
    ) -> StatementDocumentParseResult:
        del text
        return StatementDocumentParseResult(
            pdf_file=pdf_path.name,
            recognized=True,
            statement_as_of_at=self.statement_as_of_at,
            rows=self._rows,
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
            balance_references=(),
            balance_reference_issues=(),
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


def test_statement_extraction_preserves_row_level_issues_and_reviews(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "statement.pdf"
    _make_pdf(pdf_path, "Recognized statement")
    statement_as_of = datetime(2026, 3, 23, 0, 0, tzinfo=UTC)
    rows = (
        StatementDocumentBalanceRow(
            source="Example",
            account="Example",
            wallet="Example",
            balance_kind="available",
            asset="BTC",
            quantity=Decimal("1.0"),
            as_of_at=statement_as_of,
            as_of_precision=TemporalPrecision.DATE,
            pdf_file=pdf_path.name,
            raw_row_ref="page=1",
        ),
    )

    class UnresolvedInstrumentAdapter(StubPdfAdapter):
        @override
        def resolve_statement_instrument_claims(
            self, row: StatementDocumentBalanceRow
        ) -> tuple[InstrumentIdentityClaim, ...]:
            del row
            return ()

    adapter = UnresolvedInstrumentAdapter("example", rows)
    adapter.statement_as_of_at = statement_as_of
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

    result = StatementExtractionService(registry).extract_source_balance_references(
        profile, tmp_path
    )

    assert not result.balance_references
    assert [issue.kind for issue in result.issues] == ["instrument_identity_blocked"]
    assert [issue.raw_row_ref for issue in result.issues] == ["page=1"]
    assert [review.kind for review in result.reviews] == ["instrument_identity_review"]
    assert [review.raw_row_ref for review in result.reviews] == ["page=1"]
