from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import pytest

from tallylot.adapters.sources.explorers.ronin.translation.rows import (
    RoninSummaryRow,
)
from tallylot.adapters.sources.explorers.ronin.translation.summary import (
    translate_summary_group,
)
from tallylot.adapters.support.drafts import compile_activity_drafts
from tests.support.services import build_source_profile


def _summary_row(**overrides: object) -> RoninSummaryRow:
    data: dict[str, object] = {
        "path_name": "ronin-summary.csv",
        "row_index": 2,
        "tx_hash": "0xsummary",
        "local_timestamp": datetime(2022, 1, 13, 13, 24, 56),
        "action_type": "transfer",
        "ronin_address": "ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        "from_address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "to_address": "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        "asset_symbol": "AXS",
        "quantity": Decimal("0.195"),
    }
    data.update(overrides)
    return RoninSummaryRow(**cast(Any, data))


def test_translate_summary_group_rejects_ambiguous_local_timestamps() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")
    owned_address = "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"
    local_timestamp = datetime(2022, 1, 13, 13, 24, 56)
    rows = (
        _summary_row(
            tx_hash="0xsummary",
            action_type="transfer",
            quantity=Decimal("0.195"),
            local_timestamp=local_timestamp,
            ronin_address=f"ronin:{owned_address[2:]}",
            from_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            to_address=owned_address,
        ),
        _summary_row(
            tx_hash="0xsummary",
            action_type="transfer",
            quantity=Decimal("0.195"),
            local_timestamp=local_timestamp + timedelta(minutes=1),
            ronin_address=f"ronin:{owned_address[2:]}",
            from_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            to_address=owned_address,
        ),
    )

    drafts, issues = translate_summary_group(
        profile,
        rows,
        owned_addresses={owned_address},
        calibrations=((local_timestamp, timedelta(hours=7)),),
    )

    assert not drafts
    assert [issue.kind for issue in issues] == ["unsupported_row"]
    assert issues[0].issue_id.endswith("ambiguous_summary_timestamp")


def test_translate_summary_group_rejects_ambiguous_action_types() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")
    owned_address = "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"
    local_timestamp = datetime(2022, 1, 13, 13, 24, 56)
    rows = (
        _summary_row(
            tx_hash="0xsummary",
            action_type="transfer",
            quantity=Decimal("0.195"),
            local_timestamp=local_timestamp,
            ronin_address=f"ronin:{owned_address[2:]}",
            from_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            to_address=owned_address,
        ),
        _summary_row(
            tx_hash="0xsummary",
            action_type="stakeaxs",
            quantity=Decimal("-0.195"),
            local_timestamp=local_timestamp,
            ronin_address=f"ronin:{owned_address[2:]}",
            from_address=owned_address,
            to_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        ),
    )

    drafts, issues = translate_summary_group(
        profile,
        rows,
        owned_addresses={owned_address},
        calibrations=((local_timestamp, timedelta(hours=7)),),
    )

    assert not drafts
    assert [issue.kind for issue in issues] == ["unsupported_row"]
    assert issues[0].issue_id.endswith("ambiguous_summary_group")


def test_translate_summary_group_handles_empty_groups() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")

    drafts, issues = translate_summary_group(
        profile,
        (),
        owned_addresses={"0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"},
    )

    assert not drafts
    assert not issues


@pytest.mark.parametrize(
    ("action_type", "quantity", "from_address", "to_address", "expected_kind"),
    (
        (
            "transfer",
            Decimal("0.195"),
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            "CHAIN_TRANSFER_IN",
        ),
        (
            "transfer",
            Decimal("-0.195"),
            "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "ASSET_WITHDRAWAL",
        ),
        (
            "stakeaxs",
            Decimal("-0.195"),
            "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "STAKING_TRANSFER_OUT",
        ),
    ),
)
def test_translate_summary_group_supports_directional_rows(
    action_type: str,
    quantity: Decimal,
    from_address: str,
    to_address: str,
    expected_kind: str,
) -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")
    local_timestamp = datetime(2022, 1, 13, 13, 24, 56)
    row = _summary_row(
        tx_hash="0xsummary",
        action_type=action_type,
        quantity=quantity,
        local_timestamp=local_timestamp,
        ronin_address="ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        from_address=from_address,
        to_address=to_address,
    )

    drafts, issues = translate_summary_group(
        profile,
        (row,),
        owned_addresses={"0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"},
        calibrations=((local_timestamp, timedelta(hours=7)),),
    )
    facts = compile_activity_drafts(drafts)

    assert len(facts) == 1
    assert facts[0].economic_kind.name == expected_kind
    assert not issues


