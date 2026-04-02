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
