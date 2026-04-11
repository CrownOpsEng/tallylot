from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from tallylot.adapters.sources.explorers.ronin.translation.raw import (
    _translate_raw_row,
    _translate_supported_raw_row,
    translate_raw_group,
)
from tallylot.adapters.sources.explorers.ronin.translation.rows import (
    RoninRawRow,
    RoninSummaryRow,
)
from tallylot.adapters.support.drafts import compile_activity_drafts
from tests.support.services import build_source_profile


def _raw_row(**overrides: object) -> RoninRawRow:
    data: dict[str, object] = {
        "path_name": "ronin-tx.csv",
        "row_index": 2,
        "tx_hash": "0xraw",
        "timestamp": datetime(2022, 1, 13, 20, 24, 56, tzinfo=UTC),
        "from_address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "to_address": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "method": "transfer",
        "asset_symbol": "AXS",
        "inbound_quantity": Decimal("1.0"),
        "outbound_quantity": Decimal("0"),
        "fee_text": "0.000000",
        "fee": Decimal("0"),
        "status": "success",
    }
    data.update(overrides)
    return RoninRawRow(**cast(Any, data))


def _summary_row(**overrides: object) -> RoninSummaryRow:
    data: dict[str, object] = {
        "path_name": "ronin-summary.csv",
        "row_index": 2,
        "tx_hash": "0xsummary",
        "action_type": "restakeaxs",
        "local_timestamp": datetime(2022, 1, 13, 13, 24, 56),
        "quantity": Decimal("0.0277578354"),
        "from_address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "to_address": "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        "asset_symbol": "AXS",
        "ronin_address": "ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
    }
    data.update(overrides)
    return RoninSummaryRow(**cast(Any, data))


