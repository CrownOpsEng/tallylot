from __future__ import annotations

import json
from pathlib import Path

from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tools.oracles.baseline import BaselineValidationService
from tools.oracles.contracts import BaselineValidateRequest


def test_baseline_validation_service_writes_relocation_safe_artifacts(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "baseline"

    response = BaselineValidationService(FilesystemArtifactStore()).execute(
        BaselineValidateRequest(export_dir=baseline_export_dir, output_dir=output_dir)
    )

    store = FilesystemArtifactStore()
    reconciliation_rows = store.read_rows(output_dir / "baseline_exchange_reconciliation.csv")
    summary = json.loads((output_dir / "baseline_summary.json").read_text(encoding="utf-8"))

    assert response.asset_count >= 1
    assert any(row["ticker"] == "CAD" for row in reconciliation_rows)
    assert summary["latest_transaction_timestamp"] == response.latest_timestamp
    assert "max_asset_difference" in summary
    assert "ending_cad_balance" in summary
    assert output_dir.joinpath("baseline_source_activity.csv").exists()


def test_baseline_validation_emits_documented_artifact_package(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "baseline"

    BaselineValidationService(FilesystemArtifactStore()).execute(
        BaselineValidateRequest(export_dir=baseline_export_dir, output_dir=output_dir)
    )

    assert (output_dir / "baseline_asset_snapshot.csv").exists()
    assert (output_dir / "baseline_exchange_reconciliation.csv").exists()
    assert (output_dir / "baseline_negative_balances.csv").exists()
    assert (output_dir / "baseline_source_activity.csv").exists()
    assert (output_dir / "baseline_cad_flow_by_type.csv").exists()
    assert (output_dir / "baseline_cad_balance_by_exchange.csv").exists()
    assert (output_dir / "baseline_summary.json").exists()
