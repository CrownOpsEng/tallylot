from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.profiling import BuildProfileUseCase
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore
from crypto_reconciliation.ports.source_adapters import SourceAdapter
from crypto_reconciliation.ports.source_profiles import SourceProfile

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "adapter_packs"


def fixture_raw_dir(adapter: str, pack: str) -> Path:
    return FIXTURE_ROOT / adapter / pack / "raw"


def profile_and_adapter(source: str, raw_dir: Path) -> tuple[SourceProfile, SourceAdapter]:
    registry = build_registry()
    profile = BuildProfileUseCase(registry, FilesystemArtifactStore()).create_profile(source, raw_dir)
    return profile, registry.source_adapter(str(profile.adapter_id))
