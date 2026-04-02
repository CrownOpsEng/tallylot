from __future__ import annotations

from pathlib import Path

from reportlab.pdfgen import canvas

from tallylot.application.checkpoints import ExtractPdfBalancesUseCase, PdfBalanceExtractRequest
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_pdf_balance_extraction_service_extracts_supported_statement_rows(tmp_path: Path) -> None:
    pdf_path = tmp_path / "coinbase_statement.pdf"
    output_path = tmp_path / "balances.csv"
    pdf = canvas.Canvas(str(pdf_path))
    pdf.drawString(72, 750, "Coinbase Account Statement")
    pdf.drawString(72, 735, "Portfolio summary balances are as of 2025-12-31 23:59:59 UTC")
    pdf.drawString(72, 720, "BTC 1.2500 N/A 90000.00 CAD/BTC 112500.00 CAD")
    pdf.drawString(72, 705, "ETH 2.5000 N/A 3000.00 CAD/ETH 7500.00 CAD")
    pdf.save()

    response = ExtractPdfBalancesUseCase(build_registry(), FilesystemArtifactStore()).execute(
        PdfBalanceExtractRequest(
            pdf_artifact_ref=to_resource_ref(pdf_path),
            output_ref=to_resource_ref(output_path),
        )
    )

    rows = FilesystemArtifactStore().read_rows(output_path)

    assert response.statement_kind == "coinbase"
    assert response.row_count == 2
    assert rows[0]["source"] == "Coinbase"
    assert rows[0]["balance_kind"] == "asset_balance"
    assert rows[0]["asset"] == "BTC"
    assert rows[0]["quantity"] == "1.25"
    assert rows[0]["price_amount"] == "90000"
    assert rows[0]["value_amount"] == "112500.00"
