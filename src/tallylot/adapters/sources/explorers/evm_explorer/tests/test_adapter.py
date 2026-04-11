from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.explorers.evm_explorer.adapter import _EvmExplorerAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter
from tests.support.services import build_source_profile


def test_evm_explorer_adapter_extracts_owned_address_from_single_to_column(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        "Transaction Hash,DateTime (UTC),Value_IN(BNB),To\n"
        "0xabc,2024-03-09 09:41:37,1.50000000,0x1111111111111111111111111111111111111111\n",
        encoding="utf-8",
    )

    records, issues = _EvmExplorerAdapter().extract_location_inventory(
        "ethereum-wallet",
        raw_dir,
        build_source_profile(
            adapter_id="evm_explorer", source="ethereum-wallet", raw_dir=str(raw_dir)
        ),
    )

    assert not issues
    assert [str(record.location_id) for record in records] == [
        "evm:ethereum:0x1111111111111111111111111111111111111111"
    ]
    assert [record.network_scope for record in records] == ["ethereum"]


def test_evm_explorer_adapter_prefers_filename_address_and_network_scope(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "polygon-0x2222222222222222222222222222222222222222.csv").write_text(
        "Transaction Hash,DateTime (UTC),Value_IN(BNB),To\n"
        "0xabc,2024-03-09 09:41:37,1.50000000,0x1111111111111111111111111111111111111111\n",
        encoding="utf-8",
    )

    records, issues = _EvmExplorerAdapter().extract_location_inventory(
        "polygon-wallet",
        raw_dir,
        build_source_profile(
            adapter_id="evm_explorer", source="polygon-wallet", raw_dir=str(raw_dir)
        ),
    )

    assert not issues
    assert [str(record.location_id) for record in records] == [
        "evm:polygon:0x2222222222222222222222222222222222222222"
    ]
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

    records, issues = _EvmExplorerAdapter().extract_location_inventory(
        "ethereum-wallet",
        raw_dir,
        build_source_profile(
            adapter_id="evm_explorer", source="ethereum-wallet", raw_dir=str(raw_dir)
        ),
    )

    assert not records
    assert len(issues) == 1
    assert issues[0].kind == "missing_identifier"


def test_evm_explorer_adapter_normalizes_positive_native_inflows_only(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "0x1111111111111111111111111111111111111111.csv").write_text(
        "Transaction Hash,DateTime (UTC),Value_IN(BNB),To\n"
        "0xzero,2024-03-09 09:41:37,0,0x1111111111111111111111111111111111111111\n"
        "0xneg,2024-03-09 10:41:37,-1,0x1111111111111111111111111111111111111111\n"
        "0xpos,2024-03-09 11:41:37,1.50000000,0x1111111111111111111111111111111111111111\n",
        encoding="utf-8",
    )

    result = _EvmExplorerAdapter().translate(
        build_source_profile(
            adapter_id="evm_explorer", source="ethereum-wallet", raw_dir=str(raw_dir)
        ),
        raw_dir,
    )
    facts = compile_activity_drafts(result.drafts)

    assert len(facts) == 1
    assert facts[0].economic_kind == EconomicKind.CHAIN_TRANSFER_IN
    assert facts[0].projection_hint == ProjectionHint.DEPOSIT
    assert facts[0].accounting_intent_hint == AccountingIntentHint.FUNDING_INFLOW
    assert facts[0].tax_treatment_hint == TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN
    assert facts[0].legs[0].leg_id == "primary"
    assert facts[0].legs[0].quantity == Decimal("1.50000000")
    assert str(facts[0].legs[0].instrument_id) == "asset:evm:ethereum:native"
    assert not result.issues


def test_evm_explorer_adapter_surfaces_suspicious_nft_airdrops_for_review(
    tmp_path: Path,
) -> None:
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

    result = _EvmExplorerAdapter().translate(
        build_source_profile(
            adapter_id="evm_explorer", source="ethereum-wallet", raw_dir=str(raw_dir)
        ),
        raw_dir,
    )

    assert not compile_activity_drafts(result.drafts)
    assert len(result.issues) == 1
    assert {issue.kind for issue in result.issues} == {"review_required"}
    assert any("$SCAM AIRDROP" in issue.message for issue in result.issues)


