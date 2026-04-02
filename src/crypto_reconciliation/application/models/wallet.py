"""Wallet inventory workflow request and response models."""

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
