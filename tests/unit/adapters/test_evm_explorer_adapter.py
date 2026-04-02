from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.sources.evm_explorer.adapter import EvmExplorerAdapter
from tests.support.services import build_source_profile


def test_evm_explorer_adapter_extracts_owned_address_from_single_to_column(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        "Transaction Hash,DateTime (UTC),Value_IN(BNB),To\n"
        "0xabc,2024-03-09 09:41:37,1.50000000,0x1111111111111111111111111111111111111111\n",
        encoding="utf-8",
    )

    records, issues = EvmExplorerAdapter().extract_wallet_inventory(
        "ethereum-wallet",
        raw_dir,
        build_source_profile(adapter_id="evm_explorer", source="ethereum-wallet", raw_dir=str(raw_dir)),
    )

    assert not issues
    assert [record.wallet_id for record in records] == ["evm_address:0x1111111111111111111111111111111111111111"]
    assert [record.network_scope for record in records] == ["ethereum"]


def test_evm_explorer_adapter_prefers_filename_address_and_network_scope(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "polygon-0x2222222222222222222222222222222222222222.csv").write_text(
        "Transaction Hash,DateTime (UTC),Value_IN(BNB),To\n"
        "0xabc,2024-03-09 09:41:37,1.50000000,0x1111111111111111111111111111111111111111\n",
        encoding="utf-8",
    )

    records, issues = EvmExplorerAdapter().extract_wallet_inventory(
        "polygon-wallet",
        raw_dir,
        build_source_profile(adapter_id="evm_explorer", source="polygon-wallet", raw_dir=str(raw_dir)),
    )

    assert not issues
    assert [record.wallet_id for record in records] == ["evm_address:0x2222222222222222222222222222222222222222"]
    assert [record.network_scope for record in records] == ["polygon"]


def test_evm_explorer_adapter_reports_missing_identifier_when_no_owned_address_is_discernible(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        "Transaction Hash,DateTime (UTC),Value_IN(BNB),To\n"
        "0xabc,2024-03-09 09:41:37,1.50000000,0x1111111111111111111111111111111111111111\n"
        "0xdef,2024-03-10 09:41:37,1.50000000,0x2222222222222222222222222222222222222222\n",
        encoding="utf-8",
    )

    records, issues = EvmExplorerAdapter().extract_wallet_inventory(
        "ethereum-wallet",
        raw_dir,
        build_source_profile(adapter_id="evm_explorer", source="ethereum-wallet", raw_dir=str(raw_dir)),
    )

    assert not records
    assert len(issues) == 1
    assert issues[0].kind == "missing_identifier"


def test_evm_explorer_adapter_normalizes_positive_native_inflows_only(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "0x1111111111111111111111111111111111111111.csv").write_text(
        "Transaction Hash,DateTime (UTC),Value_IN(BNB),To\n"
        "0xzero,2024-03-09 09:41:37,0,0x1111111111111111111111111111111111111111\n"
        "0xneg,2024-03-09 10:41:37,-1,0x1111111111111111111111111111111111111111\n"
        "0xpos,2024-03-09 11:41:37,1.50000000,0x1111111111111111111111111111111111111111\n",
        encoding="utf-8",
    )

    result = EvmExplorerAdapter().normalize(
        build_source_profile(adapter_id="evm_explorer", source="ethereum-wallet", raw_dir=str(raw_dir)),
        raw_dir,
    )

    assert len(result.canonical_events) == 1
    assert result.canonical_events[0].event_kind == "Deposit"
    assert str(result.canonical_events[0].amount_in) == "1.50000000"
    assert not result.issues


def test_evm_explorer_adapter_surfaces_suspicious_nft_airdrops_for_review(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    address = "0x1111111111111111111111111111111111111111"
    (raw_dir / f"{address}.csv").write_text(
        f"Transaction Hash,DateTime (UTC),Value_IN(BNB),To\n0xabc,2024-03-09 09:41:37,1.50000000,{address}\n",
        encoding="utf-8",
    )
    (raw_dir / "nft-transfers.csv").write_text(
        f"Transaction Hash,To,TokenName\n0xabc,{address},$SCAM AIRDROP\n",
        encoding="utf-8",
    )

    result = EvmExplorerAdapter().normalize(
        build_source_profile(adapter_id="evm_explorer", source="ethereum-wallet", raw_dir=str(raw_dir)),
        raw_dir,
    )

    assert not result.canonical_events
    assert len(result.issues) == 1
    assert result.issues[0].kind == "review_required"
    assert "$SCAM AIRDROP" in result.issues[0].message
