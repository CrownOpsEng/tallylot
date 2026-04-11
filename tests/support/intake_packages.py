from __future__ import annotations

from dataclasses import dataclass

from tallylot.application.intake import PlannedPackageItem


@dataclass(frozen=True)
class PackageContext:
    source_folder: str = "binance"
    capture_label: str = "capture-a"
    scope_tokens: tuple[str, ...] = ()


DEFAULT_PACKAGE_CONTEXT = PackageContext()


def package_item(
    *,
    bundle_id: str,
    bundle_relative_path: str,
    sha256: str,
    relative_path: str,
    context: PackageContext = DEFAULT_PACKAGE_CONTEXT,
) -> PlannedPackageItem:
    return PlannedPackageItem(
        path=f"/incoming/{relative_path}",
        relative_path=relative_path,
        archive_source_path="",
        source_folder=context.source_folder,
        capture_label=context.capture_label,
        category="source_raw",
        action="copy",
        sha256=sha256,
        bundle_id=bundle_id,
        bundle_relative_path=bundle_relative_path,
        scope_tokens=context.scope_tokens,
    )


def archive_item(
    *,
    bundle_id: str,
    bundle_relative_path: str,
    sha256: str,
    archive_source_path: str,
    context: PackageContext = DEFAULT_PACKAGE_CONTEXT,
) -> PlannedPackageItem:
    return PlannedPackageItem(
        path=f"/incoming/{archive_source_path}",
        relative_path=archive_source_path,
        archive_source_path=f"/incoming/{archive_source_path}",
        source_folder=context.source_folder,
        capture_label=context.capture_label,
        category="source_raw",
        action="extract_copy"
        if bundle_relative_path.startswith("contents/")
        else "copy",
        sha256=sha256,
        bundle_id=bundle_id,
        bundle_relative_path=bundle_relative_path,
        scope_tokens=context.scope_tokens,
    )
