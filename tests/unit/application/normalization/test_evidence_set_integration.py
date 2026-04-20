from __future__ import annotations

import json
from pathlib import Path

import pytest

from tallylot.application.normalization import NormalizeRequest
from tallylot.application.resource_refs import to_resource_ref
from repo_support.capture_roots import materialize_capture_root
from tests.support.services import build_normalization_service


def test_coinbase_normalization_writes_evidence_set_product_outputs(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="coinbase")
    (raw_dir / "2026-03-23 Statement - All Time.csv").write_text(
        _coinbase_retail_csv(),
        encoding="utf-8",
    )
    output_dir = tmp_path / "normalized"

    response = build_normalization_service().execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    evidence_root = (
        tmp_path
        / "workspace"
        / "working"
        / "products"
        / "evidence_sets"
        / response.evidence_set_id
    )
    evidence_payload = json.loads(
        (evidence_root / "evidence_set.json").read_text(encoding="utf-8")
    )
    capture_payload = json.loads((raw_dir / "capture.json").read_text(encoding="utf-8"))
    compatibility_payload = json.loads(
        (evidence_root / "compatibility" / "translation_input_plan.json").read_text(
            encoding="utf-8"
        )
    )
    profile_payload = json.loads(
        (output_dir / "profile.json").read_text(encoding="utf-8")
    )
    summary_payload = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )

    assert response.evidence_set_id
    assert response.evidence_set_ref == (
        f"working/products/evidence_sets/{response.evidence_set_id}/evidence_set.json"
    )
    assert evidence_payload["evidence_set_id"] == response.evidence_set_id
    assert (
        evidence_payload["capture_manifest_fingerprint"]
        == (capture_payload["manifest_fingerprint"])
    )
    assert (
        evidence_payload["capture_manifest_fingerprint"]
        != (profile_payload["manifest_fingerprint"])
    )
    assert compatibility_payload == json.loads(
        (output_dir / "translation_input_plan.json").read_text(encoding="utf-8")
    )
    assert summary_payload["evidence_set_id"] == response.evidence_set_id
    assert summary_payload["evidence_set_ref"] == response.evidence_set_ref


def test_coinbase_blocked_normalization_leaves_evidence_set_product_outputs(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="coinbase")
    (raw_dir / "2021 statement a.csv").write_text(
        _coinbase_retail_csv_with_amount("tx-a", "1.00000000"),
        encoding="utf-8",
    )
    (raw_dir / "2021 statement b.csv").write_text(
        _coinbase_retail_csv_with_amount("tx-b", "2.00000000"),
        encoding="utf-8",
    )
    output_dir = tmp_path / "normalized"

    with pytest.raises(
        ValueError, match="translation input planning blocked normalization"
    ):
        build_normalization_service().execute(
            NormalizeRequest(
                source="coinbase",
                raw_capture_ref=to_resource_ref(raw_dir),
                normalized_output_ref=to_resource_ref(output_dir),
            )
        )

    evidence_roots = tuple(
        sorted(
            (
                tmp_path / "workspace" / "working" / "products" / "evidence_sets"
            ).iterdir()
        )
    )

    assert len(evidence_roots) == 1
    assert (evidence_roots[0] / "evidence_set.json").exists()
    assert (
        evidence_roots[0] / "compatibility" / "translation_input_plan.json"
    ).exists()
    assert (output_dir / "translation_input_candidates.json").exists()
    assert (output_dir / "translation_input_plan.json").exists()
    assert (output_dir / "translation_input_issues.csv").exists()
    assert not (output_dir / "facts.csv").exists()
    assert not (output_dir / "normalization_summary.json").exists()


def _coinbase_retail_csv() -> str:
    return (
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,"
        "Price at Transaction,Subtotal,Total (inclusive of fees and/or spread),"
        "Fees and/or Spread,Notes\n"
        "legacy-1,2021-12-30 08:56:53 UTC,Receive,FET,1.9859001,CAD,$0.64,"
        "$1.27098,$1.27098,$0.00,Received 1.9859001 FET\n"
    )


def _coinbase_retail_csv_with_amount(transaction_id: str, amount: str) -> str:
    return (
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,"
        "Price at Transaction,Subtotal,Total (inclusive of fees and/or spread),"
        "Fees and/or Spread,Notes\n"
        f"{transaction_id},2021-12-30 08:56:53 UTC,Receive,FET,{amount},CAD,$0.64,"
        f"${amount},${amount},$0.00,Received {amount} FET\n"
    )
