from __future__ import annotations

from pathlib import Path

import pytest

from tallylot.application.profiling import BuildProfileUseCase
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


@pytest.mark.parametrize(
    ("source", "expected_adapter"),
    [
        ("Coinbase", "coinbase"),
        ("WealthSimple", "wealthsimple"),
        ("Binance", "binance"),
        ("Crypto.com", "crypto_com"),
        ("Shakepay", "shakepay"),
        ("ledger-live-main", "ledger_live"),
        ("near-main", "near"),
        ("GTrade 1CT", "gtrade"),
        ("bsc-wallet-fixture", "evm_explorer"),
        ("Ronin Wallet", "ronin"),
        ("Ledger Live", "ledger_live"),
        ("NEAR Wallet", "near"),
    ],
)
def test_profile_service_resolves_supported_sources(
    source: str, expected_adapter: str, tmp_path: Path
) -> None:
    profile = BuildProfileUseCase(
        build_registry(), FilesystemArtifactStore()
    ).create_profile(source, tmp_path)

    assert str(profile.adapter_id) == expected_adapter


def test_profile_service_resolves_from_profile_inventory_before_source_label(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "broker-export.csv").write_text(
        "transaction_date,settlement_date,account_id,account_type,activity_type,activity_sub_type,direction,"
        "symbol,name,currency,quantity,unit_price,commission,net_cash_amount\n"
        "2023-09-21,,acct,Crypto,trade,BUY,buy,BTC,Bitcoin,CAD,0.1,60000,0,6000\n",
        encoding="utf-8",
    )

    profile = BuildProfileUseCase(
        build_registry(), FilesystemArtifactStore()
    ).create_profile("Future Broker", raw_dir)

    assert str(profile.adapter_id) == "wealthsimple"


def test_profile_service_uses_content_family_for_ronin_exports(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "renamed.csv").write_text(
        "Txhash,Blockno,UnixTimestamp,DateTime,From,To,Method,Token / Collectibles,"
        "Value in,Value out,TxnFee(RON),Status\n"
        "0xabc,1,1641068696,2022-01-01 20:24:56,0xb32e9a84ae0b55b8ab715e4ac793a61b277bafa3,"
        "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94,transfer,Axie Infinity Shard,0.1950000000,0,0.000052,Success\n",
        encoding="utf-8",
    )

    profile = BuildProfileUseCase(
        build_registry(), FilesystemArtifactStore()
    ).create_profile("wallet-a", raw_dir)

    assert str(profile.adapter_id) == "ronin"
