"""Round workflow request and response models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class RoundScaffoldRequest:
    workspace_root: Path
    round_id: str
    phase: str
    source: str
    today: date | None = None


@dataclass(frozen=True)
class RoundScaffoldResponse:
    workspace_root: Path
    round_dir: Path
    round_log_path: Path
    readme_path: Path
    seeded: bool
