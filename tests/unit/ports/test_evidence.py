from __future__ import annotations

from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.locations import LocationKind
from tallylot.domain.types import CaptureUid, LocationId
from tallylot.ports.evidence import LOCATION_INVENTORY_HEADER, LocationInventoryRecord


def test_location_inventory_record_row_includes_evidence_provenance_columns() -> None:
    record = LocationInventoryRecord(
        source="binance",
        capture_uid="01HV4A5H7VJH7M3Y5A6B7C8D9E",
        capture_label="2026-03-23T14-15-16Z",
        capture_root_ref="evidence/raw/source/binance/2026-03-23T14-15-16Z",
        location_id=LocationId("binance:primary"),
        location_kind=LocationKind.ACCOUNT,
        location_label="Primary",
        identifier_kind="account_wallet",
        identifier_value="binance:primary",
        evidence_kind="normalized_transactions",
        evidence_provenance=ProvenanceLocator(
            capture_uid=CaptureUid("01HV4A5H7VJH7M3Y5A6B7C8D9E"),
            relative_path="statement.pdf",
            locator_kind="raw_file",
            anchor="page=2",
        ),
        confidence="high",
        notes="",
    )

    row = record.to_row()

    assert tuple(row.keys()) == LOCATION_INVENTORY_HEADER
    assert row["evidence_capture_uid"] == "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    assert row["evidence_relative_path"] == "statement.pdf"
    assert row["evidence_anchor"] == "page=2"
