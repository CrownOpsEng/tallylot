from __future__ import annotations

import json
from pathlib import Path

import pytest

from tallylot.application.normalization import NormalizeRequest
from tallylot.application.normalization.contracts import NormalizeUpdateMode
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.serialization.csv_io import read_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from repo_support.capture_roots import materialize_capture_root
from tests.support.adapter_packs import fixture_raw_dir
from tests.support.services import build_normalization_service


def test_normalization_service_filters_events_outside_explicit_window(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    (raw_dir / "transactions.csv").write_text(
        (
            "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
            "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
            "tx_hash,description,account,wallet\n"
            "2023-08-04 10:00:00,trade,BTC,1.0,CAD,10.0,CAD,0.1,out,,,,tx-early,early,Fixture,Primary\n"
            "2023-08-06 10:00:00,trade,ETH,2.0,CAD,20.0,CAD,0.2,out,,,,tx-keep,keep,Fixture,Primary\n"
        ),
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
            window_start="2023-08-05 08:34:05",
            window_end="2025-12-31 23:59:59",
        )
    )

    normalized_rows = read_rows(output_dir / "facts.csv")
    fact_annotations = json.loads(
        (output_dir / "fact_annotations.json").read_text(encoding="utf-8")
    )
    summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )
    profile = json.loads((output_dir / "profile.json").read_text(encoding="utf-8"))

    assert response.fact_count == 1
    assert len(normalized_rows) == 1
    assert normalized_rows[0]["tx_hash"] == "tx-keep"
    assert normalized_rows[0]["fact_id"] == "fixture_source:3"
    assert fact_annotations == [
        {
            "fact_id": normalized_rows[0]["fact_id"],
            "provenance_refs": [],
            "review_markers": [],
            "adapter_metadata": [],
        }
    ]
    assert summary["fact_count"] == 1
    assert summary["facts_outside_normalization_window"] == 1
    assert summary["normalization_window_start"] == "2023-08-05 08:34:05"
    assert summary["normalization_window_end"] == "2025-12-31 23:59:59"
    assert (
        profile["normalization_hints"]["normalization_window_start"]
        == "2023-08-05 08:34:05"
    )
    assert (
        profile["normalization_hints"]["normalization_window_end"]
        == "2025-12-31 23:59:59"
    )


def test_normalization_service_filters_timestamped_issues_outside_explicit_window(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="Binance")
    (raw_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv").write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,23-08-05 08:34:04,Funding,Transfer Between Main and Funding Wallet,USDT,-10,\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="Binance",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
            window_start="2023-08-05 08:34:05",
            window_end="2025-12-31 23:59:59",
        )
    )

    issue_rows = read_rows(output_dir / "exceptions.csv")
    summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )

    assert response.issue_count == 0
    assert not issue_rows
    assert summary["issue_count"] == 0
    assert summary["issues_outside_normalization_window"] == 1


def test_normalization_service_filters_row_scoped_issues_outside_explicit_window(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="Future Broker")
    (raw_dir / "activity.csv").write_text(
        "transaction_date,settlement_date,account_id,account_type,activity_type,activity_sub_type,"
        "quantity,currency,symbol,commission,net_cash_amount\n"
        "2023-09-22,2023-09-22,acct-1,Crypto,staking_reward,REWARD,0.05,CAD,BTC,0,0\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="Future Broker",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
            window_start="2023-09-23 00:00:00",
            window_end="2025-12-31 23:59:59",
        )
    )

    issue_rows = read_rows(output_dir / "exceptions.csv")
    summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )

    assert response.issue_count == 0
    assert not issue_rows
    assert summary["issue_count"] == 0
    assert summary["issues_outside_normalization_window"] == 1


def test_normalization_service_rejects_ambiguous_timezone_inventory(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="Binance")
    (raw_dir / "Binance-Spot-Trade-History.csv").write_text(
        "Time,Pair,Side,Price,Executed,Amount,Fee\n"
        "23-09-20 18:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n",
        encoding="utf-8",
    )
    service = build_normalization_service()

    with pytest.raises(ValueError, match="timezone issues"):
        service.execute(
            NormalizeRequest(
                source="Binance",
                raw_capture_ref=to_resource_ref(raw_dir),
                normalized_output_ref=to_resource_ref(tmp_path / "normalized"),
            )
        )


