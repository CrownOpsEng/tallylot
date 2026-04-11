from __future__ import annotations

from pathlib import Path

from tallylot.application.checkpoints.balance_submission import (
    BALANCE_REFERENCES_EXAMPLE_FILENAME,
    BALANCE_SNAPSHOTS_EXAMPLE_FILENAME,
    LOCATION_INVENTORY_EXAMPLE_FILENAME,
    README_FILENAME,
)
from tallylot.application.checkpoints.contracts import ScaffoldBalanceSubmissionRequest
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
    assert (submission_root / BALANCE_SNAPSHOTS_EXAMPLE_FILENAME).exists()
    assert (submission_root / BALANCE_REFERENCES_EXAMPLE_FILENAME).exists()
    assert (submission_root / LOCATION_INVENTORY_EXAMPLE_FILENAME).exists()
    assert not (submission_root / "balance_snapshots.csv").exists()
    assert not (submission_root / "balance_references.csv").exists()
    assert not (submission_root / "location_inventory.csv").exists()

    readme_text = (submission_root / README_FILENAME).read_text(encoding="utf-8")
    balance_rows = artifacts.read_rows(
        submission_root / BALANCE_SNAPSHOTS_EXAMPLE_FILENAME
    )
    reference_rows = artifacts.read_rows(
        submission_root / BALANCE_REFERENCES_EXAMPLE_FILENAME
    )

    assert "instrument_id" in readme_text
    assert "not guessed" in readme_text
    assert "do not create" in readme_text
    assert balance_rows[0]["source"] == "coinbase"
    assert balance_rows[0]["balance_kind"] == "available"
    assert reference_rows[0]["reference_kind"] == "operator_assertion"
    assert reference_rows[0]["reviewed_at"] == "2026-03-24 00:00:00"


def test_scaffold_balance_submission_uses_source_specific_example_ids(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "ledger"

    scaffold_balance_submission_use_case().execute(
        ScaffoldBalanceSubmissionRequest(
            source="ledger",
            submission_root_ref=to_resource_ref(submission_root),
        )
    )

    artifacts = FilesystemArtifactStore()
    balance_rows = artifacts.read_rows(
        submission_root / BALANCE_SNAPSHOTS_EXAMPLE_FILENAME
    )
    reference_rows = artifacts.read_rows(
        submission_root / BALANCE_REFERENCES_EXAMPLE_FILENAME
    )

    assert balance_rows[0]["instrument_id"] == "symbol:BTC@ledger"
    assert reference_rows[0]["instrument_id"] == "symbol:BTC@ledger"
