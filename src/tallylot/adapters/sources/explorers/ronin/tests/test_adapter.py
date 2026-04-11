from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.explorers.ronin.adapter import _RoninAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.transactions import EconomicKind, LegKind, ProjectionHint
from tests.support.services import build_source_profile

RAW_HEADER = (
    "Txhash,Blockno,UnixTimestamp,DateTime,From,To,Method,Token / Collectibles,"
    "Value in,Value out,TxnFee(RON),Status\n"
)


def test_ronin_adapter_extracts_owned_wallet_and_normalizes_supported_rows(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    address = "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"
    (raw_dir / f"{address}-tx.csv").write_text(
        RAW_HEADER
        + "0xtransfer,1,1641068696,2022-01-01 20:24:56,0xb32e9a84ae0b55b8ab715e4ac793a61b277bafa3,"
        f"{address},transfer,Axie Infinity Shard,0.1950000000,0,0.000052,Success\n"
        + f"0xstake,2,1641070412,2022-01-01 20:53:32,{address},0x05b0bb3c1c320b280501b86706c3551995bc8571,"
        "stake,Axie Infinity Shard,0,3.0439300000,0.000000,Success\n"
        + f"0xunstake,3,1675853938,2023-02-08 10:58:58,0x05b0bb3c1c320b280501b86706c3551995bc8571,{address},"
        "unstake,Axie Infinity Shard,3.7403105801,0,0.000000,Success\n"
        + "0xreward,3,1675854028,2023-02-08 11:00:28,0x8bd81a19420bad681b7bfc20e703ebd8e253782d,"
        f"{address},claimPendingRewards,Axie Infinity Shard,1.9206358286,0,0.000000,Success\n",
        encoding="utf-8",
    )
    (raw_dir / f"{address}-xfer.csv").write_text(
        RAW_HEADER
        + f"0xtransfer,1,1641068696,2022-01-01 20:24:56,0xb32e9a84ae0b55b8ab715e4ac793a61b277bafa3,{address},"
        "transfer,Axie Infinity Shard,0.1950000000,0,0.000052,Success\n"
        + f"0xrestake,4,1641333457,2022-01-04 21:57:37,0x8bd81a19420bad681b7bfc20e703ebd8e253782d,{address},"
        "restakeRewards,Axie Infinity Shard,0.0277578354,0,0.000000,Success\n"
        + f"0xrestake,5,1641333457,2022-01-04 21:57:37,{address},0x05b0bb3c1c320b280501b86706c3551995bc8571,"
        "restakeRewards,Axie Infinity Shard,0,0.0277578354,0.000000,Success\n",
        encoding="utf-8",
    )

    profile = build_source_profile(
        adapter_id="ronin", source="wallet-a", raw_dir=str(raw_dir)
    )

    location_inventory, location_issues = _RoninAdapter().extract_location_inventory(
        "wallet-a", raw_dir, profile
    )
    result = _RoninAdapter().translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert not location_issues
    assert [str(row.location_id) for row in location_inventory] == [
        f"evm:ronin:{address}"
    ]
    assert len(facts) == 6
    assert [fact.tx_hash for fact in facts].count("0xtransfer") == 1
    facts_by_hash = {(fact.tx_hash, str(fact.legs[0].quantity)): fact for fact in facts}
    assert {
        (fact.tx_hash, fact.economic_kind, fact.projection_hint) for fact in facts
    } == {
        ("0xtransfer", EconomicKind.CHAIN_TRANSFER_IN, ProjectionHint.DEPOSIT),
        ("0xstake", EconomicKind.STAKING_TRANSFER_OUT, ProjectionHint.WITHDRAWAL),
        ("0xunstake", EconomicKind.STAKING_TRANSFER_IN, ProjectionHint.DEPOSIT),
        ("0xreward", EconomicKind.STAKING_REWARD, ProjectionHint.STAKING),
        ("0xrestake", EconomicKind.STAKING_REWARD, ProjectionHint.STAKING),
        ("0xrestake", EconomicKind.STAKING_TRANSFER_OUT, ProjectionHint.WITHDRAWAL),
    }
    assert facts_by_hash[("0xtransfer", "0.195")].legs[0].quantity == Decimal(
        "0.1950000000"
    )
    assert facts_by_hash[("0xstake", "-3.04393")].legs[0].quantity == Decimal(
        "-3.0439300000"
    )
    assert facts_by_hash[("0xunstake", "3.7403105801")].legs[0].quantity == Decimal(
        "3.7403105801"
    )
    assert facts_by_hash[("0xreward", "1.9206358286")].legs[0].quantity == Decimal(
        "1.9206358286"
    )
    assert facts_by_hash[("0xrestake", "0.0277578354")].legs[0].quantity == Decimal(
        "0.0277578354"
    )
    assert facts_by_hash[("0xrestake", "-0.0277578354")].legs[0].quantity == Decimal(
        "-0.0277578354"
    )
    assert result.issues
    assert {issue.kind for issue in result.issues} == {"instrument_identity_blocked"}
    assert len(result.reviews) == 1
    assert result.reviews[0].kind == "insufficient_decimal_precision"


def test_ronin_adapter_accepts_precise_non_zero_fee_values(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    address = "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"
    (raw_dir / f"{address}-tx.csv").write_text(
        RAW_HEADER
        + "0xtransfer,1,1641068696,2022-01-01 20:24:56,0xb32e9a84ae0b55b8ab715e4ac793a61b277bafa3,"
        f"{address},transfer,Axie Infinity Shard,0.1950000000,0,0.000051876,Success\n",
        encoding="utf-8",
    )

    result = _RoninAdapter().translate(
        build_source_profile(
            adapter_id="ronin", source="wallet-a", raw_dir=str(raw_dir)
        ),
        raw_dir,
    )
    facts = compile_activity_drafts(result.drafts)

    assert len(facts) == 1
    charge_legs = tuple(leg for leg in facts[0].legs if leg.kind is LegKind.CHARGE)
    assert charge_legs[0].quantity == Decimal("-0.000051876")
    assert str(charge_legs[0].instrument_id) == "asset:evm:ronin:native"
    assert not result.reviews


def test_ronin_adapter_surfaces_approvals_as_explicit_issues(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    address = "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"
    (raw_dir / f"{address}.csv").write_text(
        RAW_HEADER
        + f"0xapprove,1,1641070382,2022-01-01 20:53:02,{address},0x97a9107c1793bc407d6f527b77e7fff4d812bece,"
        "approve,RON,0,0.0000000000,0.000000,Success\n",
        encoding="utf-8",
    )

    result = _RoninAdapter().translate(
        build_source_profile(
            adapter_id="ronin", source="wallet-a", raw_dir=str(raw_dir)
        ),
        raw_dir,
    )

    assert not compile_activity_drafts(result.drafts)
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"
    assert "approve" in result.issues[0].message
