"""SQLite storage placeholder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SqliteStorageStub:
    database_path: Path

    def describe(self) -> dict[str, str]:
        return {
            "status": "stub",
            "database_path": str(self.database_path),
            "note": "SQLite storage is intentionally not active in this phase.",
        }
