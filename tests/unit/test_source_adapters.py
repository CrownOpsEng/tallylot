from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import normalize_source
import pipeline_common
import source_adapters
from tests.support.helpers import REPO_ROOT


class SourceAdapterTests(unittest.TestCase):
    def test_get_adapter_resolves_supported_sources(self) -> None:
        self.assertEqual("coinbase", source_adapters.get_adapter("Coinbase").name)
        self.assertTrue(source_adapters.get_adapter("Coinbase").supported)
        self.assertEqual("wealthsimple", source_adapters.get_adapter("WealthSimple").name)
        self.assertTrue(source_adapters.get_adapter("WealthSimple").supported)
        self.assertEqual("binance", source_adapters.get_adapter("Binance").name)
        self.assertTrue(source_adapters.get_adapter("Binance").supported)
        self.assertEqual("crypto_com", source_adapters.get_adapter("Crypto.com").name)
        self.assertTrue(source_adapters.get_adapter("Crypto.com").supported)
        self.assertEqual("shakepay", source_adapters.get_adapter("Shakepay").name)
        self.assertTrue(source_adapters.get_adapter("Shakepay").supported)
        self.assertEqual("ledger_live", source_adapters.get_adapter("ledger-live-main").name)
        self.assertTrue(source_adapters.get_adapter("ledger-live-main").supported)
        self.assertEqual("near", source_adapters.get_adapter("near-main").name)
        self.assertTrue(source_adapters.get_adapter("near-main").supported)
        self.assertEqual("gtrade", source_adapters.get_adapter("GTrade 1CT").name)
        self.assertTrue(source_adapters.get_adapter("GTrade 1CT").supported)
        self.assertEqual("evm_explorer", source_adapters.get_adapter("bsc-metamask1").name)
        self.assertTrue(source_adapters.get_adapter("bsc-metamask1").supported)
        self.assertEqual("ledger_live", source_adapters.get_adapter("Ledger Live").name)
        self.assertEqual("near", source_adapters.get_adapter("NEAR Wallet").name)

    def test_get_adapter_can_resolve_from_profile_before_source_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            (raw_dir / "activities-export-2026-03-23.csv").write_text(
                "transaction_date,settlement_date,account_id,account_type,activity_type,activity_sub_type\n"
                "2023-09-21,,acct,Crypto,Trade,BUY\n",
                encoding="utf-8",
            )

            profile = pipeline_common.build_source_profile(
                source="Future Broker",
                raw_dir=raw_dir,
                adapter_name="generic",
                adapter_supported=False,
            )

        self.assertEqual("wealthsimple", source_adapters.get_adapter("Future Broker", profile).name)

    def test_load_exception_decisions_filters_by_manifest_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "exception_decisions.csv"
            path.write_text(
                (
                    "manifest_fingerprint,event_id,resolution_status,resolution_note\n"
                    "abc,evt-1,accepted,handled once\n"
                    "other,evt-2,accepted,ignore\n"
                ),
                encoding="utf-8",
            )

            decisions = source_adapters.load_exception_decisions(path, "abc")

        self.assertEqual({"resolution_status": "accepted", "resolution_note": "handled once"}, decisions["evt-1"])
        self.assertNotIn("evt-2", decisions)

    def test_coinbase_adapter_normalizes_repo_exports(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "coinbase" / "raw"
        adapter = source_adapters.get_adapter("Coinbase")
        profile = pipeline_common.build_source_profile(
            source="Coinbase",
            raw_dir=raw_dir,
            adapter_name=adapter.name,
            adapter_supported=adapter.supported,
        )

        result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertEqual(82, len(result.canonical_events))
        self.assertGreaterEqual(len(result.canonical_balances), 10)
        self.assertEqual([], result.exceptions)
        self.assertEqual(
            "2025-10-17 13:38:17",
            next(
                row["timestamp"]
                for row in result.canonical_events
                if row["event_id"] == "coinbase-asset-migration-68f246c9a0081dc3b61e422c-68f246c95d5ca606c968fd16"
            ),
        )

    def test_wealthsimple_adapter_normalizes_repo_exports(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "wealthsimple" / "raw"
        adapter = source_adapters.get_adapter("WealthSimple")
        profile = pipeline_common.build_source_profile(
            source="WealthSimple",
            raw_dir=raw_dir,
            adapter_name=adapter.name,
            adapter_supported=adapter.supported,
        )

        result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertEqual(26, len(result.canonical_events))
        self.assertEqual([], result.exceptions)
        self.assertEqual("Withdrawal", result.canonical_events[0]["event_kind"])
        self.assertEqual("Trade", result.canonical_events[2]["event_kind"])
        self.assertTrue(all(row["render_match_window_seconds"] == "86399" for row in result.canonical_events))

    def test_crypto_com_adapter_normalizes_repo_exports(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "crypto.com" / "raw"
        adapter = source_adapters.get_adapter("Crypto.com")
        profile = pipeline_common.build_source_profile(
            source="Crypto.com",
            raw_dir=raw_dir,
            adapter_name=adapter.name,
            adapter_supported=adapter.supported,
        )

        result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertEqual(12, len(result.canonical_events))
        self.assertEqual([], result.exceptions)
        self.assertEqual(
            {"Deposit": 4, "Trade": 4, "Withdrawal": 4},
            {
                event_kind: sum(1 for row in result.canonical_events if row["event_kind"] == event_kind)
                for event_kind in {"Deposit", "Trade", "Withdrawal"}
            },
        )

    def test_shakepay_adapter_normalizes_repo_exports(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "shakepay" / "raw"
        adapter = source_adapters.get_adapter("Shakepay")
        profile = pipeline_common.build_source_profile(
            source="Shakepay",
            raw_dir=raw_dir,
            adapter_name=adapter.name,
            adapter_supported=adapter.supported,
        )

        result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertEqual(1895, len(result.canonical_events))
        self.assertEqual(2, len(result.canonical_balances))
        self.assertEqual([], result.exceptions)
        self.assertEqual("Reward / Bonus", result.canonical_events[0]["event_kind"])
        self.assertEqual("shakingsats", result.canonical_events[0]["description"])
        self.assertEqual("2022-01-04 18:19:41", result.canonical_events[0]["timestamp"])

    def test_ledger_live_adapter_normalizes_repo_exports(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "ledger-live-main" / "2026-03"
        adapter = source_adapters.get_adapter("ledger-live-main")
        profile = pipeline_common.build_source_profile(
            source="ledger-live-main",
            raw_dir=raw_dir,
            adapter_name=adapter.name,
            adapter_supported=adapter.supported,
        )

        result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertEqual(22, len(result.canonical_events))
        self.assertEqual([], result.exceptions)
        kinds = {row["event_kind"] for row in result.canonical_events}
        self.assertIn("Trade", kinds)
        self.assertIn("Expense (non taxable)", kinds)
        self.assertIn("Withdrawal", kinds)

    def test_near_adapter_normalizes_repo_exports(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "near-main" / "2026-03"
        adapter = source_adapters.get_adapter("near-main")
        profile = pipeline_common.build_source_profile(
            source="near-main",
            raw_dir=raw_dir,
            adapter_name=adapter.name,
            adapter_supported=adapter.supported,
        )

        result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertEqual(10, len(result.canonical_events))
        self.assertEqual([], result.exceptions)
        self.assertTrue(any(row["source"] == "near-main - Staking" for row in result.canonical_events))
        self.assertTrue(any(row["event_kind"] == "Airdrop" for row in result.canonical_events))
        self.assertIn(
            "2022-01-30 09:31:41",
            {row["timestamp"] for row in result.canonical_events},
        )

    def test_binance_adapter_converts_filename_timezone_to_utc(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "binance" / "raw"
        adapter = source_adapters.get_adapter("Binance")
        profile = pipeline_common.build_source_profile(
            source="Binance",
            raw_dir=raw_dir,
            adapter_name=adapter.name,
            adapter_supported=adapter.supported,
        )

        result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertIn(
            "2023-09-21 00:20:55",
            {
                row["timestamp"]
                for row in result.canonical_events
                if row["raw_file"] == "Binance-Spot-Trade-History-202603230406(UTC--6)_5d63c10c.csv"
                and row["raw_row_ref"] == "row:2"
            },
        )

    def test_evm_explorer_adapter_normalizes_bsc_repo_exports(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "bsc-metamask1" / "2026-03"
        adapter = source_adapters.get_adapter("bsc-metamask1")
        profile = pipeline_common.build_source_profile(
            source="bsc-metamask1",
            raw_dir=raw_dir,
            adapter_name=adapter.name,
            adapter_supported=adapter.supported,
        )

        result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertEqual(31, len(result.canonical_events))
        self.assertEqual([], result.exceptions)
        self.assertTrue(any(row["event_kind"] == "Trade" for row in result.canonical_events))
        self.assertTrue(any(row["event_kind"] == "Staking" for row in result.canonical_events))
        self.assertTrue(any(row["fee_amount"] for row in result.canonical_events))
        self.assertLess(sum(1 for row in result.canonical_events if row["event_kind"] == "Other Fee"), 10)

    def test_evm_explorer_adapter_surfaces_polygon_review_rows_without_importing_them(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "polygon-metamask1" / "2026-03"
        adapter = source_adapters.get_adapter("polygon-metamask1")
        profile = pipeline_common.build_source_profile(
            source="polygon-metamask1",
            raw_dir=raw_dir,
            adapter_name=adapter.name,
            adapter_supported=adapter.supported,
        )

        result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertEqual(17, len(result.canonical_events))
        self.assertEqual(5, len(result.exceptions))
        self.assertTrue(all(row["exception_kind"] == "review_required" for row in result.exceptions))
        self.assertTrue(any("suspicious NFT airdrop" in row["message"] for row in result.exceptions))
        self.assertTrue(any(row["fee_amount"] for row in result.canonical_events))

    def test_evm_explorer_adapter_surfaces_eth_gala_review_rows_without_importing_them(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "eth-gala1" / "2026-03"
        adapter = source_adapters.get_adapter("eth-gala1")
        profile = pipeline_common.build_source_profile(
            source="eth-gala1",
            raw_dir=raw_dir,
            adapter_name=adapter.name,
            adapter_supported=adapter.supported,
        )

        result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertEqual(11, len(result.canonical_events))
        self.assertEqual(3, len(result.exceptions))
        self.assertTrue(all(row["exception_kind"] == "review_required" for row in result.exceptions))
        self.assertTrue(any("suspicious NFT airdrop" in row["message"] for row in result.exceptions))
        self.assertTrue(any(row["fee_amount"] for row in result.canonical_events))

    def test_gtrade_adapter_surfaces_report_limits_without_guessing(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "gtrade" / "raw"
        adapter = source_adapters.get_adapter("GTrade 1CT")
        profile = pipeline_common.build_source_profile(
            source="GTrade 1CT",
            raw_dir=raw_dir,
            adapter_name=adapter.name,
            adapter_supported=adapter.supported,
        )

        result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertEqual(3, len(result.canonical_events))
        self.assertEqual(3, len(result.exceptions))
        self.assertTrue(all(row["event_kind"] == "Derivatives / Futures Loss" for row in result.canonical_events))
        self.assertTrue(all(row["exception_kind"] == "unsupported_row" for row in result.exceptions))

    def test_binance_adapter_handles_supported_and_review_required_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            (raw_dir / "Binance-Spot-Trade-History-202603230406(UTC--6)_abcd.csv").write_text(
                (
                    "Time,Pair,Side,Price,Executed,Amount,Fee\n"
                    "23-09-20 18:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n"
                ),
                encoding="utf-8",
            )
            (raw_dir / "Binance-Deposit-History-202603230411(UTC--6)_abcd.csv").write_text(
                (
                    "Time,Coin,Network,Amount,Address,TXID,Status\n"
                    "23-05-06 23:05:55,USDT,MATIC,125.564991,addr,tx-dep,Completed\n"
                ),
                encoding="utf-8",
            )
            (raw_dir / "Binance-Withdraw-History-202603230412(UTC--6)_abcd.csv").write_text(
                (
                    "Time,Coin,Network,Amount,Fee,Address,TXID,Status\n"
                    "23-09-20 22:25:57,HNT,SOL,12.013,0.11,addr,tx-wd,Completed\n"
                ),
                encoding="utf-8",
            )
            (raw_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv").write_text(
                (
                    "User ID,Time,Account,Operation,Coin,Change,Remark\n"
                    "1,23-08-06 02:34:03,Spot,ETH 2.0 Staking Rewards,BETH,0.00000599,\n"
                    "1,23-09-20 18:46:46,Spot,Small Assets Exchange BNB,ETH,-0.00005643,ETH to BNB\n"
                    "1,23-09-20 18:46:46,Spot,Small Assets Exchange BNB,BNB,0.00041767,ETH to BNB\n"
                    "1,23-09-20 18:17:41,USD-M Futures,Transfer Between Spot Account and UM Futures Account,USDT,-43.90477684,\n"
                    "1,23-09-20 18:17:41,Spot,Transfer Between Spot Account and UM Futures Account,USDT,43.90477684,\n"
                    "1,21-05-11 00:44:33,Spot,Binance Convert,ETH,0.03158115,\n"
                ),
                encoding="utf-8",
            )

            adapter = source_adapters.get_adapter("Binance")
            profile = pipeline_common.build_source_profile(
                source="Binance",
                raw_dir=raw_dir,
                adapter_name=adapter.name,
                adapter_supported=adapter.supported,
            )
            result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertEqual(5, len(result.canonical_events))
        self.assertEqual(1, len(result.exceptions))
        kinds = [row["event_kind"] for row in result.canonical_events]
        self.assertIn("Trade", kinds)
        self.assertIn("Deposit", kinds)
        self.assertIn("Withdrawal", kinds)
        self.assertIn("Staking", kinds)

    def test_binance_convert_date_updated_covers_transaction_history_one_second_skew(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            (raw_dir / "Binance-Convert-Order-History-202603230441(UTC--6)_abcd.csv").write_text(
                (
                    "Time,Wallet,Pair,Type,Sell,Buy,Price,Inverse Price,Date Updated,Status\n"
                    "21-05-11 00:44:32,SPOT,ETHBUSD,Instant,124.60184573 BUSD,0.03158115 ETH,x,x,21-05-11 00:44:33,Successful\n"
                ),
                encoding="utf-8",
            )
            (raw_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv").write_text(
                (
                    "User ID,Time,Account,Operation,Coin,Change,Remark\n"
                    "1,21-05-11 00:44:33,Spot,Binance Convert,ETH,0.03158115,\n"
                ),
                encoding="utf-8",
            )

            adapter = source_adapters.get_adapter("Binance")
            profile = pipeline_common.build_source_profile(
                source="Binance",
                raw_dir=raw_dir,
                adapter_name=adapter.name,
                adapter_supported=adapter.supported,
            )
            result = adapter.normalize(raw_dir, profile, exception_decisions={})

        self.assertEqual(1, len(result.canonical_events))
        self.assertEqual(0, len(result.exceptions))

    def test_build_source_profile_smoke_covers_major_sources(self) -> None:
        cases = [
            ("Coinbase", REPO_ROOT / "01_raw_exports" / "external" / "coinbase" / "raw"),
            ("WealthSimple", REPO_ROOT / "01_raw_exports" / "external" / "wealthsimple" / "raw"),
            ("Binance", REPO_ROOT / "01_raw_exports" / "external" / "binance" / "raw"),
            ("bsc-metamask1", REPO_ROOT / "01_raw_exports" / "external" / "bsc-metamask1" / "2026-03"),
            ("Crypto.com", REPO_ROOT / "01_raw_exports" / "external" / "crypto.com" / "raw"),
            ("GTrade 1CT", REPO_ROOT / "01_raw_exports" / "external" / "gtrade" / "raw"),
            ("Shakepay", REPO_ROOT / "01_raw_exports" / "external" / "shakepay" / "raw"),
            ("ledger-live-main", REPO_ROOT / "01_raw_exports" / "external" / "ledger-live-main" / "2026-03"),
            ("near-main", REPO_ROOT / "01_raw_exports" / "external" / "near-main" / "2026-03"),
        ]

        for source, raw_dir in cases:
            with self.subTest(source=source):
                adapter = source_adapters.get_adapter(source)
                profile = pipeline_common.build_source_profile(
                    source=source,
                    raw_dir=raw_dir,
                    adapter_name=adapter.name,
                    adapter_supported=adapter.supported,
                )
                self.assertTrue(profile.file_inventory)
                self.assertTrue(profile.manifest_fingerprint)

    def test_timezone_validation_passes_for_repo_supported_sources(self) -> None:
        cases = [
            ("Coinbase", REPO_ROOT / "01_raw_exports" / "external" / "coinbase" / "raw"),
            ("WealthSimple", REPO_ROOT / "01_raw_exports" / "external" / "wealthsimple" / "raw"),
            ("Binance", REPO_ROOT / "01_raw_exports" / "external" / "binance" / "raw"),
            ("bsc-metamask1", REPO_ROOT / "01_raw_exports" / "external" / "bsc-metamask1" / "2026-03"),
            ("Crypto.com", REPO_ROOT / "01_raw_exports" / "external" / "crypto.com" / "raw"),
            ("Shakepay", REPO_ROOT / "01_raw_exports" / "external" / "shakepay" / "raw"),
            ("ledger-live-main", REPO_ROOT / "01_raw_exports" / "external" / "ledger-live-main" / "2026-03"),
            ("near-main", REPO_ROOT / "01_raw_exports" / "external" / "near-main" / "2026-03"),
            ("GTrade 1CT", REPO_ROOT / "01_raw_exports" / "external" / "gtrade" / "raw"),
        ]

        for source, raw_dir in cases:
            with self.subTest(source=source):
                adapter = source_adapters.get_adapter(source)
                profile = pipeline_common.build_source_profile(
                    source=source,
                    raw_dir=raw_dir,
                    adapter_name=adapter.name,
                    adapter_supported=adapter.supported,
                )
                summary, issues = adapter.validate_profile_timezones(profile)
                self.assertEqual("passed", summary["status"])
                self.assertEqual([], issues)

    def test_normalize_source_rejects_ambiguous_timezone_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "binance" / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "Binance-Spot-Trade-History.csv").write_text(
                (
                    "Time,Pair,Side,Price,Executed,Amount,Fee\n"
                    "23-09-20 18:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n"
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Timezone validation failed"):
                normalize_source.normalize_source("Binance", raw_dir, Path(tmpdir) / "normalized")

    def test_normalize_source_cache_invalidates_when_exception_decisions_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_dir = root / "future_exchange" / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "payload.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            out_dir = root / "normalized"

            first = normalize_source.normalize_source("Future Exchange", raw_dir, out_dir)
            summary_path = out_dir / "normalization_summary.json"
            first_summary = pipeline_common.read_profile(summary_path)
            manifest_fingerprint = str(first_summary["manifest_fingerprint"])
            decisions_path = root / "exception_decisions.csv"
            decisions_path.write_text(
                (
                    "manifest_fingerprint,event_id,resolution_status,resolution_note\n"
                    f"{manifest_fingerprint},generic:adapter_not_implemented,accepted,known gap\n"
                ),
                encoding="utf-8",
            )

            second = normalize_source.normalize_source(
                "Future Exchange",
                raw_dir,
                out_dir,
                exception_decisions=decisions_path,
            )
            second_summary = pipeline_common.read_profile(summary_path)

        self.assertEqual(1, first["exceptions"])
        self.assertEqual(0, second["exceptions"])
        self.assertNotEqual(
            first_summary["exception_decisions_fingerprint"],
            second_summary["exception_decisions_fingerprint"],
        )

    def test_normalize_source_uses_current_adapter_support_even_with_stale_profile_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "wealthsimple" / "raw"
            out_dir = root / "normalized"
            profile_json = root / "profile.json"
            profile_json.write_text(
                (
                    '{\n'
                    '  "manifest_fingerprint": "stale",\n'
                    '  "adapter": "wealthsimple",\n'
                    '  "adapter_supported": false\n'
                    '}\n'
                ),
                encoding="utf-8",
            )

            summary = normalize_source.normalize_source(
                "WealthSimple",
                raw_dir,
                out_dir,
                profile_json=profile_json,
                force=True,
            )

        self.assertTrue(summary["adapter_supported"])
        self.assertEqual("ready", summary["status"])