def test_evm_explorer_empty_chain_scoped_capture_reports_missing_identifier(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "export-empty.csv").write_text(
        "Transaction Hash,DateTime (UTC)\n", encoding="utf-8"
    )

    records, issues = _EvmExplorerAdapter().extract_location_inventory(
        "eth-wallet-fixture",
        raw_dir,
        build_source_profile(
            adapter_id="evm_explorer",
            source="eth-wallet-fixture",
            raw_dir=str(raw_dir),
        ),
    )

    assert not records
    assert len(issues) == 1
    assert issues[0].kind == "missing_identifier"


def test_evm_explorer_fixture_reports_multiple_primary_identifiers() -> None:
    raw_dir = fixture_raw_dir("evm_explorer", "multi_wallet_capture")

    profile, adapter = profile_and_adapter("bsc-wallet-1", raw_dir)
    evidence, issues = adapter.extract_location_inventory(
        "bsc-wallet-1", raw_dir, profile
    )

    assert str(profile.adapter_id) == "evm_explorer"
    assert len({row.location_id for row in evidence}) == 2
    assert any(issue.kind == "multiple_primary_identifiers" for issue in issues)


def test_evm_explorer_chain_scoped_capture_accepts_neutral_filenames() -> None:
    raw_dir = fixture_raw_dir("evm_explorer", "chain_scoped_deposit")

    profile, adapter = profile_and_adapter("bsc-wallet", raw_dir)
    result = adapter.translate(profile, raw_dir)
    evidence, issues = adapter.extract_location_inventory(
        "bsc-wallet", raw_dir, profile
    )
    facts = compile_activity_drafts(result.drafts)

    assert str(profile.adapter_id) == "evm_explorer"
    assert issues == ()
    assert [str(row.location_id) for row in evidence] == [
        "evm:bsc:0x1111111111111111111111111111111111111111"
    ]
    assert len(facts) == 1
    assert facts[0].economic_kind == EconomicKind.CHAIN_TRANSFER_IN
    assert facts[0].projection_hint == ProjectionHint.DEPOSIT
    assert facts[0].legs[0].leg_id == "primary"
    assert facts[0].legs[0].quantity == Decimal("1.50000000")
    assert str(facts[0].legs[0].instrument_id) == "asset:evm:bsc:native"


def test_evm_explorer_chain_scoped_capture_works_from_nested_bundle_paths(
    tmp_path: Path,
) -> None:
    nested = tmp_path / "raw" / "2024-03" / "bundle-01"
    nested.mkdir(parents=True)
    source_path = (
        fixture_raw_dir("evm_explorer", "chain_scoped_deposit") / "transactions.csv"
    )
    (nested / "transactions.csv").write_text(
        source_path.read_text(encoding="utf-8"), encoding="utf-8"
    )

    profile, adapter = profile_and_adapter("bsc-wallet", tmp_path / "raw")
    result = adapter.translate(profile, tmp_path / "raw")

    assert str(profile.adapter_id) == "evm_explorer"
    facts = compile_activity_drafts(result.drafts)
    assert len(facts) == 1
    assert facts[0].projection_hint == ProjectionHint.DEPOSIT


def test_evm_explorer_suspicious_nft_fixture_surfaces_review_without_auto_import() -> (
    None
):
    raw_dir = fixture_raw_dir("evm_explorer", "suspicious_nft_review")

    profile, adapter = profile_and_adapter("bsc-wallet", raw_dir)
    result = adapter.translate(profile, raw_dir)

    assert not compile_activity_drafts(result.drafts)
    assert len(result.issues) == 1
    assert {issue.kind for issue in result.issues} == {"review_required"}
    assert any("suspicious NFT airdrop" in issue.message for issue in result.issues)


