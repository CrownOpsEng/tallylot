from __future__ import annotations

import json
from pathlib import Path

import pytest

from tallylot.application.checkpoints.balance_submission import (
    BALANCE_REFERENCES_HEADER,
    BALANCE_SNAPSHOTS_HEADER,
    LOCATION_INVENTORY_HEADER,
)
from tallylot.application.checkpoints.contracts import SubmitBalancesRequest
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.composition.runtime import submit_balances_use_case
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import FilesystemEvidenceRepository


def test_submit_balances_materializes_canonical_balance_outputs(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    artifacts = FilesystemArtifactStore()
    evidence = FilesystemEvidenceRepository()
    summary = json.loads(
        (output_root / "balance_submission_summary.json").read_text(encoding="utf-8")
    )

    assert not response.blocked
    assert response.ready_for_balance_check is True
    assert response.wrote_balance_snapshots is True
    assert response.wrote_balance_references is True
    assert response.balance_snapshot_row_count == 1
    assert response.balance_reference_row_count == 1
    assert (
        str(
            evidence.read_balance_snapshots(output_root / "balance_snapshots.csv")[
                0
            ].location_id
        )
        == "coinbase:primary:primary"
    )
    assert (
        evidence.read_balance_references(output_root / "balance_references.csv")[
            0
        ].support_ref
        == "statement.pdf#page=1"
    )
    assert artifacts.read_rows(output_root / "balance_submission_issues.csv") == []
    assert summary["ready_for_balance_check"] is True
    assert summary["wrote_balance_references"] is True


def test_submit_balances_materializes_optional_location_inventory(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "submission" / "ledger"
    output_root = tmp_path / "normalized" / "ledger"
    _write_valid_required_files(submission_root, source="ledger")
    _write_rows(
        submission_root / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (
            {
                "source": "ledger",
                "account": "account-1",
                "wallet": "wallet-1",
                "identifier_kind": "evm_address",
                "identifier_value": "0x1111111111111111111111111111111111111111",
                "network_scope": "ethereum",
                "controller": "self_custody",
                "confidence": "high",
                "notes": "wallet identity",
            },
            {
                "source": "ledger",
                "account": "vault",
                "wallet": "vault",
                "identifier_kind": "btc_address",
                "identifier_value": "bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq9e75rs",
                "network_scope": "",
                "controller": "self_custody",
                "confidence": "medium",
                "notes": "account level",
            },
        ),
    )

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="ledger",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    location_rows = FilesystemArtifactStore().read_rows(
        output_root / "location_inventory.csv"
    )

    assert response.wrote_location_inventory is True
    assert response.location_inventory_row_count == 2
    assert location_rows[0]["location_id"] == "ledger:account_1:wallet_1"
    assert location_rows[0]["location_kind"] == "subaccount"
    assert location_rows[0]["parent_location_id"] == "ledger:account_1"
    assert location_rows[0]["location_path"] == "account-1 / wallet-1"
    assert location_rows[0]["capture_root_ref"] == str(submission_root)
    assert location_rows[0]["evidence_kind"] == "manual_submission"
    assert location_rows[0]["evidence_relative_path"] == "location_inventory.csv"
    assert location_rows[1]["location_kind"] == "account"
    assert location_rows[1]["parent_location_id"] == ""
    assert location_rows[1]["location_path"] == "vault"


def test_submit_balances_blocks_when_reference_file_is_missing(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_rows(
        submission_root / "balance_snapshots.csv",
        BALANCE_SNAPSHOTS_HEADER,
        (
            {
                "source": "coinbase",
                "account": "primary",
                "wallet": "primary",
                "instrument_id": "symbol:BTC@coinbase",
                "quantity": "1.25",
                "target_at": "2026-03-23",
                "target_precision": "date",
                "balance_kind": "available",
                "notes": "",
            },
        ),
    )

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    issue_rows = FilesystemArtifactStore().read_rows(
        output_root / "balance_submission_issues.csv"
    )

    assert response.blocked is True
    assert response.issue_count >= 1
    assert issue_rows[0]["issue_kind"] == "missing_required_file"
    assert not (output_root / "balance_references.csv").exists()


def test_submit_balances_rejects_invalid_header(tmp_path: Path) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")
    (submission_root / "balance_references.csv").write_text(
        "source,wallet,instrument_id\ncoinbase,primary,symbol:BTC@coinbase\n",
        encoding="utf-8",
    )

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    issue_rows = FilesystemArtifactStore().read_rows(
        output_root / "balance_submission_issues.csv"
    )

    assert response.blocked is True
    assert issue_rows[0]["issue_kind"] == "invalid_header"


@pytest.mark.parametrize(
    ("field", "value", "expected_issue_kind"),
    (
        ("quantity", "not-a-decimal", "invalid_decimal"),
        ("target_precision", "hour", "invalid_precision"),
        ("target_at", "2026-03-23 10:00:00", "invalid_timestamp"),
        ("instrument_id", "", "missing_required_value"),
    ),
)
def test_submit_balances_rejects_invalid_balance_values(
    tmp_path: Path,
    field: str,
    value: str,
    expected_issue_kind: str,
) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")
    rows = FilesystemArtifactStore().read_rows(
        submission_root / "balance_snapshots.csv"
    )
    rows[0][field] = value
    _write_rows(
        submission_root / "balance_snapshots.csv",
        BALANCE_SNAPSHOTS_HEADER,
        tuple(rows),
    )

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    issue_rows = FilesystemArtifactStore().read_rows(
        output_root / "balance_submission_issues.csv"
    )

    assert response.blocked is True
    assert expected_issue_kind in {row["issue_kind"] for row in issue_rows}


@pytest.mark.parametrize(
    ("field", "value", "expected_issue_kind"),
    (
        ("reference_kind", "unsupported_kind", "invalid_reference_kind"),
        ("reference_kind", "manual_assertion", "invalid_reference_kind"),
        ("reviewed_at", "2026-03-24", "invalid_timestamp"),
        ("reviewed_by", "", "missing_required_value"),
    ),
)
def test_submit_balances_rejects_invalid_reference_values(
    tmp_path: Path,
    field: str,
    value: str,
    expected_issue_kind: str,
) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")
    rows = FilesystemArtifactStore().read_rows(
        submission_root / "balance_references.csv"
    )
    rows[0][field] = value
    _write_rows(
        submission_root / "balance_references.csv",
        BALANCE_REFERENCES_HEADER,
        tuple(rows),
    )

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    issue_rows = FilesystemArtifactStore().read_rows(
        output_root / "balance_submission_issues.csv"
    )

    assert response.blocked is True
    assert expected_issue_kind in {row["issue_kind"] for row in issue_rows}


def test_submit_balances_rejects_missing_matching_reference_row(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")
    _write_rows(
        submission_root / "balance_references.csv",
        BALANCE_REFERENCES_HEADER,
        (),
    )

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    issue_rows = FilesystemArtifactStore().read_rows(
        output_root / "balance_submission_issues.csv"
    )

    assert response.blocked is True
    assert "missing_matching_reference" in {row["issue_kind"] for row in issue_rows}


def test_submit_balances_rejects_orphan_reference_row(tmp_path: Path) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")
    rows = FilesystemArtifactStore().read_rows(
        submission_root / "balance_references.csv"
    )
    rows.append(
        {
            **rows[0],
            "wallet": "secondary",
            "support_ref": "statement-2.pdf#page=1",
        }
    )
    _write_rows(
        submission_root / "balance_references.csv",
        BALANCE_REFERENCES_HEADER,
        tuple(rows),
    )

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    issue_rows = FilesystemArtifactStore().read_rows(
        output_root / "balance_submission_issues.csv"
    )

    assert response.blocked is True
    assert "orphan_reference" in {row["issue_kind"] for row in issue_rows}


def test_submit_balances_rejects_conflicting_high_confidence_location_identity(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")
    _write_rows(
        submission_root / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (
            {
                "source": "coinbase",
                "account": "primary",
                "wallet": "primary",
                "identifier_kind": "evm_address",
                "identifier_value": "0x1111111111111111111111111111111111111111",
                "network_scope": "ethereum",
                "controller": "self_custody",
                "confidence": "high",
                "notes": "",
            },
            {
                "source": "coinbase",
                "account": "primary",
                "wallet": "primary",
                "identifier_kind": "evm_address",
                "identifier_value": "0x2222222222222222222222222222222222222222",
                "network_scope": "ethereum",
                "controller": "self_custody",
                "confidence": "high",
                "notes": "",
            },
        ),
    )

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    issue_rows = FilesystemArtifactStore().read_rows(
        output_root / "balance_submission_issues.csv"
    )

    assert response.blocked is True
    assert issue_rows[0]["issue_kind"] == "conflicting_high_confidence_identity"


def test_submit_balances_rejects_output_inside_submission_root(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")

    with pytest.raises(
        ValueError,
        match="balance submission output root must not be inside balance submission root",
    ):
        submit_balances_use_case().execute(
            SubmitBalancesRequest(
                source="coinbase",
                submission_root_ref=to_resource_ref(submission_root),
                output_root_ref=to_resource_ref(submission_root / "normalized"),
            )
        )


def test_submit_balances_clears_stale_outputs_when_rerun_blocks(tmp_path: Path) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")
    submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )
    (output_root / "balance_assertions.csv").write_text("stale\n", encoding="utf-8")
    (submission_root / "balance_references.csv").unlink()

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assert response.blocked is True
    assert (output_root / "balance_snapshots.csv").exists()
    assert (output_root / "balance_references.csv").exists()
    assert (output_root / "balance_assertions.csv").exists()
    assert not (output_root / "location_inventory.csv").exists()


def test_submit_balances_clears_stale_outputs_when_submission_root_is_missing(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")
    submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )
    (submission_root / "balance_snapshots.csv").unlink()
    (submission_root / "balance_references.csv").unlink()
    submission_root.rmdir()

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assert response.blocked is True
    assert (output_root / "balance_snapshots.csv").exists()
    assert (output_root / "balance_references.csv").exists()
    assert not (output_root / "location_inventory.csv").exists()


def test_submit_balances_clears_stale_optional_location_inventory_on_rerun(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")
    location_inventory_path = submission_root / "location_inventory.csv"
    _write_rows(
        location_inventory_path,
        LOCATION_INVENTORY_HEADER,
        (
            {
                "source": "coinbase",
                "account": "primary",
                "wallet": "primary",
                "identifier_kind": "evm_address",
                "identifier_value": "0x1111111111111111111111111111111111111111",
                "network_scope": "ethereum",
                "controller": "self_custody",
                "confidence": "high",
                "notes": "",
            },
        ),
    )
    submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )
    location_inventory_path.unlink()

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assert response.blocked is False
    assert response.wrote_location_inventory is False
    assert (output_root / "location_inventory.csv").exists()


def _write_valid_required_files(submission_root: Path, *, source: str) -> None:
    _write_rows(
        submission_root / "balance_snapshots.csv",
        BALANCE_SNAPSHOTS_HEADER,
        (
            {
                "source": source,
                "account": "primary",
                "wallet": "primary",
                "instrument_id": f"symbol:BTC@{source}",
                "quantity": "1.25",
                "target_at": "2026-03-23",
                "target_precision": "date",
                "balance_kind": "available",
                "notes": "snapshot",
            },
        ),
    )
    _write_rows(
        submission_root / "balance_references.csv",
        BALANCE_REFERENCES_HEADER,
        (
            {
                "source": source,
                "account": "primary",
                "wallet": "primary",
                "instrument_id": f"symbol:BTC@{source}",
                "quantity": "1.25",
                "target_at": "2026-03-23",
                "target_precision": "date",
                "balance_kind": "available",
                "reference_kind": "operator_assertion",
                "observed_at": "2026-03-23",
                "observed_precision": "date",
                "support_ref": "statement.pdf#page=1",
                "reviewed_by": "operator@example.com",
                "reviewed_at": "2026-03-24 00:00:00",
                "notes": "confirmation",
            },
        ),
    )


def _write_rows(
    path: Path,
    header: tuple[str, ...],
    rows: tuple[dict[str, str], ...],
) -> None:
    FilesystemArtifactStore().write_rows(path, header, rows)
