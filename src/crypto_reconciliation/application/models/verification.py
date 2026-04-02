"""Verification workflow request and response models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VerificationCompareRequest:
    previous_dir: Path
    current_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class VerificationCompareResponse:
    output_dir: Path
    changed_reports: int
    gate_suggestion: str
