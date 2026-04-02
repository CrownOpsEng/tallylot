"""ZIP-member traversal for archive scanning."""

from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile, ZipInfo

from .archive_members import handle_archive_member_limits, record_archive_member, resolve_archive_member
from .archive_models import ArchiveMemberContext, ArchiveScanState, ResolvedArchiveMember
from .archive_support import write_extracted_file


def scan_zip_file(
    archive_path: Path,
    *,
    relative_path: str,
    state: ArchiveScanState,
    depth: int,
) -> None:
    if state.extracted_root is None:
        return
    archive_size = archive_path.stat().st_size
    if archive_size > state.settings.max_archive_file_size_bytes:
        state.add_issue(
            relative_path=relative_path,
            kind="archive_too_large",
            message=(
                f"Archive exceeds the {state.settings.max_archive_file_size_bytes} "
                f"byte inspection limit; skipping members for "
                f"{relative_path!r}."
            ),
        )
        return
    try:
        with ZipFile(archive_path) as handle:
            scan_zip_handle(
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


def scan_nested_zip_bytes(
    payload: bytes,
    *,
    relative_path: str,
    state: ArchiveScanState,
    depth: int,
) -> None:
    extracted_root = state.extracted_root
    if extracted_root is None:
        return
    if len(payload) > state.settings.max_archive_file_size_bytes:
        state.add_issue(
            relative_path=relative_path,
            kind="archive_too_large",
            message=(
                f"Nested archive exceeds the {state.settings.max_archive_file_size_bytes} "
                f"byte inspection limit; skipping members for "
                f"{relative_path!r}."
            ),
        )
        return
    extracted_path = write_extracted_file(
        extracted_root,
        relative_path=relative_path,
        payload=payload,
    )
    try:
        with ZipFile(extracted_path) as handle:
            scan_zip_handle(
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


def scan_zip_handle(
    handle: ZipFile,
    *,
    archive_relative_path: str,
    state: ArchiveScanState,
    depth: int,
) -> None:
    if depth >= state.settings.max_archive_depth:
        state.add_issue(
            relative_path=archive_relative_path,
            kind="archive_depth_limit_exceeded",
            message=(
                f"Archive nesting exceeds the maximum depth of "
                f"{state.settings.max_archive_depth}; skipping members under "
                f"{archive_relative_path!r}."
            ),
        )
        return

    context = ArchiveMemberContext(
        archive_relative_path=archive_relative_path,
        seen_paths=set(),
        state=state,
        settings=state.settings,
        depth=depth,
    )
    for member in sorted(handle.infolist(), key=lambda item: item.filename):
        if member.is_dir():
            continue
        if not scan_zip_member(handle, member, context):
            return


def scan_zip_member(handle: ZipFile, member: ZipInfo, context: ArchiveMemberContext) -> bool:
    resolved_member = resolve_archive_member(member, context)
    if resolved_member is None:
        return True
    return read_archive_member(handle, member, context, resolved_member)


def read_archive_member(
    handle: ZipFile,
    member: ZipInfo,
    context: ArchiveMemberContext,
    resolved_member: ResolvedArchiveMember,
) -> bool:
    stop_scan = handle_archive_member_limits(member, context, resolved_member)
    if stop_scan is not None:
        return stop_scan

    next_expanded_bytes = context.state.budget.expanded_bytes + member.file_size
    if next_expanded_bytes > context.settings.max_archive_total_expanded_bytes:
        context.state.add_issue(
            relative_path=context.archive_relative_path,
            kind="archive_expanded_size_limit_exceeded",
            message=(
                "Archive inspection exceeded the total expanded-size "
                f"limit of {context.settings.max_archive_total_expanded_bytes} bytes; "
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
    scanned_member = record_archive_member(
        context=context,
        resolved_member=resolved_member,
        payload=payload,
    )
    context.state.add_file(scanned_member)
    if scanned_member.file_path.suffix.lower() in context.settings.supported_archive_suffixes:
        scan_nested_zip_bytes(
            payload,
            relative_path=resolved_member.relative_path,
            state=context.state,
            depth=context.depth + 1,
        )
    return True
