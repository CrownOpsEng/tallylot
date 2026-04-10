"""Shared statement extraction orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, cast

from pypdf import PdfReader

from tallylot.ports.adapter_contracts import AdapterManifest
from tallylot.ports.evidence import StatementBalanceEvidenceBatch
from tallylot.ports.source_adapters import SourceAdapterRegistryPort
from tallylot.ports.source_profiles import SourceProfile

from .models import PdfBalanceRows


class _PdfBalanceStatementAdapter(Protocol):
    manifest: AdapterManifest

    def match_pdf_statement(self, pdf_path: Path, text: str) -> int: ...

    def extract_pdf_balances(
        self, pdf_path: Path, text: str
    ) -> list[dict[str, str]]: ...


class _SourceStatementEvidenceAdapter(Protocol):
    manifest: AdapterManifest

    def extract_statement_balance_evidence(
        self,
        profile: SourceProfile,
        raw_dir: Path,
    ) -> StatementBalanceEvidenceBatch: ...


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
        return PdfBalanceRows(
            adapter_id=str(adapter.manifest.adapter_id),
            rows=tuple(adapter.extract_pdf_balances(pdf_path, text)),
        )

    def extract_source_balance_evidence(
        self,
        profile: SourceProfile,
        raw_dir: Path,
    ) -> StatementBalanceEvidenceBatch:
        adapter = self._registry.source_adapter(str(profile.adapter_id))
        if not _supports_source_statement_evidence(adapter):
            return StatementBalanceEvidenceBatch(
                balance_evidence=(), issues=(), reviews=()
            )
        return cast(
            _SourceStatementEvidenceAdapter, adapter
        ).extract_statement_balance_evidence(
            profile,
            raw_dir,
        )


def _extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _resolve_pdf_balance_adapter(
    registry: SourceAdapterRegistryPort,
    pdf_path: Path,
    text: str,
    requested: str | None,
) -> _PdfBalanceStatementAdapter:
    if requested is not None:
        try:
            adapter = registry.source_adapter(requested)
        except KeyError as error:
            raise ValueError(f"unsupported statement kind: {requested}") from error
        if not _supports_pdf_balance_extraction(adapter):
            raise ValueError(f"unsupported statement kind: {requested}")
        return cast(_PdfBalanceStatementAdapter, adapter)
    matches = [
        (candidate.match_pdf_statement(pdf_path, text), candidate)
        for adapter in registry.source_adapters
        if _supports_pdf_balance_extraction(adapter)
        for candidate in (cast(_PdfBalanceStatementAdapter, adapter),)
    ]
    scored_matches = [(score, adapter) for score, adapter in matches if score > 0]
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


def _supports_pdf_balance_extraction(adapter: object) -> bool:
    return callable(getattr(adapter, "match_pdf_statement", None)) and callable(
        getattr(adapter, "extract_pdf_balances", None)
    )


def _supports_source_statement_evidence(adapter: object) -> bool:
    return callable(getattr(adapter, "extract_statement_balance_evidence", None))
