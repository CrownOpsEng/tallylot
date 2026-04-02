from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.explorers.ronin.adapter import RoninAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.transactions import EconomicKind, ProjectionHint
from tests.support.services import build_source_profile

RAW_HEADER = (
    "Txhash,Blockno,UnixTimestamp,DateTime,From,To,Method,Token / Collectibles,Value in,Value out,TxnFee(RON),Status\n"
)
SUMMARY_HEADER = (
    '"RoninAddress","TxnHash","TxnURL","Timestamp","ActionType","Actions","AxieID","AxieURL","LandID",'
    '"ItemID","ETH","SLP","AXS","USDC","¥/ETH","¥/SLP","¥/AXS","AXS-WETH","SLP-WETH","USDC-WETH","From","To"\n'
)


def test_ronin_adapter_extracts_owned_wallet_and_normalizes_supported_rows(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    address = "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"
    (raw_dir / f"{address}-tx.csv").write_text(
        RAW_HEADER + "0xtransfer,1,1641068696,2022-01-01 20:24:56,0xb32e9a84ae0b55b8ab715e4ac793a61b277bafa3,"
        f"{address},transfer,Axie Infinity Shard,0.1950000000,0,0.000052,Success\n"
        + f"0xstake,2,1641070412,2022-01-01 20:53:32,{address},0x05b0bb3c1c320b280501b86706c3551995bc8571,"
        "stake,Axie Infinity Shard,0,3.0439300000,0.000000,Success\n"
        + "0xreward,3,1675854028,2023-02-08 11:00:28,0x8bd81a19420bad681b7bfc20e703ebd8e253782d,"
        f"{address},claimPendingRewards,Axie Infinity Shard,1.9206358286,0,0.000000,Success\n",
        encoding="utf-8",
    )
    (raw_dir / f"{address}-xfer.csv").write_text(
        RAW_HEADER + "0xtransfer,1,1641068696,2022-01-01 20:24:56,0xb32e9a84ae0b55b8ab715e4ac793a61b277bafa3,"
        f"{address},transfer,Axie Infinity Shard,0.1950000000,0,0.000052,Success\n",
        encoding="utf-8",
    )
    (raw_dir / "summary.csv").write_text(
        SUMMARY_HEADER
        + f'"ronin:{address.removeprefix("0x")}","0xrestake","https://explorer.roninchain.com/tx/0xrestake",'
        '"04/01/2022, 14:57:37","RestakeAXS","Restake 0.027757835385899127 AXS","","","","","0","0",'
        '"0.027757835385899127","0","0","0","0","0","0","0",'
        '"ronin:8bd81a19420bad681b7bfc20e703ebd8e253782d",'
        f'"ronin:{address.removeprefix("0x")}"\n'
        + f'"ronin:{address.removeprefix("0x")}","0xrestake","https://explorer.roninchain.com/tx/0xrestake",'
        '"04/01/2022, 14:57:37","RestakeAXS","Restake 0.027757835385899127 AXS","","","","","0","0",'
        '"-0.027757835385899127","0","0","0","0","0","0","0",'
        f'"ronin:{address.removeprefix("0x")}","ronin:05b0bb3c1c320b280501b86706c3551995bc8571"\n',
        encoding="utf-8",
    )

    adapter = RoninAdapter()
    profile = build_source_profile(adapter_id="ronin", source="ronin-main", raw_dir=str(raw_dir))

    location_inventory, location_issues = adapter.extract_location_inventory("ronin-main", raw_dir, profile)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert not location_issues
    assert [str(row.location_id) for row in location_inventory] == [f"evm:ronin:{address}"]
    assert len(facts) == 5
    assert [fact.tx_hash for fact in facts].count("0xtransfer") == 1
    facts_by_hash = {(fact.tx_hash, str(fact.legs[0].quantity)): fact for fact in facts}
    assert {(fact.tx_hash, fact.economic_kind, fact.projection_hint) for fact in facts} == {
        ("0xtransfer", EconomicKind.CHAIN_TRANSFER_IN, ProjectionHint.DEPOSIT),
        ("0xstake", EconomicKind.STAKING_TRANSFER_OUT, ProjectionHint.WITHDRAWAL),
        ("0xreward", EconomicKind.STAKING_REWARD, ProjectionHint.STAKING),
        ("0xrestake", EconomicKind.STAKING_REWARD, ProjectionHint.STAKING),
        ("0xrestake", EconomicKind.STAKING_TRANSFER_OUT, ProjectionHint.WITHDRAWAL),
    }
    assert facts_by_hash[("0xtransfer", "0.195")].legs[0].quantity == Decimal("0.1950000000")
    assert facts_by_hash[("0xstake", "-3.04393")].legs[0].quantity == Decimal("-3.0439300000")
    assert facts_by_hash[("0xreward", "1.9206358286")].legs[0].quantity == Decimal("1.9206358286")
    assert facts_by_hash[("0xrestake", "0.027757835385899127")].legs[0].quantity == Decimal("0.027757835385899127")
    assert facts_by_hash[("0xrestake", "-0.027757835385899127")].legs[0].quantity == Decimal("-0.027757835385899127")
    assert not result.issues


def test_ronin_adapter_surfaces_approvals_as_explicit_issues(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    address = "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"
    (raw_dir / f"{address}.csv").write_text(
        RAW_HEADER + f"0xapprove,1,1641070382,2022-01-01 20:53:02,{address},0x97a9107c1793bc407d6f527b77e7fff4d812bece,"
        "approve,RON,0,0.0000000000,0.000000,Success\n",
        encoding="utf-8",
    )

    result = RoninAdapter().translate(
        build_source_profile(adapter_id="ronin", source="ronin-main", raw_dir=str(raw_dir)),
        raw_dir,
    )

    assert not compile_activity_drafts(result.drafts)
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"
    assert "approve" in result.issues[0].message
