"""Deterministic filesystem and ZIP archive scanning helpers."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from shutil import rmtree
from stat import S_ISLNK
from tempfile import mkdtemp
from typing import Final, override
from zipfile import (
    ZIP_BZIP2,
    ZIP_DEFLATED,
    ZIP_LZMA,
    ZIP_STORED,
    BadZipFile,
    ZipFile,
    ZipInfo,
)

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


@dataclass
class _ArchiveBudget:
    expanded_bytes: int = 0
    member_count: int = 0


@dataclass
class _ArchiveScanState:
    extracted_root: Path | None
    files: list[ScannedFile]
    issues: list[ScanIssue]
    budget: _ArchiveBudget

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
class _ResolvedArchiveMember:
    name: str
    relative_path: str


@dataclass
class _ArchiveMemberContext:
    archive_relative_path: str
    seen_paths: set[str]
    state: _ArchiveScanState
    depth: int


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
    excluded = {_resolve_path(path) for path in exclude_paths}
    state = _ArchiveScanState(
        extracted_root=extracted_root,
        files=files,
        issues=issues,
        budget=_ArchiveBudget(),
    )

    for candidate in sorted(path for path in root.rglob("*") if path.is_file()):
        resolved = _resolve_path(candidate)
        if resolved in excluded:
            continue
        relative_path = str(candidate.relative_to(root))
        files.append(_filesystem_file(candidate, relative_path=relative_path))
        if not inspect_archives:
            continue
        if candidate.suffix.lower() in SUPPORTED_ARCHIVE_SUFFIXES:
            _scan_zip_file(
                candidate,
                relative_path=relative_path,
                state=state,
                depth=0,
            )
            continue
        if _has_unsupported_archive_suffix(candidate.name):
            state.add_issue(
                relative_path=relative_path,
                kind="unsupported_archive_type",
                message=(
                    "Archive inspection supports ZIP only in this phase; "
                    f"skipping archive-style file {candidate.name!r}."
                ),
            )

    tree.files = tuple(files)
    tree.issues = tuple(issues)
    return tree


def _filesystem_file(path: Path, *, relative_path: str) -> ScannedFile:
    return ScannedFile(
        relative_path=relative_path,
        file_path=path,
        size_bytes=path.stat().st_size,
        sha256=_sha256sum_path(path),
    )


def _scan_zip_file(
    archive_path: Path,
    *,
    relative_path: str,
    state: _ArchiveScanState,
    depth: int,
) -> None:
    if state.extracted_root is None:
        return
    archive_size = archive_path.stat().st_size
    if archive_size > MAX_ARCHIVE_FILE_SIZE_BYTES:
        state.add_issue(
            relative_path=relative_path,
            kind="archive_too_large",
            message=(
                f"Archive exceeds the {MAX_ARCHIVE_FILE_SIZE_BYTES} "
                f"byte inspection limit; skipping members for "
                f"{relative_path!r}."
            ),
        )
        return
    try:
        with ZipFile(archive_path) as handle:
            _scan_zip_handle(
                handle,
                archive_relative_path=relative_path,
                state=state,
                depth=depth,
            )
    except BadZipFile:
        state.add_issue(
            relative_path=relative_path,
            kind="invalid_archive",
            message=f"Could not read ZIP archive {relative_path!r}.",
        )


def _scan_nested_zip_bytes(
    payload: bytes,
    *,
    relative_path: str,
    state: _ArchiveScanState,
    depth: int,
) -> None:
    extracted_root = state.extracted_root
    if extracted_root is None:
        return
    if len(payload) > MAX_ARCHIVE_FILE_SIZE_BYTES:
        state.add_issue(
            relative_path=relative_path,
            kind="archive_too_large",
            message=(
                f"Nested archive exceeds the {MAX_ARCHIVE_FILE_SIZE_BYTES} "
                f"byte inspection limit; skipping members for "
                f"{relative_path!r}."
            ),
        )
        return
    extracted_path = _write_extracted_file(
        extracted_root,
        relative_path=relative_path,
        payload=payload,
    )
    try:
        with ZipFile(extracted_path) as handle:
            _scan_zip_handle(
                handle,
                archive_relative_path=relative_path,
                state=state,
                depth=depth,
            )
    except BadZipFile:
        state.add_issue(
            relative_path=relative_path,
            kind="invalid_archive",
            message=f"Could not read nested ZIP archive {relative_path!r}.",
        )


def _scan_zip_handle(
    handle: ZipFile,
    *,
    archive_relative_path: str,
    state: _ArchiveScanState,
    depth: int,
) -> None:
    if depth >= MAX_ARCHIVE_DEPTH:
        state.add_issue(
            relative_path=archive_relative_path,
            kind="archive_depth_limit_exceeded",
            message=(
                f"Archive nesting exceeds the maximum depth of "
                f"{MAX_ARCHIVE_DEPTH}; skipping members under "
                f"{archive_relative_path!r}."
            ),
        )
        return

    context = _ArchiveMemberContext(
        archive_relative_path=archive_relative_path,
        seen_paths=set(),
        state=state,
        depth=depth,
    )
    for member in sorted(handle.infolist(), key=lambda item: item.filename):
        if member.is_dir():
            continue
        if not _scan_zip_member(handle, member, context):
            return


def _scan_zip_member(handle: ZipFile, member: ZipInfo, context: _ArchiveMemberContext) -> bool:
    resolved_member = _resolve_archive_member(member, context)
    if resolved_member is None:
        return True
    return _read_archive_member(handle, member, context, resolved_member)


def _resolve_archive_member(
    member: ZipInfo,
    context: _ArchiveMemberContext,
) -> _ResolvedArchiveMember | None:
    member_path = _sanitize_archive_member_path(member.filename)
    member_relative_path = (
        f"{context.archive_relative_path}::{member_path}" if member_path is not None else context.archive_relative_path
    )
    if member_path is None:
        context.state.add_issue(
            relative_path=member_relative_path,
            kind="unsafe_archive_member_path",
            message=(f"Archive member {member.filename!r} has an unsafe path and was skipped."),
        )
        return None

    member_name = str(member_path)
    if member_name in context.seen_paths:
        context.state.add_issue(
            relative_path=f"{context.archive_relative_path}::{member_name}",
            kind="duplicate_archive_member_path",
            message=(f"Archive member path {member_name!r} appears more than once and was skipped."),
        )
        return None
    context.seen_paths.add(member_name)
    return _ResolvedArchiveMember(
        name=member_name,
        relative_path=f"{context.archive_relative_path}::{member_name}",
    )


def _read_archive_member(
    handle: ZipFile,
    member: ZipInfo,
    context: _ArchiveMemberContext,
    resolved_member: _ResolvedArchiveMember,
) -> bool:
    stop_scan = _handle_archive_member_limits(member, context, resolved_member)
    if stop_scan is not None:
        return stop_scan

    next_expanded_bytes = context.state.budget.expanded_bytes + member.file_size
    if next_expanded_bytes > MAX_ARCHIVE_TOTAL_EXPANDED_BYTES:
        context.state.add_issue(
            relative_path=context.archive_relative_path,
            kind="archive_expanded_size_limit_exceeded",
            message=(
                "Archive inspection exceeded the total expanded-size "
                f"limit of {MAX_ARCHIVE_TOTAL_EXPANDED_BYTES} bytes; "
                f"skipping remaining members for "
                f"{context.archive_relative_path!r}."
            ),
        )
        return False
    try:
        payload = handle.read(member)
    except OSError:
        context.state.add_issue(
            relative_path=resolved_member.relative_path,
            kind="archive_member_read_failed",
            message=f"Archive member {resolved_member.name!r} could not be read.",
        )
        return True

    context.state.budget.expanded_bytes = next_expanded_bytes
    context.state.budget.member_count += 1
    _record_archive_member(
        context=context,
        resolved_member=resolved_member,
        payload=payload,
    )
    return True


def _handle_archive_member_limits(
    member: ZipInfo,
    context: _ArchiveMemberContext,
    resolved_member: _ResolvedArchiveMember,
) -> bool | None:
    member_name = resolved_member.name
    if context.state.budget.member_count >= MAX_ARCHIVE_MEMBER_COUNT:
        context.state.add_issue(
            relative_path=context.archive_relative_path,
            kind="archive_member_limit_exceeded",
            message=(
                f"Archive inspection exceeded the "
                f"{MAX_ARCHIVE_MEMBER_COUNT} member limit; skipping "
                f"remaining members for {context.archive_relative_path!r}."
            ),
        )
        return False
    if member.flag_bits & 0x1:
        context.state.add_issue(
            relative_path=resolved_member.relative_path,
            kind="encrypted_archive_member",
            message=f"Encrypted archive member {member_name!r} is not supported.",
        )
        return True
    if member.compress_type not in SUPPORTED_ZIP_COMPRESSIONS:
        context.state.add_issue(
            relative_path=resolved_member.relative_path,
            kind="unsupported_archive_compression",
            message=(f"Archive member {member_name!r} uses an unsupported ZIP compression method."),
        )
        return True
    if S_ISLNK(member.external_attr >> 16):
        context.state.add_issue(
            relative_path=resolved_member.relative_path,
            kind="unsupported_archive_member_type",
            message=(f"Archive member {member_name!r} is a symbolic link and was skipped."),
        )
        return True
    if member.file_size > MAX_ARCHIVE_MEMBER_SIZE_BYTES:
        context.state.add_issue(
            relative_path=resolved_member.relative_path,
            kind="archive_member_too_large",
            message=(
                f"Archive member {member_name!r} exceeds the "
                f"{MAX_ARCHIVE_MEMBER_SIZE_BYTES} byte inspection limit "
                "and was skipped."
            ),
        )
        return True
    return None


def _record_archive_member(
    *,
    context: _ArchiveMemberContext,
    resolved_member: _ResolvedArchiveMember,
    payload: bytes,
) -> None:
    extracted_root = context.state.extracted_root
    if extracted_root is None:
        return
    extracted_path = _write_extracted_file(
        extracted_root,
        relative_path=resolved_member.relative_path,
        payload=payload,
    )
    context.state.add_file(
        ScannedFile(
            relative_path=resolved_member.relative_path,
            file_path=extracted_path,
            size_bytes=len(payload),
            sha256=_sha256sum_bytes(payload),
            archive_source_path=context.archive_relative_path,
            archive_member_path=resolved_member.name,
        )
    )
    if extracted_path.suffix.lower() in SUPPORTED_ARCHIVE_SUFFIXES:
        _scan_nested_zip_bytes(
            payload,
            relative_path=resolved_member.relative_path,
            state=context.state,
            depth=context.depth + 1,
        )


def _sanitize_archive_member_path(name: str) -> PurePosixPath | None:
    path = PurePosixPath(name)
    if path.is_absolute():
        return None
    parts = [part for part in path.parts if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        return None
    return PurePosixPath(*parts)


def _write_extracted_file(
    extracted_root: Path,
    *,
    relative_path: str,
    payload: bytes,
) -> Path:
    digest = _sha256sum_bytes(payload)
    suffix = Path(relative_path.replace("::", "__")).suffix
    target = extracted_root / f"{digest}{suffix}"
    if not target.exists():
        target.write_bytes(payload)
    return target


def _has_unsupported_archive_suffix(name: str) -> bool:
    lower_name = name.lower()
    return any(lower_name.endswith(suffix) for suffix in UNSUPPORTED_ARCHIVE_SUFFIXES)


def _resolve_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _sha256sum_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256sum_bytes(payload: bytes) -> str:
    return sha256(payload).hexdigest()
