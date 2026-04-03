from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.services.profile import ProfileService
from crypto_reconciliation.domain.models import SourceProfile
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from crypto_reconciliation.ports.adapters import SourceAdapter

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "adapter_packs"


def fixture_raw_dir(adapter_id: str, pack_name: str) -> Path:
    return FIXTURE_ROOT / adapter_id / pack_name / "raw"


def profile_and_adapter(source: str, raw_dir: Path) -> tuple[SourceProfile, SourceAdapter]:
    registry = build_registry()
    profile = ProfileService(registry, FilesystemArtifactStore()).create_profile(source, raw_dir)
    return profile, registry.source_adapter(str(profile.adapter_id))