def test_translate_summary_group_supports_restake_pairs() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")
    local_timestamp = datetime(2022, 1, 13, 13, 24, 56)
    owned_reward_address = "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"
    owned_stake_address = "0x05b0bb3c1c320b280501b86706c3551995bc8571"
    rows = (
        _summary_row(
            tx_hash="0xrestake",
            action_type="restakeaxs",
            quantity=Decimal("0.0277578354"),
            local_timestamp=local_timestamp,
            ronin_address=f"ronin:{owned_reward_address[2:]}",
            from_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            to_address=owned_reward_address,
            row_index=2,
        ),
        _summary_row(
            tx_hash="0xrestake",
            action_type="restakeaxs",
            quantity=Decimal("-0.0277578354"),
            local_timestamp=local_timestamp,
            ronin_address=f"ronin:{owned_stake_address[2:]}",
            from_address=owned_stake_address,
            to_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            row_index=3,
        ),
    )

    drafts, issues = translate_summary_group(
        profile,
        rows,
        owned_addresses={owned_reward_address, owned_stake_address},
        calibrations=((local_timestamp, timedelta(hours=7)),),
    )
    facts = compile_activity_drafts(drafts)

    assert len(facts) == 2
    assert {fact.economic_kind.name for fact in facts} == {
        "STAKING_REWARD",
        "STAKING_TRANSFER_OUT",
    }
    assert not issues


def test_translate_summary_group_rejects_supported_group_shape_mismatch() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")
    local_timestamp = datetime(2022, 1, 13, 13, 24, 56)
    rows = (
        _summary_row(
            tx_hash="0xsummary",
            action_type="transfer",
            quantity=Decimal("0.195"),
            local_timestamp=local_timestamp,
            ronin_address="ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            from_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            to_address="0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        ),
        _summary_row(
            tx_hash="0xsummary",
            action_type="transfer",
            quantity=Decimal("-0.195"),
            local_timestamp=local_timestamp,
            ronin_address="ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            from_address="0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            to_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            row_index=3,
        ),
    )

    drafts, issues = translate_summary_group(
        profile,
        rows,
        owned_addresses={"0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"},
        calibrations=((local_timestamp, timedelta(hours=7)),),
    )

    assert not drafts
    assert [issue.kind for issue in issues] == ["unsupported_row"]
    assert issues[0].issue_id.endswith("unsupported_summary_group")


def test_translate_summary_group_rejects_unsupported_stake_direction() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")
    local_timestamp = datetime(2022, 1, 13, 13, 24, 56)
    row = _summary_row(
        tx_hash="0xsummary",
        action_type="stakeaxs",
        quantity=Decimal("-0.195"),
        local_timestamp=local_timestamp,
        ronin_address="ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        from_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        to_address="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )

    drafts, issues = translate_summary_group(
        profile,
        (row,),
        owned_addresses={"0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"},
        calibrations=((local_timestamp, timedelta(hours=7)),),
    )

    assert not drafts
    assert [issue.kind for issue in issues] == ["unsupported_row"]
    assert issues[0].issue_id.endswith("unsupported_summary_group")


def test_translate_summary_group_rejects_unsupported_restake_pair() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")
    local_timestamp = datetime(2022, 1, 13, 13, 24, 56)
    rows = (
        _summary_row(
            tx_hash="0xrestake",
            action_type="restakeaxs",
            quantity=Decimal("0.0277578354"),
            local_timestamp=local_timestamp,
            ronin_address="ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            from_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            to_address="0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        ),
        _summary_row(
            tx_hash="0xrestake",
            action_type="restakeaxs",
            quantity=Decimal("-0.0277578354"),
            local_timestamp=local_timestamp,
            ronin_address="ronin:05b0bb3c1c320b280501b86706c3551995bc8571",
            from_address="0x05b0bb3c1c320b280501b86706c3551995bc8571",
            to_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            row_index=3,
        ),
    )

    drafts, issues = translate_summary_group(
        profile,
        rows,
        owned_addresses={"0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"},
        calibrations=((local_timestamp, timedelta(hours=7)),),
    )

    assert not drafts
    assert [issue.kind for issue in issues] == ["unsupported_row"]
    assert issues[0].issue_id.endswith("unsupported_summary_group")


def test_translate_summary_group_rejects_unsupported_summary_directions() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")
    local_timestamp = datetime(2022, 1, 13, 13, 24, 56)
    row = _summary_row(
        tx_hash="0xsummary",
        action_type="transfer",
        quantity=Decimal("0.195"),
        local_timestamp=local_timestamp,
        ronin_address="ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        from_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        to_address="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )

    drafts, issues = translate_summary_group(
        profile,
        (row,),
        owned_addresses={"0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"},
        calibrations=((local_timestamp, timedelta(hours=7)),),
    )

    assert not drafts
    assert [issue.kind for issue in issues] == ["unsupported_row"]
    assert issues[0].issue_id.endswith("unsupported_summary_group")
