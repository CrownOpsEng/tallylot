from __future__ import annotations

from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter


def test_gtrade_adapter_surfaces_report_limits_without_guessing() -> None:
    raw_dir = fixture_raw_dir("gtrade", "realized_pnl_alias")

    profile, adapter = profile_and_adapter("GTrade 1CT", raw_dir)
    result = adapter.normalize(profile, raw_dir)

    assert str(profile.adapter_id) == "gtrade"
    assert [event.category for event in result.transactions] == [
        "derivatives_profit",
        "derivatives_loss",
    ]
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"


def test_gtrade_wallet_inventory_includes_alias_issue() -> None:
    raw_dir = fixture_raw_dir("gtrade", "realized_pnl_alias")

    profile, adapter = profile_and_adapter("GTrade 1CT", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("GTrade 1CT", raw_dir, profile)

    assert str(profile.adapter_id) == "gtrade"
    assert any(row.wallet_id == "address_alias:bb4d" for row in evidence)
    assert any(issue.kind == "partial_identifier_only" for issue in issues)
