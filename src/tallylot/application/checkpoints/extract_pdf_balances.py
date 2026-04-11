"""PDF balance extraction workflow."""

from __future__ import annotations

from tallylot.application.checkpoints.contracts import (
    PdfBalanceExtractRequest,
    PdfBalanceExtractResponse,
)
from tallylot.application.evidence.statement_extraction import (
    StatementExtractionService,
)
from tallylot.application.resource_refs import path_from_ref
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.source_adapters import SourceAdapterRegistryPort

from .pdf_balance_schema import BALANCE_HEADER


class ExtractPdfBalancesUseCase:
    def __init__(
        self, registry: SourceAdapterRegistryPort, artifacts: ArtifactStorePort
    ) -> None:
        self._artifacts = artifacts
        self._statement_extraction = StatementExtractionService(registry)

    def execute(self, request: PdfBalanceExtractRequest) -> PdfBalanceExtractResponse:
        pdf_path = path_from_ref(request.pdf_artifact_ref)
        output_path = path_from_ref(request.output_ref)
        result = self._statement_extraction.extract_pdf_balance_rows(
            pdf_path,
            requested_statement_kind=request.statement_kind,
        )
        self._artifacts.write_rows(output_path, BALANCE_HEADER, result.rows)
        return PdfBalanceExtractResponse(
            output_ref=request.output_ref,
            row_count=len(result.rows),
            statement_kind=result.adapter_id,
        )
