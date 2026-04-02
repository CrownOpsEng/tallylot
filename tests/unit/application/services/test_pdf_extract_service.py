from __future__ import annotations

import pytest

from crypto_reconciliation.application.services.pdf_extract import _detect_statement_kind, _parse_balance_lines


def test_detect_statement_kind_accepts_requested_supported_kind() -> None:
    assert _detect_statement_kind("anything", "binance") == "binance"


def test_detect_statement_kind_rejects_unknown_requested_kind() -> None:
    with pytest.raises(ValueError, match="unsupported statement kind"):
        _detect_statement_kind("anything", "kraken")


def test_detect_statement_kind_rejects_unknown_pdf_text() -> None:
    with pytest.raises(ValueError, match="unable to detect supported statement kind"):
        _detect_statement_kind("Generic account export", None)


def test_parse_balance_lines_rejects_empty_supported_statement() -> None:
    with pytest.raises(ValueError, match="no balance rows were extracted"):
        _parse_balance_lines("Coinbase Account Statement", "coinbase")
