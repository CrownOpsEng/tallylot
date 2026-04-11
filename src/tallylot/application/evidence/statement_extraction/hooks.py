"""Statement document adapter hook protocols."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from tallylot.domain.instruments import InstrumentIdentityClaim
from tallylot.ports.adapter_contracts import AdapterManifest
from tallylot.ports.evidence import (
    StatementDocumentBalanceRow,
    StatementDocumentParseResult,
)


class StatementDocumentParser(Protocol):
    manifest: AdapterManifest

    def match_statement_document(self, pdf_path: Path, text: str) -> int: ...

    def parse_statement_document(
        self, pdf_path: Path, text: str
    ) -> StatementDocumentParseResult: ...


class StatementDocumentEvidenceAdapter(StatementDocumentParser, Protocol):
    def resolve_statement_instrument_claims(
        self,
        row: StatementDocumentBalanceRow,
    ) -> tuple[InstrumentIdentityClaim, ...]: ...


def supports_statement_document_parser(adapter: object) -> bool:
    return callable(getattr(adapter, "match_statement_document", None)) and callable(
        getattr(adapter, "parse_statement_document", None)
    )


def supports_statement_document_evidence(adapter: object) -> bool:
    return supports_statement_document_parser(adapter) and callable(
        getattr(adapter, "resolve_statement_instrument_claims", None)
    )
