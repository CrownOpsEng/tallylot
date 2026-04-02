from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import wallet_inventory
from tests.support.helpers import REPO_ROOT, write_csv


class WalletInventoryTests(unittest.TestCase):
    def test_profile_wallet_identifiers_extracts_ledger_live_accounts(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "ledger-live-main" / "2026-03"

        evidence, issues, summary = wallet_inventory.profile_wallet_identifiers("ledger-live-main", raw_dir, adapter_name="ledger_live")

        wallet_ids = {row["wallet_id"] for row in evidence}
        self.assertIn(
            "btc_xpub:xpub6A111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
            wallet_ids,
        )
        self.assertIn("evm_address:0x2222222222222222222222222222222222222222", wallet_ids)
        self.assertIn(
            "cardano_account_key:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            wallet_ids,
        )
        self.assertEqual([], issues)
        self.assertEqual("passed", summary["status"])
        self.assertEqual("ledger_live", summary["adapter"])

    def test_profile_wallet_identifiers_extracts_metamask_app_accounts_and_snap_addresses(self) -> None:
        payload = {
            "metamask": {
                "internalAccounts": {
                    "accounts": {
                        "acc-1": {
                            "address": "0x1111111111111111111111111111111111111111",
                            "metadata": {"name": "Account 1", "keyring": {"type": "HD Key Tree"}},
                        },
                        "acc-2": {
                            "address": "0x2222222222222222222222222222222222222222",
                            "metadata": {"name": "Ledger 1", "keyring": {"type": "Ledger Hardware"}},
                        },
                    }
                },
                "identities": {
                    "TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA": {"name": ""},
                    "bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": {"name": ""},
                    "F11111111111111111111111111111111111111111": {"name": ""},
                },
            }
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            (raw_dir / "MetaMask state logs.json").write_text(json.dumps(payload), encoding="utf-8")

            evidence, issues, summary = wallet_inventory.profile_wallet_identifiers("MetaMask app", raw_dir)

        wallet_ids = {row["wallet_id"] for row in evidence}
        self.assertIn("evm_address:0x1111111111111111111111111111111111111111", wallet_ids)
        self.assertIn("evm_address:0x2222222222222222222222222222222222222222", wallet_ids)
        self.assertIn("btc_address:bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", wallet_ids)
        self.assertIn("tron_address:TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", wallet_ids)
        self.assertIn("solana_address:F11111111111111111111111111111111111111111", wallet_ids)
        self.assertEqual([], issues)
        self.assertEqual("passed", summary["status"])

    def test_build_wallet_inventory_includes_gtrade_alias_issue(self) -> None:
        inventory_rows, evidence_rows, issue_rows, summary = wallet_inventory.build_wallet_inventory(REPO_ROOT)

        self.assertTrue(any(row["wallet_id"] == "address_alias:bb4d" for row in evidence_rows))
        self.assertTrue(any(row["issue_kind"] == "partial_identifier_only" for row in issue_rows))
        self.assertGreater(summary["wallet_count"], 5)

    def test_refresh_wallet_inventory_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "inventory"
            summary = wallet_inventory.refresh_wallet_inventory(REPO_ROOT, out_dir=out_dir)

            with (out_dir / "wallet_inventory.csv").open(encoding="utf-8") as handle:
                inventory_rows = list(handle)
            with (out_dir / "wallet_inventory_evidence.csv").open(encoding="utf-8") as handle:
                evidence_rows = list(handle)
            issues = json.loads((out_dir / "wallet_inventory_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(str(out_dir / "wallet_inventory.csv"), summary["inventory_path"])
        self.assertTrue(any("wallet_id" in line for line in inventory_rows[:1]))
        self.assertTrue(any("source,capture_path" in line for line in evidence_rows[:1]))
        self.assertEqual(summary["wallet_count"], issues["wallet_count"])

    def test_profile_wallet_identifiers_flags_empty_chain_scoped_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            write_csv(raw_dir / "export-empty.csv", ["Transaction Hash", "DateTime (UTC)"], [])

            evidence, issues, summary = wallet_inventory.profile_wallet_identifiers("eth-metamask1", raw_dir)

        self.assertEqual([], evidence)
        self.assertEqual("needs_review", summary["status"])
        self.assertTrue(any(row["issue_kind"] == "missing_identifier" for row in issues))

    def test_profile_wallet_identifiers_resolves_adapter_from_profile_without_hint(self) -> None:
        raw_dir = REPO_ROOT / "01_raw_exports" / "external" / "near-main" / "2026-03"

        evidence, issues, summary = wallet_inventory.profile_wallet_identifiers("capture-near", raw_dir)

        self.assertTrue(any(row["identifier_kind"] == "near_account" for row in evidence))
        self.assertEqual([], issues)
        self.assertEqual("near", summary["adapter"])
