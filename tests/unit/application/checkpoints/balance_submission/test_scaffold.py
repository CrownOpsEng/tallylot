from __future__ import annotations

from pathlib import Path

from tallylot.application.checkpoints.balance_submission import (
    BALANCE_EVIDENCE_EXAMPLE_FILENAME,
    BALANCES_EXAMPLE_FILENAME,
    LOCATION_INVENTORY_EXAMPLE_FILENAME,
    README_FILENAME,
)
from tallylot.application.checkpoints.contracts import (
    ScaffoldBalanceSubmissionRequest,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.composition.runtime import (
    scaffold_balance_submission_use_case,
)
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_scaffold_balance_submission_creates_expected_templates(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "coinbase"

    response = scaffold_balance_submission_use_case().execute(
        ScaffoldBalanceSubmissionRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
        )
    )

    artifacts = FilesystemArtifactStore()
    assert response.source == "coinbase"
    assert (submission_root / README_FILENAME).exists()
    assert (submission_root / BALANCES_EXAMPLE_FILENAME).exists()
    assert (submission_root / BALANCE_EVIDENCE_EXAMPLE_FILENAME).exists()
    assert (submission_root / LOCATION_INVENTORY_EXAMPLE_FILENAME).exists()
    assert not (submission_root / "balances.csv").exists()
    assert not (submission_root / "balance_evidence.csv").exists()
    assert not (submission_root / "location_inventory.csv").exists()

    readme_text = (submission_root / README_FILENAME).read_text(encoding="utf-8")
    balance_rows = artifacts.read_rows(submission_root / BALANCES_EXAMPLE_FILENAME)

    assert "instrument_id" in readme_text
    assert "not guessed" in readme_text
    assert balance_rows[0]["source"] == "coinbase"
    assert balance_rows[0]["balance_kind"] == "available"
