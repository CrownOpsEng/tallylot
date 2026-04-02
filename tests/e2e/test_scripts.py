from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from tests.support.helpers import copy_script_to_repo, read_dict_rows, read_json, run_script, write_csv
from tests.support.adapter_packs import load_adapter_packs, stage_adapter_pack


NORMALIZATION_PACKS = load_adapter_packs("normalize")


def write_verification_set(
    directory: Path,
    *,
    validate_rows: list[list[str]],
    missing_rows: list[list[str]],
    duplicate_rows: list[list[str]],
    current_balance_rows: list[list[str]],
    exchange_rows: list[list[str]],
) -> None:
    write_csv(directory / "Validate Transactions.csv", ["Issue"], validate_rows)
    write_csv(
        directory / "Missing Transactions.csv",
        ["Type", "Amount", "Cur.", "Fee", "Fee Cur.", "Value in CAD", "Exchange", "Trade Group", "Comment", "Trade ID", "Date", "Match", ""],
        missing_rows,
    )
    write_csv(
        directory / "Duplicate Transactions.csv",
        ["", "# of duplicates", "Type", "Exchange", "Exchange ID", "Buy", "Sell", "Trade Group", "Tx ID", "Tx Date"],
        duplicate_rows,
    )
    write_csv(
        directory / "Current Balance.csv",
        ["Ticker", "Name", "Type", "Amount", "Value in CAD"],
        current_balance_rows,
    )
    write_csv(
        directory / "Balance by Exchange.csv",
        ["Amount", "Currency", "Current value in CAD", "Current value in BTC", "Exchange"],
        exchange_rows,
    )


def test_source_manifest_cli_generates_manifest_for_capture_folder(tmp_path: Path) -> None:
    source_dir = tmp_path / "source" / "2026-03"
    source_dir.mkdir(parents=True)
    (source_dir / "payload.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    output = tmp_path / "manifest.csv"

    result = run_script("source_manifest.py", "--source-dir", str(source_dir), "--output", str(output))
    rows = read_dict_rows(output)

    assert len(rows) == 1
    assert rows[0]["filename"] == "payload.csv"
    assert rows[0]["size_bytes"] == "8"
    assert rows[0]["sha256"] == hashlib.sha256(b"a,b\n1,2\n").hexdigest()
    assert "Wrote manifest with 1 file(s)" in result.stdout


def test_baseline_check_cli_writes_expected_artifacts(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    write_csv(
        export_dir / "Trade Table.csv",
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
        [["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04"]],
    )
    write_csv(
        export_dir / "Current Balance.csv",
        ["Ticker", "Name", "Type", "Amount", "Value in CAD"],
        [["BTC", "Bitcoin", "Coin", "1.00000000", "10.00"], ["CAD", "Canadian Dollar", "Currency", "-10.00000000", "-10.00"]],
    )
    write_csv(
        export_dir / "Balance by Exchange.csv",
        ["Amount", "Currency", "Current value in CAD", "Current value in BTC", "Exchange"],
        [["1.00000000", "BTC", "10.00", "0.1", "Coinbase"], ["-10.00000000", "CAD", "-10.00", "-0.1", "Coinbase"]],
    )
    write_csv(export_dir / "Validate Transactions.csv", ["Issue"], [["AXS"]])
    write_csv(export_dir / "Missing Transactions.csv", ["Issue"], [["Missing"]])
    write_csv(export_dir / "Duplicate Transactions.csv", ["Issue"], [])
    out_dir = tmp_path / "out"

    result = run_script("baseline_check.py", "--export-dir", str(export_dir), "--out-dir", str(out_dir))
    summary = json.loads(result.stdout)

    assert summary["latest_transaction_timestamp"] == "2023-08-05 08:34:04"
    assert (out_dir / "baseline_summary.json").exists()
    assert (out_dir / "baseline_asset_snapshot.csv").exists()


def test_binance_unwrap_cli_extracts_and_combines(tmp_path: Path) -> None:
    source_dir = tmp_path / "source" / "raw"
    normalized_dir = tmp_path / "02_working" / "normalized"
    source_dir.mkdir(parents=True)
    normalized_dir.mkdir(parents=True)
    (source_dir / "Binance Transactions 2024.csv").write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,2024-09-10 12:09:17,Spot,Deposit,USDT,10,test\n",
        encoding="utf-8",
    )
    archive_path = source_dir / "Binance-Futures-Transaction-History-202603230525(UTC--6)_abcd1234.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "Binance-Futures-Transaction-History-202603230525(UTC--6).csv",
            (
                "Time,Type,Amount,Asset,Symbol,Transaction ID\n"
                "2024-01-02 03:04:05,REALIZED_PNL,1.5,USDT,BTCUSDT,txn-1\n"
            ),
        )

    result = run_script(
        "binance_unwrap.py",
        "--source-dir",
        str(source_dir),
        "--normalized-dir",
        str(normalized_dir),
        "--delete-zips",
    )
    summary = json.loads(result.stdout)

    assert summary["zip_files_processed"] == 1
    assert summary["earliest_timestamp"] == "2024-01-02 09:04:05"
    assert not archive_path.exists()
    assert summary["combined_files_written"] == 0
    assert (source_dir.parent / "raw_csv_inventory.csv").exists()
    assert (source_dir / "Binance-Futures-Transaction-History-202603230525(UTC--6)_abcd1234.csv").exists()


