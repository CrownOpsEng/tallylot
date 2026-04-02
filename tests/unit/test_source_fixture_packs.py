from __future__ import annotations

from pathlib import Path

import pytest

import pipeline_common
import source_adapters
import wallet_inventory
from tests.support.source_packs import load_source_packs, stage_source_pack, strip_dynamic_wallet_paths


NORMALIZATION_PACKS = load_source_packs("normalize")
WALLET_PACKS = load_source_packs("wallet")


@pytest.mark.parametrize("pack", NORMALIZATION_PACKS, ids=lambda pack: pack.name)
def test_normalization_source_packs(pack, tmp_path: Path) -> None:
    raw_dir = stage_source_pack(pack, tmp_path)
    seeded_adapter = source_adapters.get_adapter(pack.source)
    profile = pipeline_common.build_source_profile(
        source=pack.source,
        raw_dir=raw_dir,
        adapter_name=seeded_adapter.name,
        adapter_supported=seeded_adapter.supported,
    )
    adapter = source_adapters.get_adapter(pack.source, profile)
    timezone_summary, _ = adapter.validate_profile_timezones(profile)
    result = adapter.normalize(raw_dir, profile, exception_decisions={})

    assert adapter.name == pack.expected_adapter
    assert timezone_summary["status"] == pack.expected_timezone_status
    assert result.canonical_events == pack.expected_json("canonical_events")
    assert result.canonical_balances == pack.expected_json("canonical_balances")
    assert result.exceptions == pack.expected_json("exceptions")


@pytest.mark.parametrize("pack", WALLET_PACKS, ids=lambda pack: pack.name)
def test_wallet_source_packs(pack, tmp_path: Path) -> None:
    raw_dir = stage_source_pack(pack, tmp_path)
    evidence, issues, summary = wallet_inventory.profile_wallet_identifiers(
        pack.source,
        raw_dir,
        adapter_name=pack.adapter_name_override,
    )

    assert summary["adapter"] == pack.expected_adapter
    assert strip_dynamic_wallet_paths(evidence) == pack.expected_json("wallet_evidence")
    assert issues == pack.expected_json("wallet_issues")
