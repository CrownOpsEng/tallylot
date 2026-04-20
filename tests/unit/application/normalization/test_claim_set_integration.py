from __future__ import annotations

import json
from pathlib import Path

from tallylot.application.normalization import NormalizeRequest
from tallylot.application.resource_refs import to_resource_ref
from repo_support.capture_roots import materialize_capture_root
from tests.support.adapter_packs import fixture_raw_dir
from tests.support.services import build_normalization_service


def test_coinbase_normalization_writes_claim_set_outputs_and_summary_fields(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(
        tmp_path,
        source="coinbase",
        source_dir=fixture_raw_dir("coinbase", "retail_buy_renamed"),
    )
    output_dir = tmp_path / "normalized"

    response = build_normalization_service().execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    claim_root = (
        tmp_path
        / "workspace"
        / "working"
        / "products"
        / "claim_sets"
        / response.claim_set_id
    )
    summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )

    assert response.claim_set_id
    assert summary["claim_set_id"] == response.claim_set_id
    assert summary["claim_set_ref"] == response.claim_set_ref
    assert (claim_root / "claim_set.json").exists()
    assert (claim_root / "assessment" / "gap" / "gap_records.json").exists()
    assert (claim_root / "assessment" / "review" / "review_records.json").exists()
    assert (claim_root / "compatibility" / "draft_projection_fields.json").exists()


def test_coinbase_blocked_planning_writes_no_claim_set_root(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="coinbase")
    (raw_dir / "2021 statement a.csv").write_text(
        "Transactions\nUser,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-a,2021-12-30 08:56:53 UTC,Receive,FET,1.00000000,CAD,$0.64,$1.27098,$1.27098,$0.00,Received FET\n",
        encoding="utf-8",
    )
    (raw_dir / "2021 statement b.csv").write_text(
        "Transactions\nUser,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-b,2021-12-30 08:56:53 UTC,Receive,FET,2.00000000,CAD,$0.64,$1.27098,$1.27098,$0.00,Received FET\n",
        encoding="utf-8",
    )

    try:
        build_normalization_service().execute(
            NormalizeRequest(
                source="coinbase",
                raw_capture_ref=to_resource_ref(raw_dir),
                normalized_output_ref=to_resource_ref(tmp_path / "normalized"),
            )
        )
    except ValueError:
        pass

    assert not (tmp_path / "workspace" / "working" / "products" / "claim_sets").exists()


def test_coinbase_missing_retail_input_writes_no_claim_set_root(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(
        tmp_path,
        source="coinbase",
        source_dir=fixture_raw_dir("coinbase", "missing_retail_csv"),
    )
    output_dir = tmp_path / "normalized"

    response = build_normalization_service().execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    assert response.claim_set_id == ""
    assert response.claim_set_ref == ""
    assert not (tmp_path / "workspace" / "working" / "products" / "claim_sets").exists()


def test_non_claim_set_adapter_keeps_empty_claim_fields(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(
        tmp_path,
        source="Future Broker",
        source_dir=fixture_raw_dir("wealthsimple", "broker_trade"),
    )
    output_dir = tmp_path / "normalized"

    response = build_normalization_service().execute(
        NormalizeRequest(
            source="Future Broker",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    assert response.claim_set_id == ""
    assert response.claim_set_ref == ""
