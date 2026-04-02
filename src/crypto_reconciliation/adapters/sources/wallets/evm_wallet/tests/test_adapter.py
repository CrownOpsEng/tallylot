# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
from pathlib import Path

from crypto_reconciliation.adapters.sources.wallets.evm_wallet.adapter import (
    EvmWalletAdapter,
    _account_records,
    _identity_records,
    _network_scope,
    _object_map,
    _wallet_state_root,
)
from crypto_reconciliation.domain.models import FileInventoryEntry
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter
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


def test_evm_wallet_adapter_matches_state_json_inventory_without_source_label() -> None:
    adapter = EvmWalletAdapter()

    score = adapter.match(
        "Unknown Wallet",
        Path("/tmp/raw"),
        (
            FileInventoryEntry(
                relative_path="renamed-state.json",
                suffix=".json",
                sha256="fixture",
                size_bytes=1,
                source_path="/tmp/raw/renamed-state.json",
            ),
        ),
    )

    assert score == 80


def test_evm_wallet_adapter_normalize_returns_wallet_inventory_and_missing_identifier_issue(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "wallet-state.json").write_text(json.dumps({"wallet_state": {}}), encoding="utf-8")

    result = EvmWalletAdapter().normalize(
        build_source_profile(adapter_id="evm_wallet", source="evm-wallets", raw_dir=str(raw_dir)),
        raw_dir,
    )

    assert not result.transactions
    assert not result.wallet_inventory
    assert len(result.issues) == 1
    assert result.issues[0].kind == "missing_identifier"


def test_evm_wallet_adapter_extracts_solana_identity_and_ignores_unknown_identity(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    path = raw_dir / "wallet-state.json"
    path.write_text(
        json.dumps(
            {
                "wallet_state": {
                    "identities": {
                        "F11111111111111111111111111111111111111111": {"name": "Solana Wallet"},
                        "not a wallet identifier": {"name": "Ignore Me"},
                    }
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
    assert [record.identifier_kind for record in records] == ["solana_address"]
    assert [record.network_scope for record in records] == ["solana"]


def test_evm_wallet_adapter_validate_profile_timezones_is_trivially_passed() -> None:
    summary, issues = EvmWalletAdapter().validate_profile_timezones(build_source_profile(adapter_id="evm_wallet"))

    assert summary == {
        "status": "passed",
        "issue_count": 0,
        "rows_with_dates": 0,
        "mode_counts": {},
    }
    assert not issues


def test_account_records_skip_non_wallet_state_shapes() -> None:
    assert not _account_records("wallets", "state.json", {})
    assert not _account_records("wallets", "state.json", {"wallet_state": {"internalAccounts": []}})
    assert not _account_records(
        "wallets",
        "state.json",
        {"wallet_state": {"internalAccounts": {"accounts": []}}},
    )
    assert not _account_records(
        "wallets",
        "state.json",
        {
            "wallet_state": {
                "internalAccounts": {
                    "accounts": {
                        "one": {"address": "", "metadata": {"name": "Ignore Me"}},
                    }
                }
            }
        },
    )


def test_identity_records_skip_non_wallet_state_shapes_and_blank_identifiers() -> None:
    assert not _identity_records("wallets", "state.json", {})
    assert not _identity_records("wallets", "state.json", {"wallet_state": {"identities": []}})
    assert not _identity_records(
        "wallets",
        "state.json",
        {"wallet_state": {"identities": {"": {"name": "Ignore Me"}}}},
    )


def test_wallet_state_helpers_handle_fallback_shapes() -> None:
    assert _network_scope("unknown") == ""
    assert _object_map("not-a-dict") == {}
    assert _wallet_state_root([]) is None
    assert _wallet_state_root({"wallet_state": "not-a-dict"}) is None
    assert _wallet_state_root({"metamask": {"identities": {}}}) == {"identities": {}}


def test_metamask_empty_state_fixture_reports_missing_identifier() -> None:
    raw_dir = fixture_raw_dir("evm_wallet", "missing_state")

    profile, adapter = profile_and_adapter("EVM wallet", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("EVM wallet", raw_dir, profile)

    assert str(profile.adapter_id) == "evm_wallet"
    assert evidence == ()
    assert len(issues) == 1
    assert issues[0].kind == "missing_identifier"


def test_metamask_wallet_inventory_uses_renamed_state_file_without_filename_dependency() -> None:
    raw_dir = fixture_raw_dir("evm_wallet", "wallets")

    profile, adapter = profile_and_adapter("Unknown Wallet", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("Unknown Wallet", raw_dir, profile)

    assert str(profile.adapter_id) == "evm_wallet"
    assert issues == ()
    assert {row.wallet_id for row in evidence} >= {
        "evm_address:0x1111111111111111111111111111111111111111",
        "btc_address:bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }
