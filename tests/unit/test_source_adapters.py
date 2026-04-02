from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import normalize_source
import pipeline_common
import source_adapters
from tests.support.helpers import REPO_ROOT


class SourceAdapterTests(unittest.TestCase):
    def test_get_adapter_resolves_supported_and_stub_sources(self) -> None:
        self.assertEqual("coinbase", source_adapters.get_adapter("Coinbase").name)
        self.assertTrue(source_adapters.get_adapter("Coinbase").supported)
        self.assertEqual("wealthsimple", source_adapters.get_adapter("WealthSimple").name)
        self.assertFalse(source_adapters.get_adapter("WealthSimple").supported)

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

    def test_build_source_profile_smoke_covers_major_sources(self) -> None:
        cases = [
            ("Coinbase", REPO_ROOT / "01_raw_exports" / "external" / "coinbase" / "raw"),
            ("WealthSimple", REPO_ROOT / "01_raw_exports" / "external" / "wealthsimple" / "raw"),
            ("Binance", REPO_ROOT / "01_raw_exports" / "external" / "binance" / "raw"),
            ("BSC MetaMask Wallet", REPO_ROOT / "01_raw_exports" / "external" / "metamask" / "raw"),
            ("Shakepay", REPO_ROOT / "01_raw_exports" / "external" / "shakepay" / "raw"),
            ("Ledger Live", REPO_ROOT / "01_raw_exports" / "external" / "ledger live" / "raw"),
            ("NEAR Wallet", REPO_ROOT / "01_raw_exports" / "external" / "near" / "raw"),
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

    def test_normalize_source_cache_invalidates_when_exception_decisions_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_dir = root / "wealthsimple" / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "activities.csv").write_text(
                "transaction_date,settlement_date,account_id,activity_type\n2024-01-01,2024-01-02,acct,deposit\n",
                encoding="utf-8",
            )
            out_dir = root / "normalized"

            first = normalize_source.normalize_source("WealthSimple", raw_dir, out_dir)
            summary_path = out_dir / "normalization_summary.json"
            first_summary = pipeline_common.read_profile(summary_path)
            manifest_fingerprint = str(first_summary["manifest_fingerprint"])
            decisions_path = root / "exception_decisions.csv"
            decisions_path.write_text(
                (
                    "manifest_fingerprint,event_id,resolution_status,resolution_note\n"
                    f"{manifest_fingerprint},wealthsimple:adapter_not_implemented,accepted,known gap\n"
                ),
                encoding="utf-8",
            )

            second = normalize_source.normalize_source(
                "WealthSimple",
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
