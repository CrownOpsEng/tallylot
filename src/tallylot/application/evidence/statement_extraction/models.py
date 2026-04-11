"""Shared statement extraction result models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PdfBalanceRows:
    adapter_id: str
    rows: tuple[dict[str, str], ...]
