from __future__ import annotations

from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter


def test_shakepay_adapter_normalizes_fixture_rows() -> None:
    raw_dir = fixture_raw_dir("shakepay", "cash_crypto_mix")

    profile, adapter = profile_and_adapter("Shakepay", raw_dir)
    result = adapter.normalize(profile, raw_dir)

    assert str(profile.adapter_id) == "shakepay"
    assert {event.category for event in result.transactions} == {
        "deposit",
        "expense",
        "reward",
        "trade",
        "withdrawal",
    }
    assert any(event.description == "shakingsats" for event in result.transactions)
    assert result.balance_evidence == ()
    assert result.issues == ()