def test_normalization_service_rewrites_stale_output_profile_with_live_adapter_state(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="Future Exchange")
    (raw_dir / "retail-export.csv").write_text(
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
        "Bought 0.01 BTC for 610 CAD\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "normalized"
    output_dir.mkdir()
    (output_dir / "profile.json").write_text(
        json.dumps(
            {
                "manifest_fingerprint": "stale",
                "adapter_id": "generic",
                "supported": False,
            }
        ),
        encoding="utf-8",
    )
    service = build_normalization_service()

    response = service.execute(
        NormalizeRequest(
            source="Future Exchange",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )
    profile = json.loads((output_dir / "profile.json").read_text(encoding="utf-8"))

    assert response.adapter_id == "coinbase"
    assert profile["adapter_id"] == "coinbase"
    assert profile["supported"] is True
    assert profile["manifest_fingerprint"] != "stale"


def test_normalization_second_identical_run_uses_auto_mode_and_reuses_target_products(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(
        tmp_path,
        source="coinbase",
        source_dir=fixture_raw_dir("coinbase", "retail_buy_renamed"),
    )
    service = build_normalization_service()
    output_dir = tmp_path / "normalized"

    first = service.execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )
    second = service.execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )
    summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )

    assert second.update_mode_requested == "auto"
    assert second.update_mode_effective == "auto"
    assert second.reused_target_product_count > 0
    assert second.economic_facts_ref == first.economic_facts_ref
    assert second.reconciliation_state_refs == first.reconciliation_state_refs
    assert second.checkpoint_refs == first.checkpoint_refs
    assert (
        summary["target_product_execution"]["economic_facts"]["kernel_action"]
        == "reused"
    )


def test_normalization_full_update_reuses_kernels_and_refreshes_detail_outputs(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(
        tmp_path,
        source="coinbase",
        source_dir=fixture_raw_dir("coinbase", "retail_buy_renamed"),
    )
    service = build_normalization_service()
    output_dir = tmp_path / "normalized"
    first = service.execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )
    second = service.execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
            update_mode=NormalizeUpdateMode.FULL_UPDATE,
        )
    )
    summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )

    assert second.economic_facts_ref == first.economic_facts_ref
    assert second.reconciliation_state_refs == first.reconciliation_state_refs
    assert (
        summary["target_product_execution"]["economic_facts"]["kernel_action"]
        == "reused"
    )
    assert (
        summary["target_product_execution"]["economic_facts"]["compatibility_action"]
        == "refreshed"
    )


def test_normalization_rebuild_mode_rebuilds_every_stage_but_preserves_ids_on_unchanged_inputs(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(
        tmp_path,
        source="coinbase",
        source_dir=fixture_raw_dir("coinbase", "retail_buy_renamed"),
    )
    service = build_normalization_service()
    output_dir = tmp_path / "normalized"
    first = service.execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )
    first_summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )
    second = service.execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
            update_mode=NormalizeUpdateMode.REBUILD,
        )
    )
    second_summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )

    assert second.economic_facts_ref == first.economic_facts_ref
    assert second.reconciliation_state_refs == first.reconciliation_state_refs
    assert (
        second_summary["target_product_execution"]["economic_facts"]["kernel_action"]
        == "rebuilt"
    )
    assert (
        second_summary["target_product_execution"]["economic_facts"]["fingerprint"]
        == first_summary["target_product_execution"]["economic_facts"]["fingerprint"]
    )


def test_normalization_rerun_prunes_stale_balance_reference_issue_file_when_clean(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="coinbase")
    output_dir = tmp_path / "normalized"
    output_dir.mkdir()
    (output_dir / "balance_reference_issues.csv").write_text(
        "issue_id\nstale\n", encoding="utf-8"
    )

    build_normalization_service().execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    assert not (output_dir / "balance_reference_issues.csv").exists()


