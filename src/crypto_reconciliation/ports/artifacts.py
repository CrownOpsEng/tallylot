"""Artifact persistence ports."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol


class ArtifactStorePort(Protocol):
    def read_rows(self, path: Path) -> list[dict[str, str]]:
        ...

    def write_rows(
        self,
        path: Path,
        header: tuple[str, ...],
        rows: Iterable[dict[str, str]],
    ) -> None:
        ...

    def write_json(self, path: Path, payload: Any) -> None:
        ...