@pytest.mark.parametrize("pack", NORMALIZATION_PACKS, ids=lambda pack: pack.id)
def test_profile_source_cli_processes_source_pack(pack, tmp_path: Path) -> None:
    raw_dir = stage_adapter_pack(pack, tmp_path)
    out_dir = tmp_path / "normalized" / pack.name

    result = run_script(
        "profile_source.py",
        "--source",
        pack.source,
        "--raw-dir",
        str(raw_dir),
        "--out-dir",
        str(out_dir),
    )
    summary = json.loads(result.stdout)
    profile = read_json(out_dir / "profile.json")

    assert summary["adapter"] == pack.expected_adapter
    assert profile["adapter"] == pack.expected_adapter
    assert profile["timezone_summary"]["status"] == pack.expected_timezone_status


@pytest.mark.parametrize("pack", NORMALIZATION_PACKS, ids=lambda pack: pack.id)
def test_normalize_source_cli_processes_source_pack(pack, tmp_path: Path) -> None:
    raw_dir = stage_adapter_pack(pack, tmp_path)
    out_dir = tmp_path / "normalized" / pack.name

    result = run_script(
        "normalize_source.py",
        "--source",
        pack.source,
        "--raw-dir",
        str(raw_dir),
        "--out-dir",
        str(out_dir),
    )
    summary = json.loads(result.stdout)

    assert summary["status"] == pack.expected_normalization_status
    assert read_json(out_dir / "normalization_summary.json")["adapter"] == pack.expected_adapter
    assert read_dict_rows(out_dir / "canonical_events.csv") == pack.expected_json("canonical_events")
    assert read_dict_rows(out_dir / "canonical_balances.csv") == pack.expected_json("canonical_balances")
    assert read_dict_rows(out_dir / "exceptions.csv") == pack.expected_json("exceptions")


def test_wallet_inventory_cli_builds_fixture_repo_inventory(copy_fixture_tree, tmp_path: Path) -> None:
    repo_root = copy_fixture_tree("repos/minimal_wallet_inventory_repo")
    out_dir = tmp_path / "inventory"

    result = run_script(
        "wallet_inventory.py",
        "--repo-root",
        str(repo_root),
        "--out-dir",
        str(out_dir),
    )
    summary = json.loads(result.stdout)
    inventory_rows = read_dict_rows(out_dir / "wallet_inventory.csv")

    assert summary["wallet_count"] == len(inventory_rows)
    assert any(row["wallet_id"] == "address_alias:bb4d" for row in inventory_rows)


