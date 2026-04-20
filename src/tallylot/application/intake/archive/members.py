"""Archive-member validation and recording helpers."""

from __future__ import annotations

from stat import S_ISLNK
from zipfile import ZipInfo

from .models import ArchiveMemberContext, ResolvedArchiveMember, ScannedFile
from .support import sanitize_archive_member_path, sha256sum_bytes, write_extracted_file


def resolve_archive_member(
    member: ZipInfo,
    context: ArchiveMemberContext,
) -> ResolvedArchiveMember | None:
    member_path = sanitize_archive_member_path(member.filename)
    member_relative_path = (
        f"{context.archive_relative_path}::{member_path}"
        if member_path is not None
        else context.archive_relative_path
    )
    if member_path is None:
        context.state.add_issue(
            relative_path=member_relative_path,
            kind="unsafe_archive_member_path",
            message=f"Archive member {member.filename!r} has an unsafe path and was skipped.",
        )
        return None

    member_name = str(member_path)
    if member_name in context.seen_paths:
        context.state.add_issue(
            relative_path=f"{context.archive_relative_path}::{member_name}",
            kind="duplicate_archive_member_path",
            message=f"Archive member path {member_name!r} appears more than once and was skipped.",
        )
        return None
    context.seen_paths.add(member_name)
    return ResolvedArchiveMember(
        name=member_name,
        relative_path=f"{context.archive_relative_path}::{member_name}",
    )


def handle_archive_member_limits(
    member: ZipInfo,
    context: ArchiveMemberContext,
    resolved_member: ResolvedArchiveMember,
) -> bool | None:
    member_name = resolved_member.name
    if context.state.budget.member_count >= context.settings.max_archive_member_count:
        context.state.add_issue(
            relative_path=context.archive_relative_path,
            kind="archive_member_limit_exceeded",
            message=(
                f"Archive inspection exceeded the "
                f"{context.settings.max_archive_member_count} member limit; skipping "
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
    if member.compress_type not in context.settings.supported_zip_compressions:
        context.state.add_issue(
            relative_path=resolved_member.relative_path,
            kind="unsupported_archive_compression",
            message=f"Archive member {member_name!r} uses an unsupported ZIP compression method.",
        )
        return True
    if S_ISLNK(member.external_attr >> 16):
        context.state.add_issue(
            relative_path=resolved_member.relative_path,
            kind="unsupported_archive_member_type",
            message=f"Archive member {member_name!r} is a symbolic link and was skipped.",
        )
        return True
    if member.file_size > context.settings.max_archive_member_size_bytes:
        context.state.add_issue(
            relative_path=resolved_member.relative_path,
            kind="archive_member_too_large",
            message=(
                f"Archive member {member_name!r} exceeds the "
                f"{context.settings.max_archive_member_size_bytes} byte inspection limit "
                "and was skipped."
            ),
        )
        return True
    return None


def record_archive_member(
    *,
    context: ArchiveMemberContext,
    resolved_member: ResolvedArchiveMember,
    payload: bytes,
) -> ScannedFile:
    extracted_root = context.state.extracted_root
    if extracted_root is None:
        raise ValueError("record_archive_member requires an extracted_root")
    extracted_path = write_extracted_file(
        extracted_root,
        relative_path=resolved_member.relative_path,
        payload=payload,
    )
    return ScannedFile(
        relative_path=resolved_member.relative_path,
        file_path=extracted_path,
        size_bytes=len(payload),
        sha256=sha256sum_bytes(payload),
        archive_source_path=context.archive_relative_path,
        archive_member_path=resolved_member.name,
    )
