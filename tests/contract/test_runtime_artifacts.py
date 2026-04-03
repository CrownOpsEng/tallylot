from __future__ import annotations

import json
from pathlib import Path

from crypto_reconciliation.application.dtos import (
    BaselineValidateRequest,
    NormalizeRequest,
    ProfileRequest,
    WalletInventoryRequest,
)
from crypto_reconciliation.application.services.baseline import BaselineValidationService
from crypto_reconciliation.application.services.normalize import (
    NormalizationDependencies,
    NormalizationService,
)
from crypto_reconciliation.application.services.profile import ProfileService
from crypto_reconciliation.application.services.wallet_inventory import WalletInventoryService
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from crypto_reconciliation.infrastructure.storage import FilesystemStorage


def test_baseline_validation_emits_documented_artifact_package(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "baseline"

    BaselineValidationService(build_registry(), FilesystemArtifactStore()).execute(
        BaselineValidateRequest(export_dir=baseline_export_dir, output_dir=output_dir)
    )

    assert (output_dir / "baseline_asset_snapshot.csv").exists()
    assert (output_dir / "baseline_exchange_reconciliation.csv").exists()
    assert (output_dir / "baseline_negative_balances.csv").exists()
    assert (output_dir / "baseline_source_activity.csv").exists()
    assert (output_dir / "baseline_cad_flow_by_type.csv").exists()
    assert (output_dir / "baseline_cad_balance_by_exchange.csv").exists()
    assert (output_dir / "baseline_summary.json").exists()


def test_profile_service_emits_timezone_artifacts(
    structured_source_dir: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "profile"
    artifacts = FilesystemArtifactStore()

    ProfileService(build_registry(), artifacts).execute(
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
    registry = build_registry()

    NormalizationService(
        NormalizationDependencies(
            source_registry=registry,
            output_registry=registry,
            profile_service=ProfileService(registry, artifacts),
            storage=FilesystemStorage(),
            artifacts=artifacts,
        )
    ).execute(
        NormalizeRequest(
            source="fixture_source",
            raw_dir=structured_source_dir,
            output_dir=normalized_dir,
        )
    )

    WalletInventoryService(artifacts).execute(
        WalletInventoryRequest(normalized_root=normalized_dir, output_path=output_path)
    )

    assert output_path.exists()
    assert output_path.with_name("wallet_inventory_evidence.csv").exists()
    assert output_path.with_name("wallet_inventory_issues.csv").exists()
    assert output_path.with_name("wallet_inventory_summary.json").exists()
