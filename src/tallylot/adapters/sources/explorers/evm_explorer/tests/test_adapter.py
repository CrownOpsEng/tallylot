from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.explorers.evm_explorer.adapter import EvmExplorerAdapter
from tallylot.domain.transactions import EconomicKind, JournalIntent, ProjectionType, TaxTreatmentCode
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter
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

    result = EvmExplorerAdapter().translate(
        build_source_profile(adapter_id="evm_explorer", source="ethereum-wallet", raw_dir=str(raw_dir)),
        raw_dir,
    )

    assert len(result.facts) == 1
    assert result.facts[0].economic_kind == EconomicKind.CHAIN_TRANSFER_IN
    assert result.facts[0].projection_type == ProjectionType.DEPOSIT
    assert result.facts[0].journal_intent == JournalIntent.FUNDING_INFLOW
    assert result.facts[0].tax_treatment_code == TaxTreatmentCode.NON_TAXABLE_TRANSFER_IN
    assert result.facts[0].legs[0].direction == "in"
    assert str(result.facts[0].amount_in) == "1.50000000"
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

    result = EvmExplorerAdapter().translate(
        build_source_profile(adapter_id="evm_explorer", source="ethereum-wallet", raw_dir=str(raw_dir)),
        raw_dir,
    )

    assert not result.facts
    assert len(result.issues) == 1
    assert result.issues[0].kind == "review_required"
    assert "$SCAM AIRDROP" in result.issues[0].message


def test_evm_explorer_empty_chain_scoped_capture_reports_missing_identifier(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "export-empty.csv").write_text("Transaction Hash,DateTime (UTC)\n", encoding="utf-8")

    records, issues = EvmExplorerAdapter().extract_wallet_inventory(
        "eth-metamask1",
        raw_dir,
        build_source_profile(adapter_id="evm_explorer", source="eth-metamask1", raw_dir=str(raw_dir)),
    )

    assert not records
    assert len(issues) == 1
    assert issues[0].kind == "missing_identifier"


def test_evm_explorer_fixture_reports_multiple_primary_identifiers() -> None:
    raw_dir = fixture_raw_dir("evm_explorer", "multi_wallet_capture")

    profile, adapter = profile_and_adapter("bsc-wallet-1", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("bsc-wallet-1", raw_dir, profile)

    assert str(profile.adapter_id) == "evm_explorer"
    assert len({row.wallet_id for row in evidence}) == 2
    assert any(issue.kind == "multiple_primary_identifiers" for issue in issues)


def test_evm_explorer_chain_scoped_capture_accepts_neutral_filenames() -> None:
    raw_dir = fixture_raw_dir("evm_explorer", "chain_scoped_deposit")

    profile, adapter = profile_and_adapter("bsc-wallet", raw_dir)
    result = adapter.translate(profile, raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("bsc-wallet", raw_dir, profile)

    assert str(profile.adapter_id) == "evm_explorer"
    assert issues == ()
    assert [row.wallet_id for row in evidence] == ["evm_address:0x1111111111111111111111111111111111111111"]
    assert len(result.facts) == 1
    assert result.facts[0].economic_kind == EconomicKind.CHAIN_TRANSFER_IN
    assert result.facts[0].projection_type == ProjectionType.DEPOSIT
    assert str(result.facts[0].asset_in) == "BNB"
    assert str(result.facts[0].amount_in) == "1.50000000"


def test_evm_explorer_chain_scoped_capture_works_from_nested_bundle_paths(tmp_path: Path) -> None:
    nested = tmp_path / "raw" / "2024-03" / "bundle-01"
    nested.mkdir(parents=True)
    source_path = fixture_raw_dir("evm_explorer", "chain_scoped_deposit") / "transactions.csv"
    (nested / "transactions.csv").write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    profile, adapter = profile_and_adapter("bsc-wallet", tmp_path / "raw")
    result = adapter.translate(profile, tmp_path / "raw")

    assert str(profile.adapter_id) == "evm_explorer"
    assert len(result.facts) == 1
    assert result.facts[0].projection_type == ProjectionType.DEPOSIT


def test_evm_explorer_suspicious_nft_fixture_surfaces_review_without_auto_import() -> None:
    raw_dir = fixture_raw_dir("evm_explorer", "suspicious_nft_review")

    profile, adapter = profile_and_adapter("bsc-wallet", raw_dir)
    result = adapter.translate(profile, raw_dir)

    assert result.facts == ()
    assert len(result.issues) == 1
    assert result.issues[0].kind == "review_required"
    assert "suspicious NFT airdrop" in result.issues[0].message
