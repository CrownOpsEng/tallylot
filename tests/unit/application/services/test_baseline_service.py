from __future__ import annotations

import json
from pathlib import Path

from crypto_reconciliation.application.models.baseline import BaselineValidateRequest
from crypto_reconciliation.application.services.baseline import BaselineValidationService
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_baseline_validation_service_writes_relocation_safe_artifacts(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "baseline"

    response = BaselineValidationService(build_registry(), FilesystemArtifactStore()).execute(
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
