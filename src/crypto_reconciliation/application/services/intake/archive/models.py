"""Archive-scan models and state holders."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from typing import override


@dataclass(frozen=True)
class ScannedFile:
    relative_path: str
    file_path: Path
    size_bytes: int
    sha256: str
    archive_source_path: str = ""
    archive_member_path: str = ""


@dataclass(frozen=True)
class ScanIssue:
    relative_path: str
    kind: str
    message: str
    severity: str = "high"


class ScannedTree(AbstractContextManager["ScannedTree"]):
    def __init__(self, extracted_root: Path | None) -> None:
        self._extracted_root = extracted_root
        self.files: tuple[ScannedFile, ...] = ()
        self.issues: tuple[ScanIssue, ...] = ()

    @override
    def __exit__(self, exc_type: object, exc: object, exc_tb: object) -> None:
        del exc_type, exc, exc_tb
        if self._extracted_root is not None:
            rmtree(self._extracted_root, ignore_errors=True)


@dataclass(frozen=True)
class ArchiveScanSettings:
    max_archive_file_size_bytes: int
    max_archive_total_expanded_bytes: int
    max_archive_member_size_bytes: int
    max_archive_member_count: int
    max_archive_depth: int
    supported_zip_compressions: frozenset[int]
    supported_archive_suffixes: frozenset[str]
    unsupported_archive_suffixes: frozenset[str]


@dataclass
class ArchiveBudget:
    expanded_bytes: int = 0
    member_count: int = 0


@dataclass
class ArchiveScanState:
    extracted_root: Path | None
    files: list[ScannedFile]
    issues: list[ScanIssue]
    budget: ArchiveBudget
    settings: ArchiveScanSettings

    def add_issue(
        self,
        relative_path: str,
        kind: str,
        message: str,
        *,
        severity: str = "high",
    ) -> None:
        self.issues.append(
            ScanIssue(
                relative_path=relative_path,
                kind=kind,
                message=message,
                severity=severity,
            )
        )

    def add_file(self, item: ScannedFile) -> None:
        self.files.append(item)


@dataclass(frozen=True)
class ResolvedArchiveMember:
    name: str
    relative_path: str


@dataclass
class ArchiveMemberContext:
    archive_relative_path: str
    seen_paths: set[str]
    state: ArchiveScanState
    settings: ArchiveScanSettings
    depth: int
