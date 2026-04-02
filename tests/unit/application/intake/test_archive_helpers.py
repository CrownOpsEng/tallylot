from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipInfo

from crypto_reconciliation.application.intake.archive.members import (
    handle_archive_member_limits,
    record_archive_member,
    resolve_archive_member,
)
from crypto_reconciliation.application.intake.archive.models import (
    ArchiveBudget,
    ArchiveMemberContext,
    ArchiveScanSettings,
    ArchiveScanState,
    ResolvedArchiveMember,
)
from crypto_reconciliation.application.intake.archive.support import (
    add_unsupported_archive_issue,
    filesystem_file,
    has_unsupported_archive_suffix,
    resolve_path,
    sanitize_archive_member_path,
    sha256sum_bytes,
    write_extracted_file,
)


def test_archive_support_helpers_normalize_paths_and_persist_extracted_payloads(tmp_path: Path) -> None:
    payload = b"fixture-data"
    file_path = tmp_path / "wallet.csv"
    file_path.write_bytes(payload)
    extracted_root = tmp_path / "extracted"
    extracted_root.mkdir()

    scanned = filesystem_file(file_path, relative_path="incoming/wallet.csv")
    extracted = write_extracted_file(extracted_root, relative_path="archive.zip::wallet.csv", payload=payload)
    extracted_again = write_extracted_file(
        extracted_root,
        relative_path="archive.zip::wallet.csv",
        payload=payload,
    )

    safe_member_path = sanitize_archive_member_path("nested/./wallet.csv")

    assert safe_member_path is not None
    assert safe_member_path.as_posix() == "nested/wallet.csv"
    assert sanitize_archive_member_path("/absolute/wallet.csv") is None
    assert sanitize_archive_member_path("../wallet.csv") is None
    assert scanned.relative_path == "incoming/wallet.csv"
    assert scanned.sha256 == sha256sum_bytes(payload)
    assert extracted == extracted_again
    assert extracted.read_bytes() == payload
    assert has_unsupported_archive_suffix("bundle.rar", _settings())
    assert resolve_path(Path("~")).is_absolute()


def test_resolve_archive_member_reports_unsafe_and_duplicate_paths(tmp_path: Path) -> None:
    context = _context(tmp_path)
    unsafe = ZipInfo("../escape.csv")
    duplicate = ZipInfo("safe.csv")

    assert resolve_archive_member(unsafe, context) is None
    first = resolve_archive_member(duplicate, context)
    second = resolve_archive_member(duplicate, context)

    assert first is not None
    assert first.relative_path == "archive.zip::safe.csv"
    assert second is None
    assert [issue.kind for issue in context.state.issues] == [
        "unsafe_archive_member_path",
        "duplicate_archive_member_path",
    ]


def test_handle_archive_member_limits_emits_expected_issues(tmp_path: Path) -> None:
    context = _context(tmp_path)
    resolved = _resolved_member(context)

    context.state.budget.member_count = context.settings.max_archive_member_count
    assert handle_archive_member_limits(ZipInfo("limit.csv"), context, resolved) is False

    encrypted = ZipInfo("encrypted.csv")
    encrypted.flag_bits = 0x1
    assert handle_archive_member_limits(encrypted, _context(tmp_path), resolved) is True

    unsupported = ZipInfo("unsupported.csv")
    unsupported.compress_type = 999
    assert handle_archive_member_limits(unsupported, _context(tmp_path), resolved) is True

    symlink = ZipInfo("symlink.csv")
    symlink.external_attr = 0o120000 << 16
    assert handle_archive_member_limits(symlink, _context(tmp_path), resolved) is True

    too_large = ZipInfo("large.csv")
    too_large.file_size = context.settings.max_archive_member_size_bytes + 1
    assert handle_archive_member_limits(too_large, _context(tmp_path), resolved) is True


def test_record_archive_member_requires_extracted_root_and_records_payload(tmp_path: Path) -> None:
    context = _context(tmp_path)
    assert context.state.extracted_root is not None
    context.state.extracted_root.mkdir()
    resolved = _resolved_member(context)

    scanned = record_archive_member(
        context=context,
        resolved_member=resolved,
        payload=b"wallet-data",
    )

    assert scanned.relative_path == "archive.zip::wallet.csv"
    assert scanned.archive_source_path == "archive.zip"
    assert scanned.archive_member_path == "wallet.csv"
    assert scanned.file_path.read_bytes() == b"wallet-data"

    missing_root_context = ArchiveMemberContext(
        archive_relative_path="archive.zip",
        seen_paths=set(),
        state=ArchiveScanState(
            extracted_root=None,
            files=[],
            issues=[],
            budget=ArchiveBudget(),
            settings=_settings(),
        ),
        settings=_settings(),
        depth=0,
    )
    try:
        record_archive_member(
            context=missing_root_context,
            resolved_member=resolved,
            payload=b"wallet-data",
        )
    except ValueError as error:
        assert "extracted_root" in str(error)
    else:
        raise AssertionError("expected record_archive_member to reject missing extracted_root")


def test_add_unsupported_archive_issue_records_zip_only_warning(tmp_path: Path) -> None:
    state = ArchiveScanState(
        extracted_root=tmp_path / "extracted",
        files=[],
        issues=[],
        budget=ArchiveBudget(),
        settings=_settings(),
    )

    add_unsupported_archive_issue(
        state,
        relative_path="incoming/archive.7z",
        name="archive.7z",
    )

    assert state.issues[0].kind == "unsupported_archive_type"
    assert "ZIP only" in state.issues[0].message


def _context(tmp_path: Path) -> ArchiveMemberContext:
    return ArchiveMemberContext(
        archive_relative_path="archive.zip",
        seen_paths=set(),
        state=ArchiveScanState(
            extracted_root=tmp_path / "extracted",
            files=[],
            issues=[],
            budget=ArchiveBudget(),
            settings=_settings(),
        ),
        settings=_settings(),
        depth=0,
    )


def _resolved_member(context: ArchiveMemberContext) -> ResolvedArchiveMember:
    member = ZipInfo("wallet.csv")
    resolved = resolve_archive_member(member, context)
    assert resolved is not None
    return resolved


def _settings() -> ArchiveScanSettings:
    return ArchiveScanSettings(
        max_archive_file_size_bytes=1024,
        max_archive_total_expanded_bytes=4096,
        max_archive_member_size_bytes=256,
        max_archive_member_count=2,
        max_archive_depth=2,
        supported_zip_compressions=frozenset({ZIP_STORED, ZIP_DEFLATED}),
        supported_archive_suffixes=frozenset({".zip"}),
        unsupported_archive_suffixes=frozenset({".rar", ".7z"}),
    )
