from __future__ import annotations

from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from tallylot.application.checkpoints import ExtractPdfBalancesUseCase, PdfBalanceExtractRequest
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.adapter_contracts import AdapterManifest
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from tallylot.ports.source_adapters import SourceAdapter
from tallylot.ports.source_profiles import FileFamilyClaim, FileInventoryEntry, SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch


class StubPdfAdapter:
    def __init__(self, adapter_id: str, match_score: int, rows: list[dict[str, str]]) -> None:
        self.manifest = AdapterManifest(
            adapter_id=AdapterId(adapter_id),
            display_name=adapter_id.title(),
            version="1.0.0",
            capabilities=frozenset(),
        )
        self._match_score = match_score
        self._rows = rows

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
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
        return None

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

    def match_pdf_statement(self, pdf_path: Path, text: str) -> int:
        del pdf_path, text
        return self._match_score

    def extract_pdf_balances(self, pdf_path: Path, text: str) -> list[dict[str, str]]:
        del pdf_path, text
        return self._rows

    def translate(self, profile: SourceProfile, raw_dir: Path) -> SourceTranslationBatch:
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


def test_pdf_balance_extraction_service_uses_requested_supported_adapter(tmp_path: Path) -> None:
    pdf_path = tmp_path / "statement.pdf"
    output_path = tmp_path / "balances.csv"
    _make_pdf(pdf_path, "Account statement")
    artifacts = FilesystemArtifactStore()
    rows = [
        {
            "source": "Example",
            "account": "Example",
            "wallet": "Example",
            "balance_kind": "asset_balance",
            "asset": "BTC",
            "quantity": "1.0",
            "staked_quantity": "",
            "value_amount": "",
            "value_currency": "",
            "price_amount": "",
            "price_currency": "",
            "as_of": "",
            "pdf_file": pdf_path.name,
            "notes": "stub",
        }
    ]
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
    assert written_rows[0]["asset"] == "BTC"


def test_pdf_balance_extraction_service_rejects_unknown_requested_kind(tmp_path: Path) -> None:
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


def test_pdf_balance_extraction_service_rejects_unknown_pdf_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "statement.pdf"
    _make_pdf(pdf_path, "Generic account export")
    artifacts = FilesystemArtifactStore()

    with pytest.raises(ValueError, match="unable to detect supported statement kind"):
        ExtractPdfBalancesUseCase(
            StubRegistry([StubPdfAdapter("example", 0, [])]),
            artifacts,
        ).execute(
            PdfBalanceExtractRequest(
                pdf_artifact_ref=to_resource_ref(pdf_path),
                output_ref=to_resource_ref(tmp_path / "balances.csv"),
            )
        )


def test_pdf_balance_extraction_service_rejects_ambiguous_detection(tmp_path: Path) -> None:
    pdf_path = tmp_path / "statement.pdf"
    _make_pdf(pdf_path, "Ambiguous statement")
    artifacts = FilesystemArtifactStore()
    registry = StubRegistry(
        [
            StubPdfAdapter("alpha", 100, []),
            StubPdfAdapter("beta", 100, []),
        ]
    )

    with pytest.raises(ValueError, match="ambiguous PDF statement kind: alpha, beta"):
        ExtractPdfBalancesUseCase(registry, artifacts).execute(
            PdfBalanceExtractRequest(
                pdf_artifact_ref=to_resource_ref(pdf_path),
                output_ref=to_resource_ref(tmp_path / "balances.csv"),
            )
        )
