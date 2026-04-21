from __future__ import annotations

import json
from pathlib import Path

from reportlab.pdfgen import canvas

from tallylot.application.normalization import NormalizeRequest
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.serialization.csv_io import read_rows
from repo_support.capture_roots import materialize_capture_root
from tests.support.adapter_packs import fixture_raw_dir
from tests.support.services import build_normalization_service


def test_coinbase_retail_only_normalization_writes_downstream_products(
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
    summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )
    workspace_root = tmp_path / "workspace"

    assert response.economic_facts_id
    assert response.economic_facts_ref
    assert response.reconciliation_state_ids
    assert response.reconciliation_state_refs
    assert not response.checkpoint_ids
    assert not response.checkpoint_refs
    assert response.fact_count == len(read_rows(output_dir / "facts.csv"))
    assert (workspace_root / response.economic_facts_ref).exists()
    assert all(
        (workspace_root / ref).exists() for ref in response.reconciliation_state_refs
    )
    assert summary["economic_facts_id"] == response.economic_facts_id
    assert summary["economic_facts_ref"] == response.economic_facts_ref
    assert summary["reconciliation_state_ids"] == list(
        response.reconciliation_state_ids
    )
    assert summary["checkpoint_ids"] == []
    assert read_rows(output_dir / "facts.csv")[0]["effective_at"] != ""


def test_coinbase_statement_backed_normalization_writes_checkpoint_products(
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
    _make_pdf(
        raw_dir / "2026-03-23 - transaction-history.pdf",
        "Coinbase Canada, Inc.",
        "Transaction History Report",
        "Closing Balance as of 2026-03-22 23:59:59 UTC 0 CAD",
        "Portfolio summary balances are as of 2026-03-22 23:59:59 UTC",
        "BTC 0.01000000 N/A 60,000.00 CAD/BTC 600.00 CAD",
    )
    output_dir = tmp_path / "normalized"

    response = build_normalization_service().execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )
    workspace_root = tmp_path / "workspace"
    balance_rows = read_rows(output_dir / "balance_snapshots.csv")
    balance_reference_rows = read_rows(output_dir / "balance_references.csv")

    assert response.economic_facts_id
    assert response.reconciliation_state_refs
    assert response.checkpoint_refs
    assert response.fact_count == len(read_rows(output_dir / "facts.csv"))
    assert (workspace_root / response.economic_facts_ref).exists()
    assert all(
        (workspace_root / ref).exists() for ref in response.reconciliation_state_refs
    )
    assert all((workspace_root / ref).exists() for ref in response.checkpoint_refs)
    assert balance_rows == [
        {
            "source": "coinbase",
            "location_id": "coinbase",
            "instrument_id": "symbol:BTC@coinbase",
            "balance_kind": "available",
            "target_at": "2026-03-22 23:59:59",
            "target_precision": "timestamp",
            "quantity": "0.01",
            "snapshot_basis": "fact_cutoff",
            "notes": "",
        },
        {
            "source": "coinbase",
            "location_id": "coinbase:coinbase_cash",
            "instrument_id": "symbol:CAD@coinbase",
            "balance_kind": "available",
            "target_at": "2026-03-22 23:59:59",
            "target_precision": "timestamp",
            "quantity": "0",
            "snapshot_basis": "fact_cutoff",
            "notes": "",
        },
    ]
    assert balance_reference_rows == [
        {
            "source": "coinbase",
            "location_id": "coinbase",
            "instrument_id": "symbol:BTC@coinbase",
            "balance_kind": "available",
            "target_at": "2026-03-22 23:59:59",
            "target_precision": "timestamp",
            "quantity": "0.01",
            "reference_kind": "source_document",
            "observed_at": "2026-03-22 23:59:59",
            "observed_precision": "timestamp",
            "support_ref": "2026-03-23 - transaction-history.pdf",
            "provider_family": "",
            "provider_locator": "",
            "provider_block_ref": "",
            "reviewed_by": "",
            "reviewed_at": "",
            "notes": "Portfolio summary asset balance from Coinbase statement PDF",
        },
        {
            "source": "coinbase",
            "location_id": "coinbase:coinbase_cash",
            "instrument_id": "symbol:CAD@coinbase",
            "balance_kind": "available",
            "target_at": "2026-03-22 23:59:59",
            "target_precision": "timestamp",
            "quantity": "0",
            "reference_kind": "source_document",
            "observed_at": "2026-03-22 23:59:59",
            "observed_precision": "timestamp",
            "support_ref": "2026-03-23 - transaction-history.pdf",
            "provider_family": "",
            "provider_locator": "",
            "provider_block_ref": "",
            "reviewed_by": "",
            "reviewed_at": "",
            "notes": "Closing fiat balance from Coinbase statement PDF",
        },
    ]


def test_coinbase_normalization_second_identical_run_preserves_refs_and_records_reuse(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(
        tmp_path,
        source="coinbase",
        source_dir=fixture_raw_dir("coinbase", "retail_buy_renamed"),
    )
    output_dir = tmp_path / "normalized"
    service = build_normalization_service()

    first = service.execute(
        NormalizeRequest(
            source="coinbase",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )
    first_facts = read_rows(output_dir / "facts.csv")
    first_snapshots = read_rows(output_dir / "balance_snapshots.csv")
    first_references = read_rows(output_dir / "balance_references.csv")
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

    assert second.economic_facts_ref == first.economic_facts_ref
    assert second.reconciliation_state_refs == first.reconciliation_state_refs
    assert second.checkpoint_refs == first.checkpoint_refs
    assert read_rows(output_dir / "facts.csv") == first_facts
    assert read_rows(output_dir / "balance_snapshots.csv") == first_snapshots
    assert read_rows(output_dir / "balance_references.csv") == first_references
    assert "target_product_execution" in summary
    assert (
        summary["target_product_execution"]["economic_facts"]["kernel_action"]
        == "reused"
    )


def test_coinbase_normalization_changed_capture_rebuilds_only_affected_target_products(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(
        tmp_path,
        source="coinbase",
        source_dir=fixture_raw_dir("coinbase", "retail_buy_renamed"),
    )
    output_dir = tmp_path / "normalized"
    service = build_normalization_service()

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
    first_facts = read_rows(output_dir / "facts.csv")
    (raw_dir / "retail-export.csv").write_text(
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-buy,2024-02-08 16:31:22 UTC,Buy,ETH,0.50000000,CAD,$4000.00,$2000.00,$2010.00,$10.00,"
        "Bought 0.5 ETH\n",
        encoding="utf-8",
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
    workspace_root = tmp_path / "workspace"

    assert (
        second.economic_facts_ref != first.economic_facts_ref
        or summary["target_product_execution"]["economic_facts"]["fingerprint"]
        != first_summary["target_product_execution"]["economic_facts"]["fingerprint"]
        or read_rows(output_dir / "facts.csv") != first_facts
    )
    assert (
        summary["target_product_execution"]["economic_facts"]["kernel_action"]
        == "rebuilt"
    )
    assert not any(
        (workspace_root / ref).exists()
        for ref in summary["target_product_execution"][
            "pruned_reconciliation_state_refs"
        ]
    )
    assert read_rows(output_dir / "facts.csv")[0]["legs"] != ""


def _make_pdf(path: Path, *lines: str) -> None:
    pdf = canvas.Canvas(str(path))
    y = 750
    for line in lines:
        pdf.drawString(72, y, line)
        y -= 15
    pdf.save()
