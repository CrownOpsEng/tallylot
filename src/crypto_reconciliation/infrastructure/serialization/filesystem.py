"""Filesystem-backed artifact store."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, override

from crypto_reconciliation.infrastructure.serialization.csv_io import read_rows, write_rows
from crypto_reconciliation.infrastructure.serialization.json_io import write_json
from crypto_reconciliation.ports.artifacts import ArtifactStorePort


class FilesystemArtifactStore(ArtifactStorePort):
    @override
    def read_rows(self, path: Path) -> list[dict[str, str]]:
        return read_rows(path)

    @override
    def write_rows(
        self,
        path: Path,
        header: tuple[str, ...],
        rows: Iterable[dict[str, str]],
    ) -> None:
        write_rows(path, header, rows)

    @override
    def write_json(self, path: Path, payload: Any) -> None:
        write_json(path, payload)