def test_normalization_rerun_prunes_stale_checkpoint_roots_when_current_run_emits_none(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="coinbase")
    (raw_dir / "retail.csv").write_text(
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-buy,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
        "Bought 0.01 BTC\n",
        encoding="utf-8",
    )
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(raw_dir / "2026-03-23 - transaction-history.pdf"))
    pdf.drawString(72, 750, "Coinbase Canada, Inc.")
    pdf.drawString(72, 735, "Transaction History Report")
    pdf.drawString(72, 720, "Closing Balance as of 2026-03-22 23:59:59 UTC 0 CAD")
    pdf.drawString(
        72,
        705,
        "Portfolio summary balances are as of 2026-03-22 23:59:59 UTC",
    )
    pdf.drawString(72, 690, "BTC 0.01000000 N/A 60,000.00 CAD/BTC 600.00 CAD")
    pdf.save()
    output_dir = tmp_path / "normalized"
    service = build_normalization_service()
    first = service.execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    for pdf_path in raw_dir.glob("*.pdf"):
        pdf_path.unlink()

    second = service.execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )
    summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )
    workspace_root = tmp_path / "workspace"

    assert first.checkpoint_refs
    assert second.checkpoint_refs == ()
    assert not any((workspace_root / ref).exists() for ref in first.checkpoint_refs)
    assert summary["target_product_execution"]["pruned_checkpoint_refs"] == list(
        first.checkpoint_refs
    )


@pytest.mark.parametrize(
    ("source", "raw_dir", "expected"),
    (
        (
            "Future Exchange",
            fixture_raw_dir("coinbase", "retail_buy_renamed"),
            {
                "fact_count": 1,
                "issue_count": 0,
                "expects_evidence_set": True,
                "expects_claim_set": True,
                "expects_economic_facts": True,
                "expects_reconciliation_states": True,
                "expects_checkpoints": False,
            },
        ),
        (
            "Future Broker",
            fixture_raw_dir("wealthsimple", "broker_trade"),
            {
                "fact_count": 1,
                "issue_count": 0,
                "expects_evidence_set": False,
                "expects_claim_set": False,
                "expects_economic_facts": False,
                "expects_reconciliation_states": False,
                "expects_checkpoints": False,
            },
        ),
        (
            "Binance",
            fixture_raw_dir("binance", "mixed_history"),
            {
                "fact_count": 5,
                "issue_count": 1,
                "expects_evidence_set": False,
                "expects_claim_set": False,
                "expects_economic_facts": False,
                "expects_reconciliation_states": False,
                "expects_checkpoints": False,
            },
        ),
    ),
)
def test_normalization_service_supports_explicit_windows_for_fixture_adapters(
    tmp_path: Path,
    source: str,
    raw_dir: Path,
    expected: dict[str, int | bool],
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source=source, source_dir=raw_dir)
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source=source,
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
            window_start="2023-01-01 00:00:00",
            window_end="2025-12-31 23:59:59",
        )
    )

    assert response.fact_count == expected["fact_count"]
    assert response.issue_count == expected["issue_count"]
    assert (response.evidence_set_id != "") is expected["expects_evidence_set"]
    assert (response.claim_set_id != "") is expected["expects_claim_set"]
    assert (response.economic_facts_id != "") is expected["expects_economic_facts"]
    assert (response.reconciliation_state_refs != ()) is expected[
        "expects_reconciliation_states"
    ]
    assert (response.checkpoint_refs != ()) is expected["expects_checkpoints"]
    if expected["expects_evidence_set"]:
        assert response.evidence_set_ref == (
            "working/products/evidence_sets/"
            f"{response.evidence_set_id}/evidence_set.json"
        )
    else:
        assert response.evidence_set_ref == ""
    if expected["expects_claim_set"]:
        assert response.claim_set_ref == (
            f"working/products/claim_sets/{response.claim_set_id}/claim_set.json"
        )
    else:
        assert response.claim_set_ref == ""
    if expected["expects_economic_facts"]:
        assert response.economic_facts_ref.endswith("/economic_facts.json")
    else:
        assert response.economic_facts_ref == ""
    assert (output_dir / "facts.csv").exists()
    assert (
        json.loads(
            (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
        )["normalization_window_start"]
        == "2023-01-01 00:00:00"
    )
