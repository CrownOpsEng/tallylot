from __future__ import annotations

from pathlib import Path

from tallylot.application.profiling import BuildProfileUseCase
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization import FilesystemArtifactStore
from tallylot.ports.source_adapters import SourceAdapter
from tallylot.ports.source_profiles import SourceProfile

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "adapter_packs"


def fixture_raw_dir(adapter: str, pack: str) -> Path:
    return FIXTURE_ROOT / adapter / pack / "raw"


def profile_and_adapter(source: str, raw_dir: Path) -> tuple[SourceProfile, SourceAdapter]:
    registry = build_registry()
    profile = BuildProfileUseCase(registry, FilesystemArtifactStore()).create_profile(source, raw_dir)
    return profile, registry.source_adapter(str(profile.adapter_id))
