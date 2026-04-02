"""PDF balance extraction workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, cast

from pypdf import PdfReader

from crypto_reconciliation.application.checkpoints.contracts import (
    PdfBalanceExtractRequest,
    PdfBalanceExtractResponse,
)
from crypto_reconciliation.ports.adapter_contracts import AdapterManifest
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.source_adapters import SourceAdapterRegistryPort

from .pdf_balance_schema import BALANCE_HEADER


class PdfBalanceAdapter(Protocol):
    manifest: AdapterManifest

    def match_pdf_statement(self, pdf_path: Path, text: str) -> int: ...

    def extract_pdf_balances(self, pdf_path: Path, text: str) -> list[dict[str, str]]: ...


class ExtractPdfBalancesUseCase:
    def __init__(self, registry: SourceAdapterRegistryPort, artifacts: ArtifactStorePort) -> None:
        self._registry = registry
        self._artifacts = artifacts

    def execute(self, request: PdfBalanceExtractRequest) -> PdfBalanceExtractResponse:
        reader = PdfReader(str(request.pdf_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        adapter = _resolve_pdf_balance_adapter(self._registry, request.pdf_path, text, request.statement_kind)
        rows = adapter.extract_pdf_balances(request.pdf_path, text)
        self._artifacts.write_rows(request.output_path, BALANCE_HEADER, rows)
        return PdfBalanceExtractResponse(
            output_path=request.output_path,
            row_count=len(rows),
            statement_kind=str(adapter.manifest.adapter_id),
        )


def _resolve_pdf_balance_adapter(
    registry: SourceAdapterRegistryPort,
    pdf_path: Path,
    text: str,
    requested: str | None,
) -> PdfBalanceAdapter:
    if requested is not None:
        try:
            adapter = registry.source_adapter(requested)
        except KeyError as error:
            raise ValueError(f"unsupported statement kind: {requested}") from error
        if not _supports_pdf_balance_extraction(adapter):
            raise ValueError(f"unsupported statement kind: {requested}")
        return cast(PdfBalanceAdapter, adapter)
    matches = [
        (candidate.match_pdf_statement(pdf_path, text), candidate)
        for adapter in registry.source_adapters
        if _supports_pdf_balance_extraction(adapter)
        for candidate in (cast(PdfBalanceAdapter, adapter),)
    ]
    scored_matches = [(score, adapter) for score, adapter in matches if score > 0]
    if not scored_matches:
        raise ValueError("unable to detect supported statement kind from PDF text")
    scored_matches.sort(key=lambda item: item[0], reverse=True)
    best_score = scored_matches[0][0]
    best_adapters = [adapter for score, adapter in scored_matches if score == best_score]
    if len(best_adapters) > 1:
        adapter_ids = ", ".join(sorted(str(adapter.manifest.adapter_id) for adapter in best_adapters))
        raise ValueError(f"ambiguous PDF statement kind: {adapter_ids}")
    return best_adapters[0]


def _supports_pdf_balance_extraction(adapter: object) -> bool:
    return callable(getattr(adapter, "match_pdf_statement", None)) and callable(
        getattr(adapter, "extract_pdf_balances", None)
    )
