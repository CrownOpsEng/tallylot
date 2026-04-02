from __future__ import annotations

from pathlib import Path

import pytest

from tallylot.application.profiling import BuildProfileUseCase, ProfileRequest
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tests.support.services import FakeSourceRegistry, MatchingSourceAdapter


def test_profile_service_rejects_ambiguous_adapter_matches(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    registry = FakeSourceRegistry(
        source_adapters=(
            MatchingSourceAdapter("alpha_adapter"),
            MatchingSourceAdapter("beta_adapter"),
        )
    )

    service = BuildProfileUseCase(registry, FilesystemArtifactStore())

    with pytest.raises(ValueError, match="ambiguous source adapter match"):
        service.create_profile("fixture", raw_dir)


def test_profile_service_rejects_missing_source_directories(tmp_path: Path) -> None:
    registry = FakeSourceRegistry(source_adapters=(MatchingSourceAdapter("alpha_adapter"),))
    service = BuildProfileUseCase(registry, FilesystemArtifactStore())

    with pytest.raises(FileNotFoundError, match="raw source directory does not exist"):
        service.create_profile("fixture", tmp_path / "missing")


def test_profile_service_rejects_output_inside_raw_tree(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        (
            "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
            "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
            "tx_hash,description,account,wallet\n"
        ),
        encoding="utf-8",
    )
    registry = build_registry()
    service = BuildProfileUseCase(registry, FilesystemArtifactStore())

    with pytest.raises(
        ValueError,
        match="profile output directory must not be inside raw source directory",
    ):
        service.execute(
            ProfileRequest(
                source="fixture_source",
                raw_dir=raw_dir,
                output_dir=raw_dir / "profile",
            )
        )
