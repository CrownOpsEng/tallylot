from __future__ import annotations

from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter


def test_shakepay_adapter_normalizes_fixture_rows() -> None:
    raw_dir = fixture_raw_dir("shakepay", "cash_crypto_mix")

    profile, adapter = profile_and_adapter("Shakepay", raw_dir)
    result = adapter.normalize(profile, raw_dir)

    assert str(profile.adapter_id) == "shakepay"
    assert {event.event_kind for event in result.canonical_events} == {
        "Deposit",
        "Expense (non taxable)",
        "Reward / Bonus",
        "Trade",
        "Withdrawal",
    }
    assert any(event.description == "shakingsats" for event in result.canonical_events)
    assert result.canonical_balances == ()
    assert result.issues == ()
