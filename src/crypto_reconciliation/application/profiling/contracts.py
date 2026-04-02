"""Profiling capability request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProfileRequest:
    source: str
    raw_dir: Path
    output_dir: Path
    inspect_archives: bool = True


@dataclass(frozen=True)
class ProfileResponse:
    output_dir: Path
    adapter_id: str
    file_count: int
    supported: bool
    issue_count: int = 0
