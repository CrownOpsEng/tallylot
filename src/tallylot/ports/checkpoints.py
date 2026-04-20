"""Checkpoint repository port."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from tallylot.domain.checkpoint import Checkpoint


class CheckpointRepositoryPort(Protocol):
    def read_checkpoint(self, path: Path) -> Checkpoint: ...

    def write_checkpoint(self, path: Path, checkpoint: Checkpoint) -> None: ...
