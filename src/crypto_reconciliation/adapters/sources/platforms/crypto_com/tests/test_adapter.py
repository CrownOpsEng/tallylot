from __future__ import annotations

from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter


def test_crypto_com_adapter_uses_transaction_kinds_without_filename_dependency() -> None:
    raw_dir = fixture_raw_dir("crypto_com", "transaction_kinds")

    profile, adapter = profile_and_adapter("Future Card", raw_dir)
    result = adapter.normalize(profile, raw_dir)

    assert str(profile.adapter_id) == "crypto_com"
    assert [event.category for event in result.transactions] == ["deposit", "trade", "withdrawal"]
    assert {event.raw_file for event in result.transactions} == {"records-a.csv", "records-b.csv"}
    assert result.issues == ()
