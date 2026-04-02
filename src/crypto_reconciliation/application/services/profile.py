"""Source profiling service."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from crypto_reconciliation.application.dtos import ProfileRequest, ProfileResponse
from crypto_reconciliation.application.services.common import (
    csv_header_and_count,
    ensure_directory,
    sha256sum,
)
from crypto_reconciliation.domain.models import FileInventoryEntry, SourceProfile
from crypto_reconciliation.domain.types import AdapterId, SourceId
from crypto_reconciliation.infrastructure.discovery.adapters import AdapterRegistry
from crypto_reconciliation.infrastructure.serialization.csv_io import write_rows
from crypto_reconciliation.infrastructure.serialization.json_io import write_json
from crypto_reconciliation.ports.adapters import SourceAdapter


class ProfileService:
    def __init__(self, registry: AdapterRegistry) -> None:
        self._registry = registry

    def execute(self, request: ProfileRequest) -> ProfileResponse:
        ensure_directory(request.output_dir)
        profile = self.create_profile(request.source, request.raw_dir)
        self.write_profile_artifacts(profile, request.output_dir)
        return ProfileResponse(
            output_dir=request.output_dir,
            adapter_id=str(profile.adapter_id),
            file_count=len(profile.file_inventory),
            supported=profile.supported,
        )

    def create_profile(self, source: str, raw_dir: Path) -> SourceProfile:
        inventory = self._build_inventory(raw_dir)
        adapter = self._select_adapter(source, raw_dir, tuple(inventory))
        fingerprint = self._manifest_fingerprint(inventory)
        return SourceProfile(
            source=SourceId(source),
            raw_dir=str(raw_dir),
            adapter_id=AdapterId(str(adapter.manifest.adapter_id)),
            manifest_fingerprint=fingerprint,
            file_inventory=tuple(inventory),
            supported=adapter.manifest.supported,
            metadata={"display_name": adapter.manifest.display_name},
        )

    def write_profile_artifacts(self, profile: SourceProfile, output_dir: Path) -> None:
        write_json(output_dir / "profile.json", profile.to_dict())
        write_rows(
            output_dir / "profile_inventory.csv",
            ("relative_path", "suffix", "size_bytes", "sha256", "row_count", "header"),
            (
                {
                    "relative_path": entry.relative_path,
                    "suffix": entry.suffix,
                    "size_bytes": str(entry.size_bytes),
                    "sha256": entry.sha256,
                    "row_count": "" if entry.row_count is None else str(entry.row_count),
                    "header": "|".join(entry.header),
                }
                for entry in profile.file_inventory
            ),
        )

    def _build_inventory(self, raw_dir: Path) -> list[FileInventoryEntry]:
        inventory: list[FileInventoryEntry] = []
        for path in sorted(candidate for candidate in raw_dir.rglob("*") if candidate.is_file()):
            header, row_count = csv_header_and_count(path)
            inventory.append(
                FileInventoryEntry(
                    relative_path=str(path.relative_to(raw_dir)),
                    suffix=path.suffix.lower(),
                    size_bytes=path.stat().st_size,
                    sha256=sha256sum(path),
                    row_count=row_count,
                    header=header,
                )
            )
        return inventory

    def _select_adapter(
        self,
        source: str,
        raw_dir: Path,
        inventory: tuple[FileInventoryEntry, ...],
    ) -> SourceAdapter:
        ranked = sorted(
            (
                (adapter.match(source, raw_dir, inventory), adapter)
                for adapter in self._registry.source_adapters
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        score, adapter = ranked[0]
        if score <= 0:
            raise ValueError(f"no source adapter matched {source!r} at {raw_dir}")
        return adapter

    def _manifest_fingerprint(self, inventory: list[FileInventoryEntry]) -> str:
        payload = [
            {
                "relative_path": item.relative_path,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
            }
            for item in inventory
        ]
        return sha256sum_from_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def sha256sum_from_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
