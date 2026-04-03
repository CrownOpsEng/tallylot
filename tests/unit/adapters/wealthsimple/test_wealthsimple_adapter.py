from __future__ import annotations

from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter


def test_wealthsimple_fixture_exercises_supported_and_unsupported_rows() -> None:
    raw_dir = fixture_raw_dir("wealthsimple", "mixed_activity_review")

    profile, adapter = profile_and_adapter("WealthSimple", raw_dir)
    result = adapter.normalize(profile, raw_dir)

    assert str(profile.adapter_id) == "wealthsimple"
    assert len(result.canonical_events) == 1
    assert result.canonical_events[0].event_kind == "Trade"
    assert str(result.canonical_events[0].timestamp) == "2023-09-22 00:00:00"
    assert result.canonical_events[0].render_match_window_seconds == "86399"
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"
    assert "Staking/REWARD" in result.issues[0].message


def test_wealthsimple_adapter_uses_broker_activity_family_without_filename_dependency() -> None:
    raw_dir = fixture_raw_dir("wealthsimple", "broker_trade")

    profile, adapter = profile_and_adapter("Future Broker", raw_dir)
    result = adapter.normalize(profile, raw_dir)

    assert str(profile.adapter_id) == "wealthsimple"
    assert len(result.canonical_events) == 1
    assert result.canonical_events[0].raw_file == "broker-export.csv"
    assert result.canonical_events[0].render_match_window_seconds == "86399"
    assert result.issues == ()
