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
        ("bsc-metamask1", "evm_explorer"),
        ("Ledger Live", "ledger_live"),
        ("NEAR Wallet", "near"),
    ],
)
def test_profile_service_resolves_supported_sources(source: str, expected_adapter: str, tmp_path: Path) -> None:
    profile = BuildProfileUseCase(build_registry(), FilesystemArtifactStore()).create_profile(source, tmp_path)

    assert str(profile.adapter_id) == expected_adapter


def test_profile_service_resolves_from_profile_inventory_before_source_label(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "broker-export.csv").write_text(
        "transaction_date,settlement_date,account_id,account_type,activity_type,activity_sub_type,direction,"
        "symbol,name,currency,quantity,unit_price,commission,net_cash_amount\n"
        "2023-09-21,,acct,Crypto,trade,BUY,buy,BTC,Bitcoin,CAD,0.1,60000,0,6000\n",
        encoding="utf-8",
    )

    profile = BuildProfileUseCase(build_registry(), FilesystemArtifactStore()).create_profile("Future Broker", raw_dir)

    assert str(profile.adapter_id) == "wealthsimple"
