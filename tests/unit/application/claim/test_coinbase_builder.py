from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from tallylot.adapters.sources.platforms.coinbase.adapter import _CoinbaseAdapter
from tallylot.application.claim import (
    CoinbaseClaimBuildResult,
    build_coinbase_claim_set,
)
from tallylot.application.evidence.evidence_sets import build_evidence_set_for_profile
from tallylot.application.evidence.statement_extraction import (
    StatementExtractionService,
)
from tallylot.application.normalization.translation_inputs import (
    plan_translation_inputs,
)
from tallylot.application.profiling import BuildProfileUseCase
from tallylot.domain.claim import ClaimBundleDecisionOutcome, ClaimKind
from tallylot.domain.claim.models import claim_set_fingerprint
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.source_profiles import SourceProfile


def _coinbase_profile(raw_dir: Path) -> SourceProfile:
    return BuildProfileUseCase(
        build_registry(), FilesystemArtifactStore()
    ).create_profile(
        "coinbase",
        raw_dir,
    )


def _make_pdf(path: Path, *lines: str) -> None:
    pdf = canvas.Canvas(str(path))
    y = 750
    for line in lines:
        pdf.drawString(72, y, line)
        y -= 15
    pdf.save()


def _retail_csv(*rows: str) -> str:
    return (
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,"
        "Price at Transaction,Subtotal,Total (inclusive of fees and/or spread),"
        "Fees and/or Spread,Notes\n"
        f"{''.join(rows)}"
    )


def _build_claim_result(raw_dir: Path) -> CoinbaseClaimBuildResult | None:
    registry = build_registry()
    adapter = _CoinbaseAdapter()
    profile = _coinbase_profile(raw_dir)
    planning_result = plan_translation_inputs(
        profile=profile,
        candidates=adapter.describe_translation_inputs(profile, raw_dir),
    )
    statement_documents = StatementExtractionService(
        registry
    ).collect_source_statement_documents(profile, raw_dir)
    evidence_set = build_evidence_set_for_profile(
        profile=profile,
        capture_uid="capture-1",
        capture_manifest_fingerprint="manifest-1",
        planner_result=planning_result,
        statement_documents=statement_documents,
    )
    if planning_result.plan.blocked:
        batch = adapter.translate_selected_inputs(
            profile, raw_dir, planning_result.plan
        )
        assert evidence_set is not None
        return build_coinbase_claim_set(
            profile=profile,
            evidence_set=evidence_set,
            evidence_set_ref=f"working/products/evidence_sets/{evidence_set.evidence_set_id}/evidence_set.json",
            planning_result=planning_result,
            batch=batch,
        )
    if evidence_set is None:
        batch = adapter.translate_selected_inputs(
            profile, raw_dir, planning_result.plan
        )
        return build_coinbase_claim_set(
            profile=profile,
            evidence_set=None,
            evidence_set_ref="",
            planning_result=planning_result,
            batch=batch,
        )
    batch = adapter.translate_selected_inputs(profile, raw_dir, planning_result.plan)
    return build_coinbase_claim_set(
        profile=profile,
        evidence_set=evidence_set,
        evidence_set_ref=f"working/products/evidence_sets/{evidence_set.evidence_set_id}/evidence_set.json",
        planning_result=planning_result,
        batch=batch,
    )


def _claim_kinds(result: CoinbaseClaimBuildResult) -> tuple[str, ...]:
    assert result is not None
    return tuple(claim.kind.value for claim in result.claim_set.claim_records)


def test_buy_row_builds_expected_claim_bundle(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        _retail_csv(
            "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
            "Bought 0.01 BTC for 610 CAD\n"
        ),
        encoding="utf-8",
    )

    result = _build_claim_result(raw_dir)

    assert result is not None
    assert _claim_kinds(result) == (
        "activity",
        "beneficial_owner",
        "instrument",
        "instrument",
        "location",
    )
    assert (
        result.claim_set.claim_bundle_decision_records[0].outcome
        is ClaimBundleDecisionOutcome.ACCEPTED
    )
    assert len(result.draft_projection_field_records) == 1
    assert not result.gap_records
    assert not result.review_records


def test_sell_row_builds_expected_claim_bundle(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        _retail_csv(
            "tx-sell,2024-02-08 16:31:22 UTC,Sell,BTC,0.01000000,CAD,$60000.00,$600.00,$590.00,$10.00,"
            "Sold 0.01 BTC for 590 CAD\n"
        ),
        encoding="utf-8",
    )

    result = _build_claim_result(raw_dir)

    assert result is not None
    activity_claim = next(
        claim
        for claim in result.claim_set.claim_records
        if claim.kind is ClaimKind.ACTIVITY
    )
    assert activity_claim.activity_label == "sell"
    assert len(activity_claim.leg_specs) == 3


def test_reward_income_row_builds_expected_claim_bundle(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        _retail_csv(
            "reward-1,2023-03-18 01:28:49 UTC,Reward Income,ADA,0.000021,CAD,$0.48,$0.00,$0.00,$0.00,"
            "Received 0.000021 ADA from Coinbase Rewards\n"
        ),
        encoding="utf-8",
    )

    result = _build_claim_result(raw_dir)

    assert result is not None
    activity_claim = next(
        claim
        for claim in result.claim_set.claim_records
        if claim.kind is ClaimKind.ACTIVITY
    )
    assert activity_claim.activity_label == "reward_income"
    assert len(activity_claim.leg_specs) == 1


def test_receive_row_builds_expected_claim_bundle(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        _retail_csv(
            "tx-receive,2024-02-09 10:00:00 UTC,Receive,ETH,1.50000000,CAD,$0.00,$0.00,$0.00,$0.00,"
            "Received ETH\n"
        ),
        encoding="utf-8",
    )

    result = _build_claim_result(raw_dir)

    assert result is not None
    activity_claim = next(
        claim
        for claim in result.claim_set.claim_records
        if claim.kind is ClaimKind.ACTIVITY
    )
    assert activity_claim.activity_label == "receive"


def test_send_row_builds_expected_claim_bundle(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        _retail_csv(
            "tx-send,2024-02-08 17:31:22 UTC,Send,ETH,-0.50000000,CAD,$0.00,$0.00,$0.00,$0.00,"
            "Sent ETH\n"
        ),
        encoding="utf-8",
    )

    result = _build_claim_result(raw_dir)

    assert result is not None
    activity_claim = next(
        claim
        for claim in result.claim_set.claim_records
        if claim.kind is ClaimKind.ACTIVITY
    )
    assert activity_claim.activity_label == "send"


def test_asset_migration_rows_build_expected_claim_bundle(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        _retail_csv(
            "migration-neg,2025-10-17 13:38:17 UTC,Asset Migration,MATIC,-1.65526374,CAD,$0.25,-$0.42,-$0.42,$0.00,\n"
            "migration-pos,2025-10-17 13:38:17 UTC,Asset Migration,POL,1.65526374,CAD,$0.25,$0.42,$0.42,$0.00,\n"
        ),
        encoding="utf-8",
    )

    result = _build_claim_result(raw_dir)

    assert result is not None
    activity_claim = next(
        claim
        for claim in result.claim_set.claim_records
        if claim.kind is ClaimKind.ACTIVITY
    )
    assert activity_claim.activity_label == "asset_migration"
    assert tuple(spec.role for spec in activity_claim.leg_specs) == (
        "asset_in",
        "asset_out",
    )
    assert (
        result.draft_projection_field_records[0].description
        == "Coinbase Asset Migration"
    )


def test_statement_row_builds_balance_claims_when_retail_is_selected(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        _retail_csv(
            "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
            "Bought 0.01 BTC for 610 CAD\n"
        ),
        encoding="utf-8",
    )
    _make_pdf(
        raw_dir / "statement.pdf",
        "Coinbase Canada, Inc.",
        "Transaction History Report",
        "Closing Balance as of 2026-03-22 23:59:59 UTC 0 CAD",
        "Portfolio summary balances are as of 2026-03-22 23:59:59 UTC",
        "ETH 0.001181807820874 N/A 2,817.007569 CAD/ETH 3.33 CAD",
    )

    result = _build_claim_result(raw_dir)

    assert result is not None
    balance_claim = next(
        claim
        for claim in result.claim_set.claim_records
        if claim.kind is ClaimKind.BALANCE
    )
    location_claim = next(
        claim
        for claim in result.claim_set.claim_records
        if claim.kind is ClaimKind.LOCATION and claim.location_group_label == "Coinbase"
    )
    assert len(balance_claim.observation_refs) == 2
    assert balance_claim.balance_kind in {"asset_balance", "cash_closing_balance"}
    assert location_claim.location_label in {"Coinbase", "Coinbase Cash"}


def test_unsupported_selected_row_creates_blocked_claim_scope_and_compatibility_issue(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        _retail_csv(
            "tx-unsupported,2024-02-10 12:00:00 UTC,Convert,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
            "Unsupported convert row\n"
        ),
        encoding="utf-8",
    )

    result = _build_claim_result(raw_dir)

    assert result is not None
    assert not result.claim_set.claim_records
    assert (
        result.claim_set.claim_bundle_decision_records[0].outcome
        is ClaimBundleDecisionOutcome.BLOCKED
    )
    assert len(result.gap_records) == 1
    assert len(result.compatibility_issue_records) == 1


