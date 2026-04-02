"""Normalization capability request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NormalizeRequest:
    source: str
    raw_dir: Path
    output_dir: Path
    window_start: str | None = None
    window_end: str | None = None
    inspect_archives: bool = True


@dataclass(frozen=True)
class NormalizeResponse:
    output_dir: Path
    adapter_id: str
    fact_count: int
    balance_count: int
    issue_count: int
    review_count: int
