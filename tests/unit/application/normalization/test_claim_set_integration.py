from __future__ import annotations

import json
from pathlib import Path

from tallylot.application.claim.contracts import CoinbaseClaimBuildResult
from tallylot.application.normalization import NormalizeRequest
from tallylot.application.normalization.translation import (
    _write_claim_assessment_sidecars,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.assessment import (
    GapConfidence,
    GapExplanation,
    GapKind,
    GapMateriality,
    GapRecord,
    GapStatus,
    ReviewConfidence,
    ReviewExplanation,
    ReviewRecord,
    ReviewStatus,
)
from tallylot.domain.claim import ClaimSet
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
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


def test_claim_assessment_sidecars_write_in_canonical_order(tmp_path: Path) -> None:
    _write_claim_assessment_sidecars(
        artifacts=FilesystemArtifactStore(),
        workspace_root=tmp_path,
        claim_set_id="claim-set-1",
        claim_build=CoinbaseClaimBuildResult(
            claim_set=ClaimSet(
                claim_set_id="claim-set-1",
                evidence_set_ref="evidence-set-1",
                emitter_id="coinbase:coinbase:claim",
                claim_records=(),
                claim_bundle_records=(),
                claim_bundle_decision_records=(),
            ),
            gap_records=(
                GapRecord(
                    gap_id="gap-2",
                    owner_stage="claim",
                    blocking_stages=("economics",),
                    scope_kind="claim_scope",
                    scope_ref="scope-2",
                    subject_ref=None,
                    gap_kind=GapKind.CONTRADICTION,
                    gap_key="contradiction",
                    status=GapStatus.OPEN,
                    materiality=GapMateriality.MATERIAL,
                    confidence=GapConfidence.LOW,
                ),
                GapRecord(
                    gap_id="gap-1",
                    owner_stage="claim",
                    blocking_stages=("claim",),
                    scope_kind="claim_scope",
                    scope_ref="scope-1",
                    subject_ref=None,
                    gap_kind=GapKind.MISSING_EVIDENCE,
                    gap_key="missing",
                    status=GapStatus.OPEN,
                    materiality=GapMateriality.SUPPORTING,
                    confidence=GapConfidence.HIGH,
                ),
            ),
            gap_explanations=(
                GapExplanation(
                    gap_id="gap-2",
                    known_facts=("fact-2",),
                    missing_inputs=(),
                    possible_meanings=(),
                    required_evidence=(),
                    resolution_options=(),
                    next_action="review",
                    provenance_refs=("prov-2",),
                ),
                GapExplanation(
                    gap_id="gap-1",
                    known_facts=("fact-1",),
                    missing_inputs=(),
                    possible_meanings=(),
                    required_evidence=(),
                    resolution_options=(),
                    next_action="review",
                    provenance_refs=("prov-1",),
                ),
            ),
            review_records=(
                ReviewRecord(
                    review_id="review-2",
                    owner_stage="claim",
                    scope_kind="claim_scope",
                    scope_ref="scope-2",
                    subject_ref=None,
                    review_kind="mapping",
                    review_key="second",
                    status=ReviewStatus.OPEN,
                    confidence=ReviewConfidence.LOW,
                    gap_ids=(),
                ),
                ReviewRecord(
                    review_id="review-1",
                    owner_stage="claim",
                    scope_kind="claim_scope",
                    scope_ref="scope-1",
                    subject_ref=None,
                    review_kind="mapping",
                    review_key="first",
                    status=ReviewStatus.ACKNOWLEDGED,
                    confidence=ReviewConfidence.HIGH,
                    gap_ids=("gap-b", "gap-a"),
                ),
            ),
            review_explanations=(
                ReviewExplanation(
                    review_id="review-2",
                    headline="Second",
                    known_facts=("fact-2",),
                    follow_up=(),
                    provenance_refs=("prov-2",),
                ),
                ReviewExplanation(
                    review_id="review-1",
                    headline="First",
                    known_facts=("fact-1",),
                    follow_up=(),
                    provenance_refs=("prov-1",),
                ),
            ),
            draft_projection_field_records=(),
            compatibility_issue_records=(),
            compatibility_review_records=(),
        ),
    )

    claim_root = tmp_path / "working" / "products" / "claim_sets" / "claim-set-1"
    gap_records_payload = json.loads(
        (claim_root / "assessment" / "gap" / "gap_records.json").read_text(
            encoding="utf-8"
        )
    )
    gap_explanations_payload = json.loads(
        (claim_root / "assessment" / "gap" / "gap_explanations.json").read_text(
            encoding="utf-8"
        )
    )
    review_records_payload = json.loads(
        (claim_root / "assessment" / "review" / "review_records.json").read_text(
            encoding="utf-8"
        )
    )
    review_explanations_payload = json.loads(
        (claim_root / "assessment" / "review" / "review_explanations.json").read_text(
            encoding="utf-8"
        )
    )

    assert [item["gap_id"] for item in gap_records_payload] == ["gap-1", "gap-2"]
    assert [item["gap_id"] for item in gap_explanations_payload] == ["gap-1", "gap-2"]
    assert [item["review_id"] for item in review_records_payload] == [
        "review-1",
        "review-2",
    ]
    assert [item["review_id"] for item in review_explanations_payload] == [
        "review-1",
        "review-2",
    ]
