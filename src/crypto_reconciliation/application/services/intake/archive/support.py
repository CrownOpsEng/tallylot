"""Support helpers for filesystem and archive scanning."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath

from .models import ArchiveScanSettings, ArchiveScanState, ScannedFile


def filesystem_file(path: Path, *, relative_path: str) -> ScannedFile:
    return ScannedFile(
        relative_path=relative_path,
        file_path=path,
        size_bytes=path.stat().st_size,
        sha256=sha256sum_path(path),
    )


def sanitize_archive_member_path(name: str) -> PurePosixPath | None:
    path = PurePosixPath(name)
    if path.is_absolute():
        return None
    parts = [part for part in path.parts if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        return None
    return PurePosixPath(*parts)


def write_extracted_file(
    extracted_root: Path,
    *,
    relative_path: str,
    payload: bytes,
) -> Path:
    digest = sha256sum_bytes(payload)
    suffix = Path(relative_path.replace("::", "__")).suffix
    target = extracted_root / f"{digest}{suffix}"
    if not target.exists():
        target.write_bytes(payload)
    return target


def has_unsupported_archive_suffix(name: str, settings: ArchiveScanSettings) -> bool:
    lower_name = name.lower()
    return any(lower_name.endswith(suffix) for suffix in settings.unsupported_archive_suffixes)


def resolve_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def sha256sum_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256sum_bytes(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def add_unsupported_archive_issue(
    state: ArchiveScanState,
    *,
    relative_path: str,
    name: str,
) -> None:
    state.add_issue(
        relative_path=relative_path,
        kind="unsupported_archive_type",
        message=(f"Archive inspection supports ZIP only in this phase; skipping archive-style file {name!r}."),
    )