def test_translate_raw_group_rejects_ambiguous_methods() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")

    drafts, issues, reviews = translate_raw_group(
        profile,
        (
            _raw_row(method="transfer"),
            _raw_row(method="stake", row_index=3),
        ),
        owned_addresses={"0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
        summary_rows=(),
    )

    assert not drafts
    assert not reviews
    assert [issue.kind for issue in issues] == ["unsupported_row"]
    assert issues[0].issue_id.endswith("ambiguous_raw_group")


def test_translate_raw_group_uses_summary_backed_restake_pair() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")
    timestamp = datetime(2022, 1, 13, 20, 24, 56, tzinfo=UTC)

    drafts, issues, reviews = translate_raw_group(
        profile,
        (
            _raw_row(
                tx_hash="0xrestake",
                method="restakerewards",
                timestamp=timestamp,
                inbound_quantity=Decimal("0.0277578354"),
                outbound_quantity=Decimal("0"),
                from_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                to_address="0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            ),
            _raw_row(
                tx_hash="0xrestake",
                method="restakerewards",
                timestamp=timestamp,
                inbound_quantity=Decimal("0"),
                outbound_quantity=Decimal("0.0277578354"),
                from_address="0x05b0bb3c1c320b280501b86706c3551995bc8571",
                to_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                row_index=3,
            ),
        ),
        owned_addresses={
            "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            "0x05b0bb3c1c320b280501b86706c3551995bc8571",
        },
        summary_rows=(
            _summary_row(
                tx_hash="0xrestake",
                action_type="restakeaxs",
                local_timestamp=datetime(2022, 1, 13, 13, 24, 56),
                quantity=Decimal("0.0277578354"),
                from_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                to_address="0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            ),
            _summary_row(
                tx_hash="0xrestake",
                action_type="restakeaxs",
                local_timestamp=datetime(2022, 1, 13, 13, 24, 56),
                quantity=Decimal("-0.0277578354"),
                from_address="0x05b0bb3c1c320b280501b86706c3551995bc8571",
                to_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                row_index=3,
            ),
        ),
    )
    facts = compile_activity_drafts(drafts)

    assert not issues
    assert not reviews
    assert [fact.timestamp for fact in facts] == [timestamp, timestamp]
    assert {fact.economic_kind.name for fact in facts} == {
        "STAKING_REWARD",
        "STAKING_TRANSFER_OUT",
    }


def test_translate_raw_group_rejects_unsupported_restake_without_pair() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")

    drafts, issues, reviews = translate_raw_group(
        profile,
        (
            _raw_row(
                tx_hash="0xrestake",
                method="restakerewards",
                inbound_quantity=Decimal("0.0277578354"),
                outbound_quantity=Decimal("0"),
                to_address="0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            ),
            _raw_row(
                tx_hash="0xrestake",
                method="restakerewards",
                inbound_quantity=Decimal("0.0277578354"),
                outbound_quantity=Decimal("0"),
                to_address="0x05b0bb3c1c320b280501b86706c3551995bc8571",
                row_index=3,
            ),
        ),
        owned_addresses={"0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"},
        summary_rows=(),
    )

    assert not drafts
    assert not reviews
    assert [issue.kind for issue in issues] == ["unsupported_row"]
    assert issues[0].issue_id.endswith("unsupported_restake")


def test_translate_raw_group_rejects_unsupported_raw_group_shape() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")

    drafts, issues, reviews = translate_raw_group(
        profile,
        (
            _raw_row(
                tx_hash="0xraw",
                method="transfer",
                inbound_quantity=Decimal("1.0"),
                to_address="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            ),
            _raw_row(
                tx_hash="0xraw",
                method="transfer",
                inbound_quantity=Decimal("1.0"),
                to_address="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                row_index=3,
            ),
        ),
        owned_addresses={"0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
        summary_rows=(),
    )

    assert not drafts
    assert not reviews
    assert [issue.kind for issue in issues] == ["unsupported_row"]
    assert issues[0].issue_id.endswith("unsupported_raw_group")


def test_translate_raw_row_rejects_unsupported_status() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")

    drafts, issues = _translate_raw_row(
        profile,
        _raw_row(status="pending"),
        owned_addresses={"0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
        authoritative_fee=Decimal("0"),
    )

    assert not drafts
    assert [issue.kind for issue in issues] == ["unsupported_row"]
    assert issues[0].issue_id.endswith("unsupported_status")


def test_translate_supported_raw_row_rejects_unknown_method_and_shapes() -> None:
    profile = build_source_profile(adapter_id="ronin", source="wallet-a")

    unknown_method_drafts, unknown_method_issues = _translate_supported_raw_row(
        profile,
        _raw_row(method="bridge"),
        owned_addresses={"0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
        authoritative_fee=Decimal("0"),
    )
    transfer_drafts, transfer_issues = _translate_supported_raw_row(
        profile,
        _raw_row(
            method="transfer",
            inbound_quantity=Decimal("1.0"),
            to_address="0xcccccccccccccccccccccccccccccccccccccccc",
        ),
        owned_addresses={"0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
        authoritative_fee=Decimal("0"),
    )
    stake_drafts, stake_issues = _translate_supported_raw_row(
        profile,
        _raw_row(
            method="stake",
            outbound_quantity=Decimal("1.0"),
            inbound_quantity=Decimal("0"),
            from_address="0xcccccccccccccccccccccccccccccccccccccccc",
        ),
        owned_addresses={"0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
        authoritative_fee=Decimal("0"),
    )
    unstake_drafts, unstake_issues = _translate_supported_raw_row(
        profile,
        _raw_row(
            method="unstake",
            inbound_quantity=Decimal("1.0"),
            outbound_quantity=Decimal("0"),
            to_address="0xcccccccccccccccccccccccccccccccccccccccc",
        ),
        owned_addresses={"0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
        authoritative_fee=Decimal("0"),
    )
    reward_drafts, reward_issues = _translate_supported_raw_row(
        profile,
        _raw_row(
            method="claimpendingrewards",
            inbound_quantity=Decimal("1.0"),
            outbound_quantity=Decimal("0"),
            to_address="0xcccccccccccccccccccccccccccccccccccccccc",
        ),
        owned_addresses={"0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
        authoritative_fee=Decimal("0"),
    )

    assert not unknown_method_drafts
    assert not transfer_drafts
    assert not stake_drafts
    assert not unstake_drafts
    assert not reward_drafts
    assert unknown_method_issues[0].issue_id.endswith("unsupported_method:bridge")
    assert transfer_issues[0].issue_id.endswith("unsupported_shape")
    assert stake_issues[0].issue_id.endswith("unsupported_shape")
    assert unstake_issues[0].issue_id.endswith("unsupported_shape")
    assert reward_issues[0].issue_id.endswith("unsupported_shape")