def test_evm_explorer_adapter_admits_same_chain_portfolio_evidence_only(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "2026-04-10T18-00-00Z"
    raw_dir.mkdir()
    address = "0x1111111111111111111111111111111111111111"
    (raw_dir / f"{address}.csv").write_text(
        "Transaction Hash,DateTime (UTC),Value_IN(BNB),To\n"
        f"0xabc,2024-03-09 09:41:37,1.50000000,{address}\n",
        encoding="utf-8",
    )
    (raw_dir / "Account1-bsc Portfolio.csv").write_text(
        "Chain,Token,Portfolio %,Price,Amount,Value\n"
        "BSC,BNB (BNB),50,600,1.25000000,750\n"
        "ETH,Gala (GALA),25,0.08,1000,80\n"
        "POL,Polygon (POL),25,0.70,40,28\n",
        encoding="utf-8",
    )

    profile, adapter = profile_and_adapter("bsc-wallet-fixture", raw_dir)
    result = adapter.translate(profile, raw_dir)

    assert str(profile.adapter_id) == "evm_explorer"
    assert [row.to_row() for row in result.balance_references] == [
        {
            "source": "bsc-wallet-fixture",
            "location_id": "evm:bsc:0x1111111111111111111111111111111111111111",
            "instrument_id": "asset:evm:bsc:native",
            "balance_kind": "available",
            "target_at": "2024-03-09",
            "target_precision": "date",
            "quantity": "1.25",
            "reference_kind": "source_document",
            "observed_at": "2024-03-09",
            "observed_precision": "date",
            "support_ref": "Account1-bsc Portfolio.csv#row:2",
            "provider_family": "",
            "provider_locator": "",
            "provider_block_ref": "",
            "reviewed_by": "",
            "reviewed_at": "",
            "notes": (
                "MetaMask portfolio quantity admitted for the source folder "
                "chain only; wallet identity remains source-folder-scoped evidence."
            ),
        }
    ]
    assert len(result.reviews) == 2
    assert {review.kind for review in result.reviews} == {
        "portfolio_row_not_admitted",
    }
    assert not result.issues
    assert any(
        "probable destination chain is ethereum" in review.message.lower()
        for review in result.reviews
    )
    assert any(
        "probable destination chain is polygon" in review.message.lower()
        for review in result.reviews
    )


def test_evm_explorer_adapter_uses_profile_inventory_timestamps_for_portfolio_as_of(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "2026-04-10T18-00-00Z"
    raw_dir.mkdir()
    address = "0x2222222222222222222222222222222222222222"
    (
        raw_dir / "Wallet-eth export-0x2222222222222222222222222222222222222222.csv"
    ).write_text(
        "Transaction Hash,DateTime (UTC),Value_IN(ETH),To\n"
        f"0xabc,2023-02-08 23:06:47,0.50000000,{address}\n",
        encoding="utf-8",
    )
    (
        raw_dir
        / "Wallet-eth export-address-token-0x2222222222222222222222222222222222222222.csv"
    ).write_text(
        "Transaction Hash,DateTime (UTC),From,To,TokenValue,TokenSymbol\n"
        f"0xdef,2025-03-24 22:55:59,0x0000000000000000000000000000000000000000,{address},1000,GALA\n",
        encoding="utf-8",
    )
    (raw_dir / "Wallet-eth portfolio.csv").write_text(
        "Chain,Token,Portfolio %,Price,Amount,Value\n"
        "ETH,Gala (GALA),100,0.08,1000,80\n",
        encoding="utf-8",
    )

    profile, adapter = profile_and_adapter("eth-wallet-fixture", raw_dir)
    result = adapter.translate(profile, raw_dir)

    assert str(profile.adapter_id) == "evm_explorer"
    assert not result.balance_references
    assert [issue.kind for issue in result.issues] == ["noncanonical_token_identity"]
    assert any(review.kind == "instrument_identity_review" for review in result.reviews)


def test_evm_explorer_adapter_flags_symbol_only_token_identity_for_history_lookup(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    address = "0x2222222222222222222222222222222222222222"
    (
        raw_dir
        / "Wallet-eth export-address-token-0x2222222222222222222222222222222222222222.csv"
    ).write_text(
        "Transaction Hash,DateTime (UTC),From,To,TokenValue,TokenSymbol\n"
        f"0xdef,2025-03-24 22:55:59,0x0000000000000000000000000000000000000000,{address},1000,GALA\n",
        encoding="utf-8",
    )

    profile, adapter = profile_and_adapter("eth-wallet-fixture", raw_dir)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert str(profile.adapter_id) == "evm_explorer"
    assert len(facts) == 1
    assert str(facts[0].legs[0].instrument_id) == "symbol:GALA@evm_explorer"
    assert [issue.kind for issue in result.issues] == ["noncanonical_token_identity"]


def test_evm_explorer_adapter_requires_single_location_for_portfolio_evidence(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "2026-03"
    raw_dir.mkdir()
    (raw_dir / "Account1-bsc Portfolio.csv").write_text(
        "Chain,Token,Portfolio %,Price,Amount,Value\n"
        "BSC,BNB (BNB),100,600,1.25000000,750\n",
        encoding="utf-8",
    )

    profile, adapter = profile_and_adapter("bsc-wallet-fixture", raw_dir)
    result = adapter.translate(profile, raw_dir)

    assert not result.balance_references
    assert any(issue.kind == "missing_identifier" for issue in result.issues)
    assert any(
        review.kind == "portfolio_location_unresolved" for review in result.reviews
    )
