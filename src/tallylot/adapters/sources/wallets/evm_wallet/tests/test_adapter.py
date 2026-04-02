from __future__ import annotations

import json
from pathlib import Path

from tallylot.adapters.sources.wallets.evm_wallet import ADAPTER
from tallylot.adapters.sources.wallets.evm_wallet.adapter import (
    _account_records,
    _network_scope,
    _object_map,
    _wallet_state_root,
)
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.ports.source_profiles import FileInventoryEntry
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter
from tests.support.services import build_source_profile


def test_evm_wallet_adapter_extracts_chain_scoped_evm_and_snap_accounts(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "wallet-state.json").write_text(
        json.dumps(
            {
                "wallet_state": {
                    "internalAccounts": {
                        "accounts": {
                            "one": {
                                "address": "0x1111111111111111111111111111111111111111",
                                "type": "eip155:eoa",
                                "scopes": ["eip155:1"],
                                "metadata": {"name": "Primary", "keyring": {"type": "HD Key Tree"}},
                            },
                            "two": {
                                "address": "Taaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                                "type": "tron:eoa",
                                "scopes": ["tron:728126428"],
                                "metadata": {
                                    "name": "Tron Wallet",
                                    "keyring": {"type": "Snap Keyring"},
                                    "snap": {"name": "Tron"},
                                },
                            },
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    records, issues = ADAPTER.extract_location_inventory(
        "evm-wallets",
        raw_dir,
        build_source_profile(adapter_id="evm_wallet", source="evm-wallets", raw_dir=str(raw_dir)),
    )

    assert not issues
    assert {record.identifier_kind for record in records} == {"evm_address", "tron_address"}
    assert {str(record.location_id) for record in records} == {
        "evm:ethereum:0x1111111111111111111111111111111111111111",
        "tron:Taaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }


def test_evm_wallet_adapter_reads_metamask_wrapped_state_for_bitcoin_snap_and_polygon_account(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "wallet-state.json").write_text(
        json.dumps(
            {
                "metamask": {
                    "internalAccounts": {
                        "accounts": {
                            "one": {
                                "address": "0x1111111111111111111111111111111111111111",
                                "type": "eip155:eoa",
                                "scopes": ["eip155:137"],
                                "metadata": {"name": "Primary", "keyring": {"type": "Ledger Hardware"}},
                            },
                            "two": {
                                "address": "bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                                "type": "bip122:p2wpkh",
                                "scopes": ["bip122:000000000019d6689c085ae165831e93"],
                                "metadata": {
                                    "name": "BTC Wallet",
                                    "keyring": {"type": "Snap Keyring"},
                                    "snap": {"name": "Bitcoin"},
                                },
                            },
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    records, issues = ADAPTER.extract_location_inventory(
        "evm-wallets",
        raw_dir,
        build_source_profile(adapter_id="evm_wallet", source="evm-wallets", raw_dir=str(raw_dir)),
    )

    assert not issues
    assert {record.identifier_kind for record in records} == {"evm_address", "btc_address"}
    assert {str(record.location_id) for record in records} == {
        "evm:polygon:0x1111111111111111111111111111111111111111",
        "bitcoin:bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }


def test_evm_wallet_adapter_marks_generic_evm_accounts_as_ambiguous(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "wallet-state.json").write_text(
        json.dumps(
            {
                "wallet_state": {
                    "internalAccounts": {
                        "accounts": {
                            "one": {
                                "address": "0x1111111111111111111111111111111111111111",
                                "metadata": {"name": "Primary", "keyring": {"type": "HD Key Tree"}},
                            }
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    records, issues = ADAPTER.extract_location_inventory(
        "evm-wallets",
        raw_dir,
        build_source_profile(adapter_id="evm_wallet", source="evm-wallets", raw_dir=str(raw_dir)),
    )

    assert not records
    assert {issue.kind for issue in issues} == {"ambiguous_wallet_identifier", "missing_identifier"}


def test_evm_wallet_adapter_matches_state_json_inventory_without_source_label() -> None:
    score = ADAPTER.match(
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


def test_evm_wallet_adapter_normalize_returns_location_inventory_and_missing_identifier_issue(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "wallet-state.json").write_text(json.dumps({"wallet_state": {}}), encoding="utf-8")

    result = ADAPTER.translate(
        build_source_profile(adapter_id="evm_wallet", source="evm-wallets", raw_dir=str(raw_dir)),
        raw_dir,
    )

    assert not compile_activity_drafts(result.drafts)
    assert not result.location_inventory
    assert len(result.issues) == 1
    assert result.issues[0].kind == "missing_identifier"


def test_evm_wallet_adapter_extracts_solana_identity_and_surfaces_unknown_identifier(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "wallet-state.json").write_text(
        json.dumps(
            {
                "wallet_state": {
                    "internalAccounts": {
                        "accounts": {
                            "sol": {
                                "address": "F11111111111111111111111111111111111111111",
                                "type": "solana:data-account",
                                "scopes": ["solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"],
                                "metadata": {
                                    "name": "Solana Wallet",
                                    "keyring": {"type": "Snap Keyring"},
                                    "snap": {"name": "Solana"},
                                },
                            },
                            "bad": {
                                "address": "not a wallet identifier",
                                "metadata": {"name": "Ignore Me"},
                            },
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    records, issues = ADAPTER.extract_location_inventory(
        "evm-wallets",
        raw_dir,
        build_source_profile(adapter_id="evm_wallet", source="evm-wallets", raw_dir=str(raw_dir)),
    )

    assert len(issues) == 1
    assert issues[0].kind == "unsupported_wallet_identifier"
    assert [record.identifier_kind for record in records] == ["solana_address"]
    assert [record.network_scope for record in records] == ["solana"]


def test_evm_wallet_adapter_validate_profile_timezones_is_trivially_passed() -> None:
    summary, issues = ADAPTER.validate_profile_timezones(build_source_profile(adapter_id="evm_wallet"))

    assert summary == {
        "status": "passed",
        "issue_count": 0,
        "rows_with_dates": 0,
        "mode_counts": {},
    }
    assert not issues


def test_account_records_skip_non_wallet_state_shapes() -> None:
    assert _account_records("wallets", "state.json", {}) == ([], [])
    assert _account_records("wallets", "state.json", {"wallet_state": {"internalAccounts": []}}) == ([], [])
    assert _account_records(
        "wallets",
        "state.json",
        {"wallet_state": {"internalAccounts": {"accounts": []}}},
    ) == ([], [])
    assert _account_records(
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
    ) == ([], [])


def test_wallet_state_helpers_handle_fallback_shapes() -> None:
    assert _network_scope("unknown") == ""
    assert _object_map("not-a-dict") == {}
    assert _wallet_state_root([]) is None
    assert _wallet_state_root({"wallet_state": "not-a-dict"}) is None
    assert _wallet_state_root({"metamask": {"identities": {}}}) == {"identities": {}}


def test_metamask_empty_state_fixture_reports_missing_identifier() -> None:
    raw_dir = fixture_raw_dir("evm_wallet", "missing_state")

    profile, adapter = profile_and_adapter("EVM wallet", raw_dir)
    evidence, issues = adapter.extract_location_inventory("EVM wallet", raw_dir, profile)

    assert str(profile.adapter_id) == "evm_wallet"
    assert evidence == ()
    assert len(issues) == 1
    assert issues[0].kind == "missing_identifier"


def test_metamask_location_inventory_uses_internal_accounts_without_filename_dependency() -> None:
    raw_dir = fixture_raw_dir("evm_wallet", "wallets")

    profile, adapter = profile_and_adapter("Unknown Wallet", raw_dir)
    evidence, issues = adapter.extract_location_inventory("Unknown Wallet", raw_dir, profile)

    assert str(profile.adapter_id) == "evm_wallet"
    assert issues == ()
    assert {str(row.location_id) for row in evidence} >= {
        "evm:ethereum:0x1111111111111111111111111111111111111111",
        "evm:polygon:0x2222222222222222222222222222222222222222",
        "bitcoin:bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }
