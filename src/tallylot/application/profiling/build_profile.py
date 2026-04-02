"""Build source profiles from raw evidence."""

from __future__ import annotations

from pathlib import Path

from tallylot.application.profiling.contracts import ProfileRequest, ProfileResponse
from tallylot.application.resource_refs import path_from_ref
from tallylot.application.workspace.filesystem import ensure_directory, ensure_output_not_within_input_tree
from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import AdapterId, JsonValue, SourceId
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.source_adapters import SourceAdapter, SourceAdapterRegistryPort
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile

from .artifacts import write_profile_artifacts
from .families import analyze_profile_families
from .inventory import build_inventory, manifest_fingerprint


class BuildProfileUseCase:
    def __init__(self, registry: SourceAdapterRegistryPort, artifacts: ArtifactStorePort) -> None:
        self._registry = registry
        self._artifacts = artifacts

    def execute(self, request: ProfileRequest) -> ProfileResponse:
        raw_dir = path_from_ref(request.raw_capture_ref)
        output_dir = path_from_ref(request.profile_output_ref)
        ensure_output_not_within_input_tree(
            raw_dir,
            output_dir,
            input_label="raw source directory",
            output_label="profile output directory",
        )
        ensure_directory(output_dir)
        profile = self.create_profile(
            request.source,
            raw_dir,
            inspect_archives=request.inspect_archives,
        )
        self.write_profile_artifacts(profile, output_dir)
        return ProfileResponse(
            profile_output_ref=request.profile_output_ref,
            adapter_id=str(profile.adapter_id),
            file_count=len(profile.file_inventory),
            supported=profile.supported,
            issue_count=len(profile.scan_issues),
        )

    def create_profile(
        self,
        source: str,
        raw_dir: Path,
        *,
        inspect_archives: bool = True,
    ) -> SourceProfile:
        inventory, scan_issues = build_inventory(raw_dir, inspect_archives=inspect_archives)
        family_analysis = analyze_profile_families(
            source=source,
            raw_dir=raw_dir,
            inventory=tuple(inventory),
            adapters=self._registry.source_adapters,
        )
        adapter = self._select_adapter(
            source,
            raw_dir,
            family_analysis.inventory,
            selected_adapter_id=family_analysis.selected_adapter_id,
        )
        fingerprint = manifest_fingerprint(list(family_analysis.inventory))
        seed_profile = SourceProfile(
            source=SourceId(source),
            raw_dir=str(raw_dir),
            adapter_id=AdapterId(str(adapter.manifest.adapter_id)),
            manifest_fingerprint=fingerprint,
            file_inventory=family_analysis.inventory,
            supported=adapter.manifest.supported and family_analysis.supported,
            metadata={
                "display_name": adapter.manifest.display_name,
                "recognized_adapter_ids": "; ".join(family_analysis.recognized_adapter_ids),
                "scan_issue_count": str(len(scan_issues) + len(family_analysis.issues)),
            },
            scan_issues=(*scan_issues, *family_analysis.issues),
        )
        timezone_summary, timezone_issues = _validate_profile_timezones(
            adapter,
            source=source,
            profile=seed_profile,
            inventory=list(family_analysis.inventory),
        )
        return SourceProfile(
            source=seed_profile.source,
            raw_dir=seed_profile.raw_dir,
            adapter_id=seed_profile.adapter_id,
            manifest_fingerprint=seed_profile.manifest_fingerprint,
            file_inventory=seed_profile.file_inventory,
            supported=seed_profile.supported,
            metadata={
                **seed_profile.metadata,
                "timezone_issue_count": str(len(timezone_issues)),
            },
            timezone_summary=timezone_summary,
            scan_issues=seed_profile.scan_issues,
            timezone_issues=timezone_issues,
        )

    def write_profile_artifacts(self, profile: SourceProfile, output_dir: Path) -> None:
        write_profile_artifacts(self._artifacts, profile, output_dir)

    def _select_adapter(
        self,
        source: str,
        raw_dir: Path,
        inventory: tuple[FileInventoryEntry, ...],
        *,
        selected_adapter_id: str | None = None,
    ) -> SourceAdapter:
        if selected_adapter_id is not None:
            return self._registry.source_adapter(selected_adapter_id)
        ranked = sorted(
            ((adapter.match(source, raw_dir, inventory), adapter) for adapter in self._registry.source_adapters),
            key=lambda item: item[0],
            reverse=True,
        )
        if not ranked:
            raise ValueError("no source adapters are registered")
        score, adapter = ranked[0]
        if score <= 0:
            raise ValueError(f"no source adapter matched {source!r} at {raw_dir}")
        tied = [candidate for candidate_score, candidate in ranked if candidate_score == score]
        if len(tied) > 1:
            tied_ids = ", ".join(sorted(str(candidate.manifest.adapter_id) for candidate in tied))
            raise ValueError(f"ambiguous source adapter match for {source!r} at {raw_dir}: {tied_ids}")
        return adapter


def _validate_profile_timezones(
    adapter: SourceAdapter,
    *,
    source: str,
    profile: SourceProfile,
    inventory: list[FileInventoryEntry],
) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
    del source, inventory
    summary, issues = adapter.validate_profile_timezones(profile)
    return summary, issues
