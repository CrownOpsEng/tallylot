from __future__ import annotations

import json
from pathlib import Path

from tallylot.application.checkpoints import RebuildWalletInventoryUseCase, WalletInventoryRequest
from tallylot.application.normalization import NormalizeRequest
from tallylot.application.profiling import BuildProfileUseCase, ProfileRequest
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tests.support.services import build_normalization_service


def test_profile_service_emits_timezone_artifacts(
    structured_source_dir: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "profile"
    artifacts = FilesystemArtifactStore()

    BuildProfileUseCase(build_registry(), artifacts).execute(
        ProfileRequest(
            source="fixture_source",
            raw_dir=structured_source_dir,
            output_dir=output_dir,
        )
    )

    profile_json = json.loads((output_dir / "profile.json").read_text(encoding="utf-8"))
    inventory_rows = artifacts.read_rows(output_dir / "profile_inventory.csv")

    assert "timezone_summary" in profile_json
    assert "timestamp_resolution" in inventory_rows[0]
    assert "timezone_mode" in inventory_rows[0]
    assert (output_dir / "timezone_issues.csv").exists()


def test_wallet_inventory_rebuild_emits_documented_outputs(
    structured_source_dir: Path,
    tmp_path: Path,
) -> None:
    normalized_dir = tmp_path / "normalized"
    output_path = tmp_path / "wallet_inventory.csv"
    artifacts = FilesystemArtifactStore()

    build_normalization_service(artifacts=artifacts).execute(
        NormalizeRequest(
            source="fixture_source",
            raw_dir=structured_source_dir,
            output_dir=normalized_dir,
        )
    )

    RebuildWalletInventoryUseCase(artifacts).execute(
        WalletInventoryRequest(normalized_root=normalized_dir, output_path=output_path)
    )

    assert output_path.exists()
    assert output_path.with_name("wallet_inventory_evidence.csv").exists()
    assert output_path.with_name("wallet_inventory_issues.csv").exists()
    assert output_path.with_name("wallet_inventory_summary.json").exists()


def test_normalization_emits_fact_and_balance_artifacts(
    structured_source_dir: Path,
    tmp_path: Path,
) -> None:
    normalized_dir = tmp_path / "normalized"

    build_normalization_service(artifacts=FilesystemArtifactStore()).execute(
        NormalizeRequest(
            source="fixture_source",
            raw_dir=structured_source_dir,
            output_dir=normalized_dir,
        )
    )

    assert (normalized_dir / "facts.csv").exists()
    assert (normalized_dir / "balances.csv").exists()
    assert (normalized_dir / "balance_evidence.csv").exists()
