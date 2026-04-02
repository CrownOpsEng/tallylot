from __future__ import annotations

import csv
from pathlib import Path
import zipfile

import pytest

import pipeline


@pytest.mark.pipeline
def test_plan_intake_dump_dry_run_writes_reports_without_copying(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming = repo_root / "01_raw_exports" / "incoming"
    incoming.mkdir(parents=True)
    (incoming / "borrow.csv").write_text(
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n",
        encoding="utf-8",
    )
    report_dir = repo_root / "02_working" / "intake_reports" / "run_01"

    summary = pipeline.plan_intake_dump(
        repo_root=repo_root,
        incoming_dir=incoming,
        report_dir=report_dir,
        apply=False,
    )

    assert summary["status"] == "planned"
    assert (report_dir / "intake_plan.csv").exists()
    assert not (repo_root / "01_raw_exports" / "external" / "binance" / "2021-05" / "binance-isolated-margin-loose" / "borrow.csv").exists()


@pytest.mark.pipeline
def test_plan_intake_dump_apply_copies_files_and_writes_manifest(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming = repo_root / "01_raw_exports" / "incoming"
    incoming.mkdir(parents=True)
    (incoming / "borrow.csv").write_text(
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n",
        encoding="utf-8",
    )
    report_dir = repo_root / "02_working" / "intake_reports" / "run_01"

    summary = pipeline.plan_intake_dump(
        repo_root=repo_root,
        incoming_dir=incoming,
        report_dir=report_dir,
        apply=True,
    )

    target = repo_root / "01_raw_exports" / "external" / "binance" / "2021-05" / "binance-isolated-margin-loose" / "borrow.csv"
    manifest = repo_root / "01_raw_exports" / "external" / "binance" / "2021-05" / "manifest.csv"
    assert summary["status"] == "applied"
    assert target.exists()
    assert manifest.exists()
    rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
    assert rows[0]["filename"] == "binance-isolated-margin-loose/borrow.csv"


@pytest.mark.pipeline
def test_plan_intake_dump_aliases_identical_duplicates_without_overwrite(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming = repo_root / "01_raw_exports" / "incoming"
    first = incoming / "tmp" / "CoinTracking Export_files" / "style.min.css"
    first.parent.mkdir(parents=True, exist_ok=True)
    first.write_text("body{}\n", encoding="utf-8")
    second = incoming / "tmp2" / "CoinTracking Export_files" / "style.min.css"
    second.parent.mkdir(parents=True, exist_ok=True)
    second.write_text("body{}\n", encoding="utf-8")
    report_dir = repo_root / "02_working" / "intake_reports" / "run_01"

    summary = pipeline.plan_intake_dump(
        repo_root=repo_root,
        incoming_dir=incoming,
        report_dir=report_dir,
        apply=True,
    )

    manifest = list(csv.DictReader((repo_root / "01_raw_exports" / "cointracking" / "history" / "review-required" / "manifest.csv").open(encoding="utf-8")))
    assert summary["alias_groups"] >= 1
    assert len(manifest) == 1
    assert "CoinTracking Export_files/style.min.css" in manifest[0]["source_paths"]


@pytest.mark.pipeline
def test_plan_intake_dump_extracts_identified_crypto_archives(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming = repo_root / "01_raw_exports" / "incoming"
    incoming.mkdir(parents=True)
    archive = incoming / "202203291736.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(
            "part-00000.csv",
            (
                "Date(UTC),Pair,Side,Price,Executed,Amount,Fee\n"
                "2022-03-28 13:01:36,SOLBUSD,SELL,110.03,0.1800000000SOL,19.8054BUSD,0.0198054BUSD\n"
            ),
        )
    report_dir = repo_root / "02_working" / "intake_reports" / "run_01"

    summary = pipeline.plan_intake_dump(
        repo_root=repo_root,
        incoming_dir=incoming,
        report_dir=report_dir,
        apply=True,
    )

    archive_path = repo_root / "01_raw_exports" / "external" / "binance" / "2022-03" / "202203291736" / "archive" / "202203291736.zip"
    extracted_path = repo_root / "01_raw_exports" / "external" / "binance" / "2022-03" / "202203291736" / "contents" / "part-00000.csv"
    manifest = list(csv.DictReader((repo_root / "01_raw_exports" / "external" / "binance" / "2022-03" / "manifest.csv").open(encoding="utf-8")))

    assert summary["status"] == "applied"
    assert archive_path.exists()
    assert extracted_path.exists()
    assert {row["filename"] for row in manifest} == {"202203291736/archive/202203291736.zip", "202203291736/contents/part-00000.csv"}


@pytest.mark.pipeline
def test_plan_intake_dump_skips_subset_duplicate_packages(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming = repo_root / "01_raw_exports" / "incoming"
    incoming.mkdir(parents=True)
    borrow_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    interest_payload = "Pair,Coin,Amount,Time,Interest Type\nADA/USDT,USDT,0.1,2021-05-25 12:53:03,Hourly\n"
    (incoming / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    bundle_dir = incoming / "2021" / "Binance" / "From Binance"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    (bundle_dir / "interest.csv").write_text(interest_payload, encoding="utf-8")
    report_dir = repo_root / "02_working" / "intake_reports" / "run_01"

    summary = pipeline.plan_intake_dump(
        repo_root=repo_root,
        incoming_dir=incoming,
        report_dir=report_dir,
        apply=False,
    )

    rows = list(csv.DictReader((report_dir / "intake_plan.csv").open(encoding="utf-8")))
    loose_row = next(row for row in rows if row["path"].endswith("/borrow.csv") and "/incoming/borrow.csv" in row["path"])
    bundle_row = next(row for row in rows if row["path"].endswith("/From Binance/borrow.csv"))

    assert summary["duplicate_packages"] >= 1
    assert loose_row["package_status"] == "duplicate_package_subset"
    assert loose_row["placement_status"] == "package_duplicate_skip"
    assert bundle_row["package_status"] == "primary"


@pytest.mark.pipeline
def test_plan_intake_dump_merges_same_cycle_near_duplicate_packages(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming = repo_root / "01_raw_exports" / "incoming"
    older = incoming / "2021" / "Binance" / "202203291730-export"
    newer = incoming / "2021" / "Binance" / "202203291830-export"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    borrow_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    interest_payload = "Pair,Coin,Amount,Time,Interest Type\nADA/USDT,USDT,0.1,2021-05-25 12:53:03,Hourly\n"
    repay_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 13:53:03,0.0345,Auto repayment,CONFIRM\n"
    (older / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    (older / "interest.csv").write_text(interest_payload, encoding="utf-8")
    (newer / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    (newer / "repay.csv").write_text(repay_payload, encoding="utf-8")
    report_dir = repo_root / "02_working" / "intake_reports" / "run_01"

    summary = pipeline.plan_intake_dump(
        repo_root=repo_root,
        incoming_dir=incoming,
        report_dir=report_dir,
        apply=True,
    )

    plan_rows = list(csv.DictReader((report_dir / "intake_plan.csv").open(encoding="utf-8")))
    primary_row = next(row for row in plan_rows if row["package_status"] == "merge_primary")
    manifest_path = repo_root / "01_raw_exports" / "external" / "binance" / primary_row["capture_id"] / "manifest.csv"
    rows = list(csv.DictReader(manifest_path.open(encoding="utf-8")))
    filenames = {row["filename"] for row in rows}

    assert summary["merge_primary_packages"] == 1
    assert summary["merged_packages"] == 1
    assert f"{primary_row['bundle_id']}/borrow.csv" in filenames
    assert f"{primary_row['bundle_id']}/interest.csv" in filenames
    assert f"{primary_row['bundle_id']}/repay.csv" in filenames
    assert all("202203291730-export" not in filename for filename in filenames)
    superseded_row = next(row for row in plan_rows if "/202203291730-export/borrow.csv" in row["source_path"])
    assert superseded_row["package_row_status"] == "package_merge_into_primary"


@pytest.mark.pipeline
def test_plan_intake_dump_keeps_different_cycle_packages_separate(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming = repo_root / "01_raw_exports" / "incoming"
    older = incoming / "2021" / "Binance" / "202203291730-export"
    newer = incoming / "2021" / "Binance" / "202203301830-export"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    borrow_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    interest_payload = "Pair,Coin,Amount,Time,Interest Type\nADA/USDT,USDT,0.1,2021-05-25 12:53:03,Hourly\n"
    repay_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 13:53:03,0.0345,Auto repayment,CONFIRM\n"
    (older / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    (older / "interest.csv").write_text(interest_payload, encoding="utf-8")
    (newer / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    (newer / "repay.csv").write_text(repay_payload, encoding="utf-8")
    report_dir = repo_root / "02_working" / "intake_reports" / "run_01"

    summary = pipeline.plan_intake_dump(
        repo_root=repo_root,
        incoming_dir=incoming,
        report_dir=report_dir,
        apply=False,
    )

    rows = list(csv.DictReader((report_dir / "intake_plan.csv").open(encoding="utf-8")))
    older_status = next(row["package_status"] for row in rows if "/202203291730-export/borrow.csv" in row["source_path"])
    newer_status = next(row["package_status"] for row in rows if "/202203301830-export/borrow.csv" in row["source_path"])

    assert summary["merged_packages"] == 0
    assert summary["overlap_packages"] == 2
    assert older_status == "overlap_partial_review"
    assert newer_status == "overlap_partial_review"


@pytest.mark.pipeline
def test_plan_intake_dump_skips_superseded_conflicting_file_during_merge_apply(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming = repo_root / "01_raw_exports" / "incoming"
    older = incoming / "2021" / "Binance" / "202203291730-export"
    newer = incoming / "2021" / "Binance" / "202203291830-export"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    shared_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    older_trades = "Date(UTC),Pair,Side,Price,Executed,Amount,Fee\n2021-05-25 12:53:03,ADAUSDT,SELL,1.5,1ADA,1.5USDT,0.001BNB\n"
    newer_trades = "Date(UTC),Pair,Side,Price,Executed,Amount,Fee\n2021-05-25 12:53:03,ADAUSDT,SELL,1.6,1ADA,1.6USDT,0.001BNB\n"
    interest_payload = "Pair,Coin,Amount,Time,Interest Type\nADA/USDT,USDT,0.1,2021-05-25 12:53:03,Hourly\n"
    (older / "borrow.csv").write_text(shared_payload, encoding="utf-8")
    (older / "trades.csv").write_text(older_trades, encoding="utf-8")
    (older / "interest.csv").write_text(interest_payload, encoding="utf-8")
    (newer / "borrow.csv").write_text(shared_payload, encoding="utf-8")
    (newer / "trades.csv").write_text(newer_trades, encoding="utf-8")
    report_dir = repo_root / "02_working" / "intake_reports" / "run_01"

    summary = pipeline.plan_intake_dump(
        repo_root=repo_root,
        incoming_dir=incoming,
        report_dir=report_dir,
        apply=True,
    )

    plan_rows = list(csv.DictReader((report_dir / "intake_plan.csv").open(encoding="utf-8")))
    superseded_row = next(row for row in plan_rows if "/202203291730-export/trades.csv" in row["source_path"])
    primary_trade_row = next(row for row in plan_rows if "/202203291830-export/trades.csv" in row["source_path"])
    manifest_path = repo_root / "01_raw_exports" / "external" / "binance" / primary_trade_row["capture_id"] / "manifest.csv"
    manifest_rows = list(csv.DictReader(manifest_path.open(encoding="utf-8")))
    filenames = {row["filename"] for row in manifest_rows}

    assert summary["merge_primary_packages"] == 1
    assert superseded_row["package_row_status"] == "package_merge_superseded_skip"
    assert superseded_row["placement_status"] == "package_merge_superseded_skip"
    assert primary_trade_row["placement_status"] == "placed_primary"
    assert f"{primary_trade_row['bundle_id']}/trades.csv" in filenames
    assert len([name for name in filenames if name.endswith("/trades.csv")]) == 1


@pytest.mark.pipeline
def test_plan_intake_dump_marks_mixed_cycle_bundle_for_review_but_still_places_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming = repo_root / "01_raw_exports" / "incoming"
    bundle = incoming / "2021" / "Binance" / "MixedCycle"
    bundle.mkdir(parents=True)
    first_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    second_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-26 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    (bundle / "202203291730-borrow.csv").write_text(first_payload, encoding="utf-8")
    (bundle / "202203301730-repay.csv").write_text(second_payload, encoding="utf-8")
    report_dir = repo_root / "02_working" / "intake_reports" / "run_01"

    summary = pipeline.plan_intake_dump(
        repo_root=repo_root,
        incoming_dir=incoming,
        report_dir=report_dir,
        apply=True,
    )

    plan_rows = list(csv.DictReader((report_dir / "intake_plan.csv").open(encoding="utf-8")))
    mixed_rows = [row for row in plan_rows if row["package_status"] == "mixed_cycle_review"]
    manifest_path = repo_root / "01_raw_exports" / "external" / "binance" / mixed_rows[0]["capture_id"] / "manifest.csv"
    manifest_rows = list(csv.DictReader(manifest_path.open(encoding="utf-8")))

    assert summary["mixed_cycle_packages"] == 1
    assert len(mixed_rows) == 2
    assert all(row["review_required"] == "yes" for row in mixed_rows)
    assert all("package_cycle_mixed" in row["review_codes"] for row in mixed_rows)
    assert all(row["placement_status"] == "placed_primary" for row in mixed_rows)
    assert len(manifest_rows) == 2


@pytest.mark.pipeline
def test_plan_intake_dump_uses_inventory_labels_in_scope_conflict_review(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    wallet_inventory = repo_root / "03_analysis" / "inventory" / "wallet_inventory.csv"
    wallet_inventory.parent.mkdir(parents=True, exist_ok=True)
    wallet_inventory.write_text(
        "wallet_id,identifier_kind,normalized_identifier,display_identifier,network_scopes,source_labels,controller_labels,account_labels,evidence_count,primary_evidence_path,status,notes\n"
        "evm_address:0x1111111111111111111111111111111111111111,evm_address,0x1111111111111111111111111111111111111111,0x1111111111111111111111111111111111111111,bsc,bsc-metamask1,Explorer export,Account 1,1,/tmp/a,ready,\n"
        "evm_address:0x1111111111111111111111111111111111111111,evm_address,0x1111111111111111111111111111111111111111,0x1111111111111111111111111111111111111111,bsc,bsc-metamask2,Explorer export,Account 2,1,/tmp/b,ready,\n",
        encoding="utf-8",
    )
    incoming = repo_root / "01_raw_exports" / "incoming"
    first = incoming / "2021" / "Binance" / "202203291730-export"
    second = incoming / "2021" / "Binance" / "202203291830-export"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    shared_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    account_header = "Address,Date(UTC),Pair,Side,Price,Executed,Amount,Fee\n"
    first_scope_payload = account_header + "0x1111111111111111111111111111111111111111,2021-05-25 12:53:03,ADAUSDT,SELL,1.5,1ADA,1.5USDT,0.001BNB\n"
    second_scope_payload = account_header + "0x1111111111111111111111111111111111111111,2021-05-25 12:53:03,ADAUSDT,SELL,1.5,1ADA,1.5USDT,0.001BNB\n"
    (first / "borrow.csv").write_text(shared_payload, encoding="utf-8")
    (first / "account.csv").write_text(first_scope_payload, encoding="utf-8")
    (second / "borrow.csv").write_text(shared_payload, encoding="utf-8")
    (second / "account.csv").write_text(second_scope_payload, encoding="utf-8")
    report_dir = repo_root / "02_working" / "intake_reports" / "run_01"

    pipeline.plan_intake_dump(
        repo_root=repo_root,
        incoming_dir=incoming,
        report_dir=report_dir,
        apply=False,
    )

    rows = list(csv.DictReader((report_dir / "intake_plan.csv").open(encoding="utf-8")))
    review_row = next(row for row in rows if "/202203291730-export/borrow.csv" in row["source_path"])

    assert review_row["package_scope_status"] == "incompatible_scope"
    assert "Account 1" in review_row["review_reason"]
    assert "Account 2" in review_row["review_reason"]


@pytest.mark.pipeline
def test_plan_intake_dump_routes_wallet_export_to_existing_inventory_source(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    source_inventory = repo_root / "03_analysis" / "issues" / "source_inventory.csv"
    source_inventory.parent.mkdir(parents=True, exist_ok=True)
    source_inventory.write_text(
        "source,activity_after_cutoff,first_post_cutoff_tx,export_window_start,export_window_end,import_order,status,capture_path,profile_status,adapter,normalization_status,exception_count,candidate_path,notes\n"
        "eth-gala1,yes,,2023-08-05 08:34:05,2025-12-31 23:59:59,1,capture_complete,01_raw_exports/external/eth-gala1/2026-03,profiled,evm_explorer,ready,0,,\n",
        encoding="utf-8",
    )
    wallet_evidence = repo_root / "03_analysis" / "inventory" / "wallet_inventory_evidence.csv"
    wallet_evidence.parent.mkdir(parents=True, exist_ok=True)
    wallet_evidence.write_text(
        "source,raw_dir,wallet_id,identifier_kind,normalized_identifier,display_identifier,network_scope,controller,account_label,evidence_kind,evidence_path,confidence,note\n"
        "eth-gala1,/tmp/capture,evm_address:0x2222222222222222222222222222222222222222,evm_address,0x2222222222222222222222222222222222222222,0x2222222222222222222222222222222222222222,ethereum,Explorer export,Account 2,filename,/tmp/evidence.csv,high,\n",
        encoding="utf-8",
    )
    incoming = repo_root / "01_raw_exports" / "incoming"
    export_path = incoming / "Account1-bsc export-address-token.csv"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(
        "Transaction Hash,Blockno,UnixTimestamp,DateTime (UTC),TokenValue,TokenSymbol,From,To\n"
        "0xabc,1,1710000000,2024-03-09 09:41:37,1,GALA,0x0,0x2222222222222222222222222222222222222222\n",
        encoding="utf-8",
    )
    report_dir = repo_root / "02_working" / "intake_reports" / "run_01"

    pipeline.plan_intake_dump(
        repo_root=repo_root,
        incoming_dir=incoming,
        report_dir=report_dir,
        apply=False,
    )

    rows = list(csv.DictReader((report_dir / "intake_plan.csv").open(encoding="utf-8")))
    row = next(item for item in rows if item["archive_source_path"] == "")

    assert row["source_folder"] == "eth-gala1"
    assert row["source_label"] == "eth-gala1"
    assert row["inventory_match_status"] == "inventory_source_match"
    assert row["review_required"] == "no"
