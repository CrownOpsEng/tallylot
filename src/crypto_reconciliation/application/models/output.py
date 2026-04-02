"""Output projection request and response models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RenderOutputRequest:
    output_adapter: str
    canonical_events_path: Path
    output_path: Path


@dataclass(frozen=True)
class RenderOutputResponse:
    output_path: Path
    row_count: int
