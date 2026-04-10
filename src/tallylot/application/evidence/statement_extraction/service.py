"""Shared statement extraction orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from pypdf import PdfReader

from tallylot.ports.evidence import (
    StatementBalanceEvidenceBatch,
    StatementDocumentParseResult,
)
from tallylot.ports.source_adapters import SourceAdapterRegistryPort
from tallylot.ports.source_profiles import SourceProfile

from .hooks import (
    StatementDocumentEvidenceAdapter,
    StatementDocumentParser,
    supports_statement_document_evidence,
    supports_statement_document_parser,
)
from .models import PdfBalanceRows
from .rows import statement_row_to_pdf_balance_row
from .source_evidence import extract_source_balance_evidence_from_inventory


class StatementExtractionService:
    def __init__(self, registry: SourceAdapterRegistryPort) -> None:
        self._registry = registry

    def extract_pdf_balance_rows(
        self,
        pdf_path: Path,
        *,
        requested_statement_kind: str | None = None,
    ) -> PdfBalanceRows:
        text = _extract_pdf_text(pdf_path)
        adapter = _resolve_pdf_balance_adapter(
            self._registry, pdf_path, text, requested_statement_kind
        )
        parsed = adapter.parse_statement_document(pdf_path, text)
        _validate_checkpoint_parse_result(
            adapter_id=str(adapter.manifest.adapter_id),
            parsed=parsed,
        )
        return PdfBalanceRows(
            adapter_id=str(adapter.manifest.adapter_id),
            rows=tuple(statement_row_to_pdf_balance_row(row) for row in parsed.rows),
        )

    def extract_source_balance_evidence(
        self,
        profile: SourceProfile,
        raw_dir: Path,
    ) -> StatementBalanceEvidenceBatch:
        adapter = self._registry.source_adapter(str(profile.adapter_id))
        if not supports_statement_document_evidence(adapter):
            return StatementBalanceEvidenceBatch(
                balance_evidence=(), issues=(), reviews=()
            )
        return extract_source_balance_evidence_from_inventory(
            cast(StatementDocumentEvidenceAdapter, adapter),
            profile,
            raw_dir,
            extract_pdf_text=_extract_pdf_text,
        )


def _extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _resolve_pdf_balance_adapter(
    registry: SourceAdapterRegistryPort,
    pdf_path: Path,
    text: str,
    requested: str | None,
) -> StatementDocumentParser:
    if requested is not None:
        return _requested_statement_adapter(registry, requested)
    scored_matches = [
        (score, candidate)
        for adapter in registry.source_adapters
        if supports_statement_document_parser(adapter)
        for candidate in (cast(StatementDocumentParser, adapter),)
        for score in (candidate.match_statement_document(pdf_path, text),)
        if score > 0
    ]
    if not scored_matches:
        raise ValueError("unable to detect supported statement kind from PDF text")
    scored_matches.sort(key=lambda item: item[0], reverse=True)
    best_score = scored_matches[0][0]
    best_adapters = [
        adapter for score, adapter in scored_matches if score == best_score
    ]
    if len(best_adapters) > 1:
        adapter_ids = ", ".join(
            sorted(str(adapter.manifest.adapter_id) for adapter in best_adapters)
        )
        raise ValueError(f"ambiguous PDF statement kind: {adapter_ids}")
    return best_adapters[0]


def _requested_statement_adapter(
    registry: SourceAdapterRegistryPort, requested: str
) -> StatementDocumentParser:
    try:
        adapter = registry.source_adapter(requested)
    except KeyError as error:
        raise ValueError(f"unsupported statement kind: {requested}") from error
    if not supports_statement_document_parser(adapter):
        raise ValueError(f"unsupported statement kind: {requested}")
    return cast(StatementDocumentParser, adapter)


def _validate_checkpoint_parse_result(
    *, adapter_id: str, parsed: StatementDocumentParseResult
) -> None:
    if not parsed.recognized:
        raise ValueError(
            f"statement kind {adapter_id} did not recognize {parsed.pdf_file}"
        )
    if not parsed.rows:
        raise ValueError(
            f"statement kind {adapter_id} recognized {parsed.pdf_file} "
            "but produced no balance rows"
        )
