from __future__ import annotations

from tallylot.application.evidence.location_inventory import (
    LocationInventoryBuildSpec,
    build_location_inventory_record,
)
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.locations import LocationKind
from tallylot.domain.types import CaptureUid, LocationId


def test_build_location_inventory_record_for_account_location() -> None:
    record = build_location_inventory_record(
        LocationInventoryBuildSpec(
            source="ledger",
            location_id=LocationId("ledger:main"),
            location_kind=LocationKind.ACCOUNT,
            location_label="Main",
            identifier_kind="btc_address",
            identifier_value="bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq9e75rs",
            evidence_provenance=ProvenanceLocator(
                capture_uid=CaptureUid("capture-1"),
                relative_path="location_inventory.csv",
                anchor="page=1",
            ),
            capture_uid="capture-1",
            capture_label="ledger-main",
            capture_root_ref="/workspace/raw/ledger-main",
            network_scope="",
            controller="self_custody",
            evidence_kind="manual_submission",
            confidence="high",
            notes="primary account",
        )
    )

    row = record.to_row()

    assert str(record.location_id) == "ledger:main"
    assert record.location_kind is LocationKind.ACCOUNT
    assert row["normalized_identifier"] == "bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq9e75rs"
    assert row["display_identifier"] == "bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq9e75rs"
    assert row["location_path"] == ""
    assert row["parent_location_id"] == ""
    assert row["evidence_capture_uid"] == "capture-1"
    assert row["evidence_relative_path"] == "location_inventory.csv"
    assert row["evidence_anchor"] == "page=1"


def test_build_location_inventory_record_for_subaccount_location() -> None:
    record = build_location_inventory_record(
        LocationInventoryBuildSpec(
            source="ledger",
            location_id=LocationId("ledger:account:wallet"),
            location_kind=LocationKind.SUBACCOUNT,
            location_label="Wallet",
            identifier_kind="evm_address",
            identifier_value="0x1111111111111111111111111111111111111111",
            evidence_provenance=ProvenanceLocator(
                capture_uid=CaptureUid("capture-2"),
                relative_path="wallets.csv",
            ),
            parent_location_id=LocationId("ledger:account"),
            location_path=("account", "wallet"),
            capture_uid="capture-2",
            capture_label="ledger-wallet",
            capture_root_ref="/workspace/raw/ledger-wallet",
            network_scope="ethereum",
            controller="self_custody",
            parent_location_label="Account",
            evidence_kind="manual_submission",
            confidence="medium",
            notes="subaccount",
        )
    )

    row = record.to_row()

    assert str(record.location_id) == "ledger:account:wallet"
    assert record.location_kind is LocationKind.SUBACCOUNT
    assert str(record.parent_location_id) == "ledger:account"
    assert row["location_path"] == "account / wallet"
    assert row["parent_location_label"] == "Account"
    assert row["network_scope"] == "ethereum"
    assert row["normalized_identifier"] == "0x1111111111111111111111111111111111111111"
