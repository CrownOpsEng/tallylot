"""Deterministic filesystem and ZIP archive scanning helpers."""

from __future__ import annotations

from pathlib import Path
from tempfile import mkdtemp
from typing import Final
from zipfile import ZIP_BZIP2, ZIP_DEFLATED, ZIP_LZMA, ZIP_STORED

from .models import ArchiveBudget, ArchiveScanSettings, ArchiveScanState, ScanIssue, ScannedFile, ScannedTree
from .support import add_unsupported_archive_issue, filesystem_file, has_unsupported_archive_suffix, resolve_path
from .zip_scan import scan_zip_file

MAX_ARCHIVE_FILE_SIZE_BYTES: Final[int] = 512 * 1024 * 1024
MAX_ARCHIVE_TOTAL_EXPANDED_BYTES: Final[int] = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_MEMBER_SIZE_BYTES: Final[int] = 256 * 1024 * 1024
MAX_ARCHIVE_MEMBER_COUNT: Final[int] = 10_000
MAX_ARCHIVE_DEPTH: Final[int] = 3
SUPPORTED_ZIP_COMPRESSIONS: Final[frozenset[int]] = frozenset({ZIP_STORED, ZIP_DEFLATED, ZIP_BZIP2, ZIP_LZMA})
SUPPORTED_ARCHIVE_SUFFIXES: Final[frozenset[str]] = frozenset({".zip"})
UNSUPPORTED_ARCHIVE_SUFFIXES: Final[frozenset[str]] = frozenset(
    {".tar", ".gz", ".tgz", ".tar.gz", ".bz2", ".xz", ".7z", ".rar"}
)


def scanned_tree_files(
    root: Path,
    *,
    exclude_paths: tuple[Path, ...] = (),
    inspect_archives: bool = True,
) -> ScannedTree:
    extracted_root = Path(mkdtemp(prefix="crypto-recon-archive-scan-")) if inspect_archives else None
    tree = ScannedTree(extracted_root)
    files: list[ScannedFile] = []
    issues: list[ScanIssue] = []
    excluded = {resolve_path(path) for path in exclude_paths}
    settings = ArchiveScanSettings(
        max_archive_file_size_bytes=MAX_ARCHIVE_FILE_SIZE_BYTES,
        max_archive_total_expanded_bytes=MAX_ARCHIVE_TOTAL_EXPANDED_BYTES,
        max_archive_member_size_bytes=MAX_ARCHIVE_MEMBER_SIZE_BYTES,
        max_archive_member_count=MAX_ARCHIVE_MEMBER_COUNT,
        max_archive_depth=MAX_ARCHIVE_DEPTH,
        supported_zip_compressions=SUPPORTED_ZIP_COMPRESSIONS,
        supported_archive_suffixes=SUPPORTED_ARCHIVE_SUFFIXES,
        unsupported_archive_suffixes=UNSUPPORTED_ARCHIVE_SUFFIXES,
    )
    state = ArchiveScanState(
        extracted_root=extracted_root,
        files=files,
        issues=issues,
        budget=ArchiveBudget(),
        settings=settings,
    )

    for candidate in sorted(path for path in root.rglob("*") if path.is_file()):
        resolved = resolve_path(candidate)
        if resolved in excluded:
            continue
        relative_path = str(candidate.relative_to(root))
        files.append(filesystem_file(candidate, relative_path=relative_path))
        if not inspect_archives:
            continue
        if candidate.suffix.lower() in settings.supported_archive_suffixes:
            scan_zip_file(
                candidate,
                relative_path=relative_path,
                state=state,
                depth=0,
            )
            continue
        if has_unsupported_archive_suffix(candidate.name, settings):
            add_unsupported_archive_issue(state, relative_path=relative_path, name=candidate.name)

    tree.files = tuple(files)
    tree.issues = tuple(issues)
    return tree