def test_no_selected_candidate_yields_no_claim_set(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    assert _build_claim_result(raw_dir) is None


def test_nested_selected_retail_file_still_builds_claims(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    nested_dir = raw_dir / "nested"
    nested_dir.mkdir(parents=True)
    (nested_dir / "retail.csv").write_text(
        _retail_csv(
            "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
            "Bought 0.01 BTC for 610 CAD\n"
        ),
        encoding="utf-8",
    )

    result = _build_claim_result(raw_dir)

    assert result is not None
    assert any(
        claim.kind is ClaimKind.ACTIVITY for claim in result.claim_set.claim_records
    )


def test_claim_builder_rejects_unmapped_selected_draft_raw_file(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        _retail_csv(
            "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
            "Bought 0.01 BTC for 610 CAD\n"
        ),
        encoding="utf-8",
    )
    registry = build_registry()
    adapter = _CoinbaseAdapter()
    profile = _coinbase_profile(raw_dir)
    planning_result = plan_translation_inputs(
        profile=profile,
        candidates=adapter.describe_translation_inputs(profile, raw_dir),
    )
    statement_documents = StatementExtractionService(
        registry
    ).collect_source_statement_documents(profile, raw_dir)
    evidence_set = build_evidence_set_for_profile(
        profile=profile,
        capture_uid="capture-1",
        capture_manifest_fingerprint="manifest-1",
        planner_result=planning_result,
        statement_documents=statement_documents,
    )
    assert evidence_set is not None
    batch = adapter.translate_selected_inputs(profile, raw_dir, planning_result.plan)
    broken_batch = replace(
        batch,
        drafts=(replace(batch.drafts[0], raw_file="missing-retail.csv"),),
    )

    with pytest.raises(
        ValueError,
        match="claim builder could not map draft raw_file 'missing-retail.csv'",
    ):
        build_coinbase_claim_set(
            profile=profile,
            evidence_set=evidence_set,
            evidence_set_ref=(
                f"working/products/evidence_sets/{evidence_set.evidence_set_id}/"
                "evidence_set.json"
            ),
            planning_result=planning_result,
            batch=broken_batch,
        )


def test_replay_with_unchanged_evidence_preserves_payload_and_fingerprint(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        _retail_csv(
            "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
            "Bought 0.01 BTC for 610 CAD\n"
        ),
        encoding="utf-8",
    )

    first = _build_claim_result(raw_dir)
    second = _build_claim_result(raw_dir)

    assert first is not None and second is not None
    assert first.claim_set.to_payload() == second.claim_set.to_payload()
    assert claim_set_fingerprint(first.claim_set) == claim_set_fingerprint(
        second.claim_set
    )


def test_inventory_order_changes_do_not_change_claim_payload_or_fingerprint(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "older.csv").write_text(
        _retail_csv(
            "legacy-1,2021-12-30 08:56:53 UTC,Receive,FET,1.9859001,CAD,$0.64,$1.27098,$1.27098,$0.00,"
            "Received 1.9859001 FET\n"
        ),
        encoding="utf-8",
    )
    (raw_dir / "2026-03-23 Statement - All Time.csv").write_text(
        _retail_csv(
            "legacy-1,2021-12-30 08:56:53 UTC,Receive,FET,1.9859001,CAD,$0.64,$1.27098,$1.27098,$0.00,"
            "Received 1.9859001 FET\n"
            "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
            "Bought 0.01 BTC for 610 CAD\n"
        ),
        encoding="utf-8",
    )
    registry = build_registry()
    adapter = _CoinbaseAdapter()
    profile = _coinbase_profile(raw_dir)
    reversed_profile = replace(
        profile,
        file_inventory=tuple(reversed(profile.file_inventory)),
    )
    statement_documents = StatementExtractionService(
        registry
    ).collect_source_statement_documents(profile, raw_dir)
    planning_result = plan_translation_inputs(
        profile=profile,
        candidates=adapter.describe_translation_inputs(profile, raw_dir),
    )
    reversed_planning_result = plan_translation_inputs(
        profile=reversed_profile,
        candidates=adapter.describe_translation_inputs(reversed_profile, raw_dir),
    )
    evidence_set = build_evidence_set_for_profile(
        profile=profile,
        capture_uid="capture-1",
        capture_manifest_fingerprint="manifest-1",
        planner_result=planning_result,
        statement_documents=statement_documents,
    )
    reversed_evidence_set = build_evidence_set_for_profile(
        profile=reversed_profile,
        capture_uid="capture-1",
        capture_manifest_fingerprint="manifest-1",
        planner_result=reversed_planning_result,
        statement_documents=statement_documents,
    )
    assert evidence_set is not None and reversed_evidence_set is not None
    first = build_coinbase_claim_set(
        profile=profile,
        evidence_set=evidence_set,
        evidence_set_ref=f"working/products/evidence_sets/{evidence_set.evidence_set_id}/evidence_set.json",
        planning_result=planning_result,
        batch=adapter.translate_selected_inputs(profile, raw_dir, planning_result.plan),
    )
    second = build_coinbase_claim_set(
        profile=reversed_profile,
        evidence_set=reversed_evidence_set,
        evidence_set_ref=(
            f"working/products/evidence_sets/{reversed_evidence_set.evidence_set_id}/evidence_set.json"
        ),
        planning_result=reversed_planning_result,
        batch=adapter.translate_selected_inputs(
            reversed_profile,
            raw_dir,
            reversed_planning_result.plan,
        ),
    )

    assert first is not None and second is not None
    assert first.claim_set.to_payload() == second.claim_set.to_payload()
    assert claim_set_fingerprint(first.claim_set) == claim_set_fingerprint(
        second.claim_set
    )
