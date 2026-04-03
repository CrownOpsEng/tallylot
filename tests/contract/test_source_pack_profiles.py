from __future__ import annotations

import pytest

from tallylot.application.profiling import BuildProfileUseCase
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tools.adapter_packs import AdapterPack, select_adapter_packs

ALL_PACKS = select_adapter_packs()


def _pack_id(pack: AdapterPack) -> str:
    return pack.id


@pytest.mark.parametrize("pack", ALL_PACKS, ids=_pack_id)
def test_adapter_pack_profiles_select_expected_adapter_and_timezone_status(pack: AdapterPack) -> None:
    profile = BuildProfileUseCase(build_registry(), FilesystemArtifactStore()).create_profile(pack.source, pack.raw_dir)

    assert str(profile.adapter_id) == pack.expected_adapter
    assert profile.timezone_summary["status"] == pack.expected_timezone_status
