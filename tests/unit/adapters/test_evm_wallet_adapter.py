from __future__ import annotations

import json
from pathlib import Path

from crypto_reconciliation.adapters.sources.evm_wallet.adapter import EvmWalletAdapter
from tests.support.services import build_source_profile


def test_evm_wallet_adapter_extracts_accounts_and_identity_records(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    path = raw_dir / "wallet-state.json"
    path.write_text(
        json.dumps(
            {
                "wallet_state": {
                    "internalAccounts": {
                        "accounts": {
                            "one": {
                                "address": "0x1111111111111111111111111111111111111111",
                                "metadata": {
                                    "name": "Primary",
                                    "keyring": {"type": "HD Key Tree"},
                                },
                            }
                        }
                    },
                    "identities": {
                        "Taaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": {"name": "Tron Wallet"},
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    records, issues = EvmWalletAdapter().extract_wallet_inventory(
        "evm-wallets",
        raw_dir,
        build_source_profile(adapter_id="evm_wallet", source="evm-wallets", raw_dir=str(raw_dir)),
    )

    assert not issues
    assert {record.identifier_kind for record in records} == {"evm_address", "tron_address"}
    assert {record.account_label for record in records} == {"Primary", "Tron Wallet"}


def test_evm_wallet_adapter_reads_metamask_wrapped_state_and_bitcoin_identity(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    path = raw_dir / "wallet-state.json"
    path.write_text(
        json.dumps(
            {
                "metamask": {
                    "internalAccounts": {
                        "accounts": {
                            "one": {
                                "address": "0x1111111111111111111111111111111111111111",
                                "metadata": {"name": "Primary", "keyring": {"type": "Ledger Hardware"}},
                            }
                        }
                    },
                    "identities": {
                        "bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": {"name": "BTC Wallet"},
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    records, issues = EvmWalletAdapter().extract_wallet_inventory(
        "evm-wallets",
        raw_dir,
        build_source_profile(adapter_id="evm_wallet", source="evm-wallets", raw_dir=str(raw_dir)),
    )

    assert not issues
    assert {record.identifier_kind for record in records} == {"evm_address", "btc_address"}
    assert {record.account_label for record in records} == {"Primary", "BTC Wallet"}
