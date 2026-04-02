from __future__ import annotations

import csv
from pathlib import Path

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
    assert not (repo_root / "01_raw_exports" / "external" / "binance" / "2021-05" / "borrow.csv").exists()


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

    target = repo_root / "01_raw_exports" / "external" / "binance" / "2021-05" / "borrow.csv"
    manifest = repo_root / "01_raw_exports" / "external" / "binance" / "2021-05" / "manifest.csv"
    assert summary["status"] == "applied"
    assert target.exists()
    assert manifest.exists()
    rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
    assert rows[0]["filename"] == "borrow.csv"
