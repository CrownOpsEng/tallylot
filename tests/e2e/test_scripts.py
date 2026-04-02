from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tests.support.helpers import REPO_ROOT, copy_script_to_repo, read_dict_rows, read_json, run_script


class ScriptEndToEndTests(unittest.TestCase):
    def test_baseline_check_cli_with_canonical_export(self) -> None:
        export_dir = REPO_ROOT / "01_raw_exports" / "cointracking" / "2023-08-05_full_export"
        expected_dir = REPO_ROOT / "03_analysis" / "reconciliation"
        expected_summary = read_json(expected_dir / "baseline_summary.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            result = run_script(
                "baseline_check.py",
                "--export-dir",
                str(export_dir),
                "--out-dir",
                str(out_dir),
            )

            summary = json.loads(result.stdout)
            generated_summary = read_json(out_dir / "baseline_summary.json")
            generated_asset_snapshot = read_dict_rows(out_dir / "baseline_asset_snapshot.csv")
            generated_reconciliation = read_dict_rows(out_dir / "baseline_exchange_reconciliation.csv")
            generated_negative_balances = read_dict_rows(out_dir / "baseline_negative_balances.csv")
            generated_source_activity = read_dict_rows(out_dir / "baseline_source_activity.csv")
            generated_cad_flow = read_dict_rows(out_dir / "baseline_cad_flow_by_type.csv")
            generated_cad_by_exchange = read_dict_rows(out_dir / "baseline_cad_balance_by_exchange.csv")

        self.assertEqual("2023-08-05 08:34:04", summary["latest_transaction_timestamp"])
        self.assertEqual(31021, summary["trade_table_rows"])
        self.assertEqual(78, summary["asset_reconciliation_assets"])
        self.assertEqual("-15654.23000000", summary["ending_cad_balance"])
        self.assertEqual("34215.69000000", summary["cad_bought_total"])
        self.assertEqual("49869.92000000", summary["cad_sold_total"])
        self.assertEqual("156.26000000", summary["cad_fee_total"])
        self.assertEqual("0.00000000", summary["max_asset_difference"])

        self.assertEqual(expected_summary["trade_table_rows"], generated_summary["trade_table_rows"])
        self.assertEqual(expected_summary["current_balance_rows"], generated_summary["current_balance_rows"])
        self.assertEqual(expected_summary["balance_by_exchange_rows"], generated_summary["balance_by_exchange_rows"])
        self.assertEqual(expected_summary["validate_transactions_rows"], generated_summary["validate_transactions_rows"])
        self.assertEqual(expected_summary["missing_transactions_rows"], generated_summary["missing_transactions_rows"])
        self.assertEqual(expected_summary["duplicate_transactions_rows"], generated_summary["duplicate_transactions_rows"])
        self.assertEqual(expected_summary["negative_balance_rows"], generated_summary["negative_balance_rows"])
        self.assertEqual(expected_summary["negative_balances"], generated_summary["negative_balances"])
        self.assertEqual(expected_summary["asset_reconciliation_assets"], generated_summary["asset_reconciliation_assets"])
        self.assertEqual(expected_summary["max_asset_difference"], generated_summary["max_asset_difference"])
        self.assertEqual(expected_summary["max_asset_difference_ticker"], generated_summary["max_asset_difference_ticker"])
        self.assertEqual(expected_summary["trade_table_sources"], generated_summary["trade_table_sources"])
        self.assertEqual(expected_summary["balance_by_exchange_sources"], generated_summary["balance_by_exchange_sources"])
        self.assertEqual(expected_summary["source_activity_rows"], generated_summary["source_activity_rows"])
        self.assertEqual(expected_summary["ending_cad_balance"], generated_summary["ending_cad_balance"])
        self.assertEqual(expected_summary["cad_bought_total"], generated_summary["cad_bought_total"])
        self.assertEqual(expected_summary["cad_sold_total"], generated_summary["cad_sold_total"])
        self.assertEqual(expected_summary["cad_fee_total"], generated_summary["cad_fee_total"])
        self.assertEqual(expected_summary["cad_net_balance_impact"], generated_summary["cad_net_balance_impact"])
        self.assertEqual(expected_summary["cad_net_after_fees"], generated_summary["cad_net_after_fees"])
        self.assertEqual(
            read_dict_rows(expected_dir / "baseline_asset_snapshot.csv"),
            generated_asset_snapshot,
        )
        self.assertEqual(
            read_dict_rows(expected_dir / "baseline_exchange_reconciliation.csv"),
            generated_reconciliation,
        )
        self.assertEqual(
            read_dict_rows(expected_dir / "baseline_negative_balances.csv"),
            generated_negative_balances,
        )
        self.assertEqual(
            read_dict_rows(expected_dir / "baseline_source_activity.csv"),
            generated_source_activity,
        )
        self.assertEqual(
            read_dict_rows(expected_dir / "baseline_cad_flow_by_type.csv"),
            generated_cad_flow,
        )
        self.assertEqual(
            read_dict_rows(expected_dir / "baseline_cad_balance_by_exchange.csv"),
            generated_cad_by_exchange,
        )

    def test_source_manifest_cli_generates_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source" / "raw"
            source_dir.mkdir(parents=True)
            (source_dir / "payload.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            output = Path(tmpdir) / "manifest.csv"

            result = run_script(
                "source_manifest.py",
                "--source-dir",
                str(source_dir),
                "--output",
                str(output),
            )
            rows = read_dict_rows(output)

        self.assertEqual(1, len(rows))
        self.assertEqual("payload.csv", rows[0]["filename"])
        self.assertEqual("8", rows[0]["size_bytes"])
        self.assertEqual(hashlib.sha256(b"a,b\n1,2\n").hexdigest(), rows[0]["sha256"])
        self.assertIn("Wrote manifest with 1 file(s)", result.stdout)

    def test_source_manifest_cli_rejects_non_raw_directory_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            (source_dir / "payload.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            output = Path(tmpdir) / "manifest.csv"

            result = run_script(
                "source_manifest.py",
                "--source-dir",
                str(source_dir),
                "--output",
                str(output),
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("raw export folder", result.stderr)

    def test_binance_unwrap_cli_extracts_and_combines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source" / "raw"
            normalized_dir = Path(tmpdir) / "02_working" / "normalized"
            source_dir.mkdir(parents=True)
            normalized_dir.mkdir(parents=True)
            (source_dir / "Binance Transactions 2024.csv").write_text(
                "User ID,Time,Account,Operation,Coin,Change,Remark\n"
                "1,2024-09-10 12:09:17,Spot,Deposit,USDT,10,test\n",
                encoding="utf-8",
            )
            (source_dir / "Binance Transactions 2023.csv").write_text(
                "User ID,Time,Account,Operation,Coin,Change,Remark\n"
                "1,2023-08-06 08:34:03,Spot,Deposit,USDT,5,test\n",
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
            archive_exists = archive_path.exists()
            combined_exists = (
                normalized_dir / "binance" / "combined" / "binance_transactions_combined.csv"
            ).exists()

        self.assertEqual(1, summary["zip_files_processed"])
        self.assertEqual("2023-08-06 08:34:03", summary["earliest_timestamp"])
        self.assertFalse(archive_exists)
        self.assertTrue(combined_exists)

    def test_round_scaffold_cli_creates_temp_repo_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            copy_script_to_repo("round_scaffold.py", repo_root)
            copy_script_to_repo("script_common.py", repo_root)
            scripts_dir = repo_root / "06_scripts"
            (repo_root / "02_working" / "verification").mkdir(parents=True)
            (repo_root / "05_outputs" / "logs").mkdir(parents=True)

            result = run_script(
                "round_scaffold.py",
                "--round-id",
                "round_01",
                "--phase",
                "baseline_repair",
                "--source",
                "shakepay",
                cwd=repo_root,
                scripts_dir=scripts_dir,
            )
            readme = repo_root / "02_working" / "verification" / "round_01" / "README.md"
            round_log = repo_root / "05_outputs" / "logs" / "round_log.csv"
            rows = read_dict_rows(round_log)
            readme_exists = readme.exists()
            round_log_exists = round_log.exists()

        self.assertTrue(readme_exists)
        self.assertTrue(round_log_exists)
        self.assertEqual("round_01", rows[0]["round_id"])
        self.assertEqual("baseline_repair", rows[0]["phase"])
        self.assertEqual("02_working/verification/round_01", rows[0]["exports_captured"])
        self.assertIn("Verification folder:", result.stdout)
        self.assertIn("Round log:", result.stdout)

    def test_round_scaffold_cli_rejects_invalid_round_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            copy_script_to_repo("round_scaffold.py", repo_root)
            copy_script_to_repo("script_common.py", repo_root)
            scripts_dir = repo_root / "06_scripts"

            result = run_script(
                "round_scaffold.py",
                "--round-id",
                "../outside",
                "--phase",
                "baseline_repair",
                "--source",
                "shakepay",
                cwd=repo_root,
                scripts_dir=scripts_dir,
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("single path segment without traversal", result.stderr)

    def test_overlap_check_cli_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline_dir = Path(tmpdir) / "baseline"
            baseline_dir.mkdir()
            candidate = Path(tmpdir) / "candidate.csv"
            out_dir = Path(tmpdir) / "out"
            (baseline_dir / "Trade Table.csv").write_text(
                (
                    "Type,Buy,Cur.,Sell,Cur.,Fee,Cur.,Exchange,Group,Comment,Date,LPN,Tx-ID\n"
                    "Trade,1.0,BTC,10.0,CAD,0.5,CAD,Coinbase,,,2023-08-05 08:34:04,,tx-1\n"
                ),
                encoding="utf-8",
            )
            candidate.write_text(
                (
                    "Type,Buy,Cur.,Sell,Cur.,Fee,Cur.,Exchange,Group,Comment,Date,Tx-ID\n"
                    "Trade,2.0,ETH,20.0,CAD,0.1,CAD,Coinbase,,,2023-08-05 08:35:04,tx-2\n"
                ),
                encoding="utf-8",
            )

            result = run_script(
                "overlap_check.py",
                "--baseline-export-dir",
                str(baseline_dir),
                "--candidate",
                str(candidate),
                "--out-dir",
                str(out_dir),
            )
            summary = json.loads(result.stdout)
            summary_exists = (out_dir / "overlap_summary.json").exists()

        self.assertEqual("pass", summary["status"])
        self.assertTrue(summary_exists)

    def test_verification_compare_cli_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            reference_dir = Path(tmpdir) / "reference"
            current_dir = Path(tmpdir) / "current"
            out_dir = Path(tmpdir) / "out"
            reference_dir.mkdir()
            current_dir.mkdir()
            write_csv = lambda path, text: path.write_text(text, encoding="utf-8")
            for directory in [reference_dir, current_dir]:
                write_csv(directory / "Validate Transactions.csv", "Issue\n")
                write_csv(
                    directory / "Missing Transactions.csv",
                    "Type,Amount,Cur.,Fee,Fee Cur.,Value in CAD,Exchange,Trade Group,Comment,Trade ID,Date,Match,\n",
                )
                write_csv(
                    directory / "Duplicate Transactions.csv",
                    "\",# of duplicates,Type,Exchange,Exchange ID,Buy,Sell,Trade Group,Tx ID,Tx Date\n",
                )
                write_csv(
                    directory / "Current Balance.csv",
                    "Ticker,Name,Type,Amount,Value in CAD\nBTC,Bitcoin,Coin,1.00000000,10.0\n",
                )
                write_csv(
                    directory / "Balance by Exchange.csv",
                    "Amount,Currency,Current value in CAD,Current value in BTC,Exchange\n1.00000000,BTC,10.0,0.1,Coinbase\n",
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
            summary_exists = (out_dir / "verification_summary.json").exists()

        self.assertEqual("review_balance_changes", summary["gate_suggestion"])
        self.assertTrue(summary_exists)
