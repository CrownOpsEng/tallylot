from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from tallylot.adapters.sources.explorers.evm_explorer.models import (
    EvmTranslationContext,
)
from tallylot.adapters.sources.explorers.evm_explorer.token_transfers import (
    translate_token_transfers,
)
from tallylot.adapters.support.drafts import compile_activity_drafts
from tests.support.services import build_source_profile


def _write_csv(path: Path, rows: tuple[dict[str, str], ...]) -> None:
    header = (
        "Transaction Hash",
        "DateTime (UTC)",
        "From",
        "To",
        "TokenValue",
        "TokenSymbol",
        "ContractAddress",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow([row.get(column, "") for column in header])


def test_translate_token_transfers_handles_blocked_and_unsupported_rows(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    owned_address = "0x1111111111111111111111111111111111111111"
    valid_contract = "0x2222222222222222222222222222222222222222"
    external_address = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    path = raw_dir / f"{owned_address}.csv"
    _write_csv(
        path,
        (
            {
                "Transaction Hash": "0xblocked",
                "DateTime (UTC)": "2024-03-09 09:41:37",
                "From": external_address,
                "To": owned_address,
                "TokenValue": "1.00000000",
                "TokenSymbol": "GALA",
                "ContractAddress": valid_contract,
            },
            {
                "Transaction Hash": "0xunsupported",
                "DateTime (UTC)": "2024-03-09 09:41:37",
                "From": external_address,
                "To": owned_address,
                "TokenValue": "2.00000000",
                "TokenSymbol": "GALA",
                "ContractAddress": valid_contract,
            },
            {
                "Transaction Hash": "0xinvalid",
                "DateTime (UTC)": "",
                "From": external_address,
                "To": owned_address,
                "TokenValue": "3.00000000",
                "TokenSymbol": "GALA",
                "ContractAddress": valid_contract,
            },
            {
                "Transaction Hash": "0xshape",
                "DateTime (UTC)": "2024-03-09 09:41:37",
                "From": owned_address,
                "To": owned_address,
                "TokenValue": "4.00000000",
                "TokenSymbol": "GALA",
                "ContractAddress": valid_contract,
            },
            {
                "Transaction Hash": "0xidentity",
                "DateTime (UTC)": "2024-03-09 09:41:37",
                "From": external_address,
                "To": owned_address,
                "TokenValue": "5.00000000",
                "TokenSymbol": "GALA",
                "ContractAddress": "GALA",
            },
            {
                "Transaction Hash": "0xvalid",
                "DateTime (UTC)": "2024-03-09 09:41:37",
                "From": external_address,
                "To": owned_address,
                "TokenValue": "6.00000000",
                "TokenSymbol": "GALA",
                "ContractAddress": valid_contract,
            },
        ),
    )

    profile = build_source_profile(
        adapter_id="evm_explorer", source="ethereum-wallet", raw_dir=str(raw_dir)
    )
    drafts, issues = translate_token_transfers(
        profile,
        path,
        EvmTranslationContext(
            owned_addresses={owned_address},
            network_scope="ethereum",
            blocked_tx_hashes={"0xblocked"},
            unsupported_methods={"0xunsupported": "approve"},
        ),
    )
    facts = compile_activity_drafts(drafts)

    assert len(facts) == 2
    assert {fact.tx_hash for fact in facts} == {"0xidentity", "0xvalid"}
    assert {str(fact.legs[0].instrument_id) for fact in facts} == {
        "symbol:GALA@evm_explorer",
        "asset:evm:ethereum:erc20:0x2222222222222222222222222222222222222222",
    }
    assert all(
        fact.timestamp == datetime(2024, 3, 9, 9, 41, 37, tzinfo=UTC) for fact in facts
    )
    assert [issue.kind for issue in issues].count("unsupported_row") == 3
    assert any(
        issue.issue_id.endswith("unsupported_related_method:approve")
        for issue in issues
    )
    assert "instrument_identity_blocked" in {issue.kind for issue in issues}
