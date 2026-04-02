"""Baseline validation request and response models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BaselineValidateRequest:
    export_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class BaselineValidateResponse:
    output_dir: Path
    latest_timestamp: str
    asset_count: int
