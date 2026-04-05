from __future__ import annotations

import json
from pathlib import Path

import pytest

from tallylot.application.checkpoints.balance_submission import (
    BALANCE_EVIDENCE_HEADER,
    BALANCES_HEADER,
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
    _write_rows(
        submission_root / "balances.csv",
        BALANCES_HEADER,
        (
            {
                "source": "coinbase",
                "account": "primary",
                "wallet": "primary",
                "instrument_id": "symbol:BTC@coinbase",
                "quantity": "1.25",
                "as_of_at": "2026-03-23",
                "as_of_precision": "date",
                "balance_kind": "available",
                "notes": "snapshot",
            },
        ),
    )
    _write_rows(
        submission_root / "balance_evidence.csv",
        BALANCE_EVIDENCE_HEADER,
        (
            {
                "source": "coinbase",
                "account": "primary",
                "wallet": "primary",
                "instrument_id": "symbol:BTC@coinbase",
                "quantity": "1.25",
                "as_of_at": "2026-03-23",
                "as_of_precision": "date",
                "balance_kind": "available",
                "evidence_ref": "statement.pdf#page=1",
                "notes": "evidence",
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

    artifacts = FilesystemArtifactStore()
    evidence = FilesystemEvidenceRepository()
    summary = json.loads(
        (output_root / "balance_submission_summary.json").read_text(encoding="utf-8")
    )

    assert not response.blocked
    assert response.ready_for_balance_check
    assert (
        str(
            evidence.read_balance_snapshots(output_root / "balances.csv")[0].location_id
        )
        == "coinbase:primary:primary"
    )
    assert (
        evidence.read_balance_evidence(output_root / "balance_evidence.csv")[
            0
        ].evidence_ref
        == "statement.pdf#page=1"
    )
    assert artifacts.read_rows(output_root / "balance_submission_issues.csv") == []
    assert summary["ready_for_balance_check"] is True
    assert summary["issue_count"] == 0


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

    assert response.wrote_location_inventory
    assert response.location_inventory_row_count == 2
    assert location_rows[0]["location_id"] == "ledger:account_1:wallet_1"
    assert location_rows[0]["location_kind"] == "subaccount"
    assert location_rows[0]["parent_location_id"] == "ledger:account_1"
    assert location_rows[0]["location_path"] == "account-1 / wallet-1"
    assert location_rows[0]["capture_path"] == str(submission_root)
    assert location_rows[0]["evidence_kind"] == "manual_submission"
    assert location_rows[0]["evidence_path"] == "location_inventory.csv"
    assert location_rows[1]["location_kind"] == "account"
    assert location_rows[1]["parent_location_id"] == ""
    assert location_rows[1]["location_path"] == "vault"


def test_submit_balances_blocks_and_writes_status_artifacts_for_missing_required_file(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_rows(
        submission_root / "balances.csv",
        BALANCES_HEADER,
        (
            {
                "source": "coinbase",
                "account": "primary",
                "wallet": "primary",
                "instrument_id": "symbol:BTC@coinbase",
                "quantity": "1.25",
                "as_of_at": "2026-03-23",
                "as_of_precision": "date",
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
    summary = json.loads(
        (output_root / "balance_submission_summary.json").read_text(encoding="utf-8")
    )

    assert response.blocked
    assert response.issue_count == 1
    assert issue_rows[0]["issue_kind"] == "missing_required_file"
    assert summary["blocked"] is True
    assert summary["ready_for_balance_check"] is False
    assert not (output_root / "balance_evidence.csv").exists()


def test_submit_balances_rejects_invalid_header(tmp_path: Path) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")
    (submission_root / "balances.csv").write_text(
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

    assert response.blocked
    assert issue_rows[0]["issue_kind"] == "invalid_header"


@pytest.mark.parametrize(
    ("field", "value", "expected_issue_kind"),
    (
        ("quantity", "not-a-decimal", "invalid_decimal"),
        ("as_of_precision", "hour", "invalid_precision"),
        ("as_of_at", "2026-03-23 10:00:00", "invalid_timestamp"),
        ("instrument_id", "", "missing_required_value"),
    ),
)
def test_submit_balances_rejects_invalid_required_values(
    tmp_path: Path,
    field: str,
    value: str,
    expected_issue_kind: str,
) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")
    rows = FilesystemArtifactStore().read_rows(submission_root / "balances.csv")
    rows[0][field] = value
    _write_rows(submission_root / "balances.csv", BALANCES_HEADER, tuple(rows))

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

    assert response.blocked
    assert expected_issue_kind in {row["issue_kind"] for row in issue_rows}


def test_submit_balances_rejects_duplicates_for_each_file(tmp_path: Path) -> None:
    submission_root = tmp_path / "submission" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_valid_required_files(submission_root, source="coinbase")
    balance_row = FilesystemArtifactStore().read_rows(submission_root / "balances.csv")[
        0
    ]
    evidence_row = FilesystemArtifactStore().read_rows(
        submission_root / "balance_evidence.csv"
    )[0]
    _write_rows(
        submission_root / "balances.csv",
        BALANCES_HEADER,
        (balance_row, balance_row),
    )
    _write_rows(
        submission_root / "balance_evidence.csv",
        BALANCE_EVIDENCE_HEADER,
        (evidence_row, evidence_row),
    )
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
                "identifier_value": "0x1111111111111111111111111111111111111111",
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

    assert response.blocked
    assert sum(row["issue_kind"] == "duplicate_row" for row in issue_rows) == 3


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

    assert response.blocked
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
        ),
    )
    submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )
    (submission_root / "balance_evidence.csv").unlink()

    response = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source="coinbase",
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assert response.blocked
    assert not (output_root / "balances.csv").exists()
    assert not (output_root / "balance_evidence.csv").exists()
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

    assert not response.blocked
    assert response.wrote_location_inventory is False
    assert not (output_root / "location_inventory.csv").exists()


def _write_valid_required_files(submission_root: Path, *, source: str) -> None:
    _write_rows(
        submission_root / "balances.csv",
        BALANCES_HEADER,
        (
            {
                "source": source,
                "account": "primary",
                "wallet": "primary",
                "instrument_id": f"symbol:BTC@{source}",
                "quantity": "1.25",
                "as_of_at": "2026-03-23",
                "as_of_precision": "date",
                "balance_kind": "available",
                "notes": "snapshot",
            },
        ),
    )
    _write_rows(
        submission_root / "balance_evidence.csv",
        BALANCE_EVIDENCE_HEADER,
        (
            {
                "source": source,
                "account": "primary",
                "wallet": "primary",
                "instrument_id": f"symbol:BTC@{source}",
                "quantity": "1.25",
                "as_of_at": "2026-03-23",
                "as_of_precision": "date",
                "balance_kind": "available",
                "evidence_ref": "statement.pdf#page=1",
                "notes": "evidence",
            },
        ),
    )


def _write_rows(
    path: Path,
    header: tuple[str, ...],
    rows: tuple[dict[str, str], ...],
) -> None:
    FilesystemArtifactStore().write_rows(path, header, rows)
