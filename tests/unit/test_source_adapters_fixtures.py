from __future__ import annotations

from pathlib import Path

import pipeline_common
import source_adapters
import wallet_inventory


def _build_profile(source: str, raw_dir: Path) -> tuple[object, pipeline_common.SourceProfile]:
    adapter = source_adapters.get_adapter(source)
    profile = pipeline_common.build_source_profile(
        source=source,
        raw_dir=raw_dir,
        adapter_name=adapter.name,
        adapter_supported=adapter.supported,
    )
    return adapter, profile


def test_coinbase_adapter_requires_retail_csv(tmp_path: Path) -> None:
    raw_dir = tmp_path / "coinbase" / "raw"
    raw_dir.mkdir(parents=True)
    adapter, profile = _build_profile("Coinbase", raw_dir)

    result = adapter.normalize(raw_dir, profile, exception_decisions={})

    assert result.canonical_events == []
    assert result.canonical_balances == []
    assert len(result.exceptions) == 1
    assert result.exceptions[0]["event_id"] == "coinbase:missing_retail_csv"
    assert result.exceptions[0]["exception_kind"] == "missing_required_input"


def test_wealthsimple_fixture_exercises_supported_and_unsupported_rows(copy_fixture_tree) -> None:
    raw_dir = copy_fixture_tree("raw_sources/wealthsimple_mixed/raw")
    adapter, profile = _build_profile("WealthSimple", raw_dir)

    result = adapter.normalize(raw_dir, profile, exception_decisions={})

    assert len(result.canonical_events) == 1
    assert result.canonical_events[0]["event_kind"] == "Trade"
    assert result.canonical_events[0]["timestamp"] == "2023-09-22 00:00:00"
    assert result.canonical_events[0]["render_match_window_seconds"] == "86399"
    assert len(result.exceptions) == 1
    assert result.exceptions[0]["exception_kind"] == "unsupported_row"
    assert "Staking/REWARD" in result.exceptions[0]["message"]


def test_load_exception_decisions_ignores_blank_event_ids(tmp_path: Path) -> None:
    decisions_path = tmp_path / "exception_decisions.csv"
    decisions_path.write_text(
        (
            "manifest_fingerprint,event_id,resolution_status,resolution_note\n"
            "abc,,accepted,missing id should be ignored\n"
            "abc,evt-1,accepted,kept\n"
        ),
        encoding="utf-8",
    )

    decisions = source_adapters.load_exception_decisions(decisions_path, "abc")

    assert decisions == {
        "evt-1": {
            "resolution_status": "accepted",
            "resolution_note": "kept",
        }
    }


def test_metamask_empty_state_fixture_reports_missing_identifier(copy_fixture_tree) -> None:
    raw_dir = copy_fixture_tree("raw_sources/metamask_empty/raw")

    evidence, issues, summary = wallet_inventory.profile_wallet_identifiers("MetaMask app", raw_dir)

    assert evidence == []
    assert summary["adapter"] == "metamask_app"
    assert summary["status"] == "needs_review"
    assert any(issue["issue_kind"] == "missing_identifier" for issue in issues)


def test_evm_explorer_fixture_reports_multiple_primary_identifiers(copy_fixture_tree) -> None:
    raw_dir = copy_fixture_tree("raw_sources/evm_explorer_multi/raw", destination_name="bsc_wallet_capture")

    evidence, issues, summary = wallet_inventory.profile_wallet_identifiers("bsc-metamask1", raw_dir)

    assert summary["adapter"] == "evm_explorer"
    assert summary["wallet_count"] == 2
    assert len({row["wallet_id"] for row in evidence}) == 2
    assert any(issue["issue_kind"] == "multiple_primary_identifiers" for issue in issues)


def test_evm_explorer_chain_scoped_capture_accepts_neutral_filenames(tmp_path: Path) -> None:
    raw_dir = tmp_path / "bsc_wallet_capture" / "raw"
    raw_dir.mkdir(parents=True)
    owned = "0x1111111111111111111111111111111111111111"
    counterparty = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    (raw_dir / "transactions.csv").write_text(
        (
            "Transaction Hash,Blockno,UnixTimestamp,DateTime (UTC),From,To,Value_IN(BNB),Value_OUT(BNB),TxnFee(BNB),Method,ErrCode\n"
            f"0xabc,1,1700000000,2023-11-14 12:00:00,{counterparty},{owned},1.50000000,0.00000000,0.00021000,Transfer,\n"
        ),
        encoding="utf-8",
    )

    evidence, issues, summary = wallet_inventory.profile_wallet_identifiers("bsc-wallet", raw_dir)
    adapter, profile = _build_profile("bsc-wallet", raw_dir)
    result = adapter.normalize(raw_dir, profile, exception_decisions={})

    assert summary["adapter"] == "evm_explorer"
    assert summary["status"] == "passed"
    assert issues == []
    assert [row["wallet_id"] for row in evidence] == [f"evm_address:{owned}"]
    assert len(result.exceptions) == 0
    assert len(result.canonical_events) == 1
    assert result.canonical_events[0]["event_kind"] == "Deposit"
    assert result.canonical_events[0]["asset_in"] == "BNB"
    assert result.canonical_events[0]["amount_in"] == "1.50000000"
