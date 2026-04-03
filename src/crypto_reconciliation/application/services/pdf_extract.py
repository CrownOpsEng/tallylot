"""PDF balance extraction service."""

from __future__ import annotations

import re
from collections.abc import Callable

from pypdf import PdfReader

from crypto_reconciliation.application.dtos import PdfBalanceExtractRequest, PdfBalanceExtractResponse
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

BALANCE_HEADER = ("asset", "amount", "statement_kind", "source_line")
BALANCE_LINE = re.compile(r"\b([A-Z]{2,10})\b\s+(-?\d[\d,]*(?:\.\d+)?)\b")


class PdfBalanceExtractionService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: PdfBalanceExtractRequest) -> PdfBalanceExtractResponse:
        reader = PdfReader(str(request.pdf_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        statement_kind = _detect_statement_kind(text, request.statement_kind)
        parser = _STATEMENT_PARSERS[statement_kind]
        rows = parser(text)
        self._artifacts.write_rows(request.output_path, BALANCE_HEADER, rows)
        return PdfBalanceExtractResponse(
            output_path=request.output_path,
            row_count=len(rows),
            statement_kind=statement_kind,
        )


def _detect_statement_kind(text: str, requested: str | None) -> str:
    if requested:
        if requested not in _STATEMENT_PARSERS:
            raise ValueError(f"unsupported statement kind: {requested}")
        return requested
    lowered = text.lower()
    for name in ("coinbase", "binance", "shakepay"):
        if name in lowered:
            return name
    raise ValueError("unable to detect supported statement kind from PDF text")


def _parse_balance_lines(text: str, statement_kind: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        match = BALANCE_LINE.search(line.strip())
        if match is None:
            continue
        rows.append(
            {
                "asset": match.group(1),
                "amount": match.group(2).replace(",", ""),
                "statement_kind": statement_kind,
                "source_line": line.strip(),
            }
        )
    if not rows:
        raise ValueError(f"no balance rows were extracted from the {statement_kind} PDF")
    return rows


def _coinbase_rows(text: str) -> list[dict[str, str]]:
    return _parse_balance_lines(text, "coinbase")


def _binance_rows(text: str) -> list[dict[str, str]]:
    return _parse_balance_lines(text, "binance")


def _shakepay_rows(text: str) -> list[dict[str, str]]:
    return _parse_balance_lines(text, "shakepay")


_STATEMENT_PARSERS: dict[str, Callable[[str], list[dict[str, str]]]] = {
    "coinbase": _coinbase_rows,
    "binance": _binance_rows,
    "shakepay": _shakepay_rows,
}
