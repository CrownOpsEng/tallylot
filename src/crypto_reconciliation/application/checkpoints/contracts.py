"""Checkpoint capability request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WalletInventoryRequest:
    normalized_root: Path
    output_path: Path


@dataclass(frozen=True)
class WalletInventoryResponse:
    output_path: Path
    wallet_count: int
    evidence_count: int
    issue_count: int


@dataclass(frozen=True)
class PdfBalanceExtractRequest:
    pdf_path: Path
    output_path: Path
    statement_kind: str | None = None


@dataclass(frozen=True)
class PdfBalanceExtractResponse:
    output_path: Path
    row_count: int
    statement_kind: str