def test_stage_import_batch_cli_stages_passing_candidate(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    write_csv(
        baseline_dir / "Trade Table.csv",
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
        [["Trade", "1.00000000", "BTC", "10.00000000", "CAD", "0.10000000", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "tx-1"]],
    )
    candidate = tmp_path / "candidate.csv"
    write_csv(
        candidate,
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
        [["Trade", "1.00000000", "BTC", "10.00000000", "CAD", "0.10000000", "CAD", "Coinbase", "", "", "2023-08-06 08:34:05", "tx-2"]],
    )
    batch_dir = tmp_path / "batch"

    result = run_script(
        "stage_import_batch.py",
        "--candidate",
        str(candidate),
        "--baseline-export-dir",
        str(baseline_dir),
        "--out-dir",
        str(batch_dir),
    )
    summary = json.loads(result.stdout)

    assert summary["status"] == "staged"
    assert (batch_dir / "stage_summary.json").exists()


def test_round_scaffold_cli_creates_temp_repo_scaffold(tmp_path: Path) -> None:
    repo_root = tmp_path
    script_dir = copy_script_to_repo("round_scaffold.py", repo_root).parent
    copy_script_to_repo("script_common.py", repo_root)

    result = run_script(
        "round_scaffold.py",
        "--round-id",
        "round_01",
        "--phase",
        "baseline_repair",
        "--source",
        "shakepay",
        cwd=repo_root,
        scripts_dir=script_dir,
    )

    assert "Verification folder:" in result.stdout
    assert (repo_root / "02_working" / "verification" / "round_01" / "README.md").exists()
    assert (repo_root / "05_outputs" / "logs" / "round_log.csv").exists()


def test_overlap_check_cli_writes_summary(tmp_path: Path) -> None:
    export_dir = tmp_path / "baseline"
    export_dir.mkdir()
    candidate = tmp_path / "candidate.csv"
    out_dir = tmp_path / "out"
    write_csv(
        export_dir / "Trade Table.csv",
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "LPN", "Tx-ID"],
        [["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "", "tx-1"]],
    )
    write_csv(
        candidate,
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
        [["Trade", "2.0", "ETH", "20.0", "CAD", "0.1", "CAD", "Coinbase", "", "", "2023-08-05 08:35:04", "tx-2"]],
    )

    result = run_script(
        "overlap_check.py",
        "--baseline-export-dir",
        str(export_dir),
        "--candidate",
        str(candidate),
        "--out-dir",
        str(out_dir),
    )
    summary = json.loads(result.stdout)

    assert summary["status"] == "pass"
    assert (out_dir / "overlap_summary.json").exists()


def test_intake_sort_cli_plans_historical_dump(tmp_path: Path) -> None:
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    (incoming / "borrow.csv").write_text(
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n",
        encoding="utf-8",
    )
    report_dir = tmp_path / "reports"

    result = run_script(
        "intake_sort.py",
        "--incoming-dir",
        str(incoming),
        "--report-dir",
        str(report_dir),
        "--repo-root",
        str(tmp_path),
    )
    summary = json.loads(result.stdout)

    assert summary["status"] == "planned"
    assert (report_dir / "intake_plan.csv").exists()


def test_adapter_pack_scaffold_cli_creates_pack_layout(tmp_path: Path) -> None:
    fixtures_root = tmp_path / "fixtures"

    result = run_script(
        "adapter_pack_scaffold.py",
        "--adapter",
        "demo",
        "--scenario",
        "basic",
        "--source",
        "Demo Source",
        "--capability",
        "normalize",
        "--fixtures-root",
        str(fixtures_root),
    )
    summary = json.loads(result.stdout)

    pack_root = Path(summary["pack_root"])
    assert (pack_root / "pack.json").exists()
    assert (pack_root / "expected" / "canonical_events.json").exists()


def test_verification_compare_cli_writes_summary(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    current_dir = tmp_path / "current"
    out_dir = tmp_path / "out"
    reference_dir.mkdir()
    current_dir.mkdir()
    write_verification_set(
        reference_dir,
        validate_rows=[],
        missing_rows=[],
        duplicate_rows=[],
        current_balance_rows=[["BTC", "Bitcoin", "Coin", "1.00000000", "10.0"]],
        exchange_rows=[["1.00000000", "BTC", "10.0", "0.1", "Coinbase"]],
    )
    write_verification_set(
        current_dir,
        validate_rows=[],
        missing_rows=[],
        duplicate_rows=[],
        current_balance_rows=[["BTC", "Bitcoin", "Coin", "1.00000000", "10.0"]],
        exchange_rows=[["1.00000000", "BTC", "10.0", "0.1", "Coinbase"]],
    )

    result = run_script(
        "verification_compare.py",
        "--reference-dir",
        str(reference_dir),
        "--current-dir",
        str(current_dir),
        "--out-dir",
        str(out_dir),
    )
    summary = json.loads(result.stdout)

    assert summary["gate_suggestion"] == "review_balance_changes"
    assert (out_dir / "verification_summary.json").exists()
