from __future__ import annotations

from pathlib import Path

import pytest

import pipeline_common
import source_adapters
import wallet_inventory
from tests.support.adapter_packs import (
    load_adapter_packs,
    stage_adapter_pack,
    strip_dynamic_issue_paths,
    strip_dynamic_wallet_paths,
)


ALL_PACKS = load_adapter_packs()
NORMALIZATION_PACKS = load_adapter_packs("normalize")
WALLET_PACKS = load_adapter_packs("wallet")


def test_supported_normalization_adapters_have_adapter_packs() -> None:
    covered = {pack.expected_adapter for pack in NORMALIZATION_PACKS}
    missing = sorted(adapter.name for adapter in source_adapters.ADAPTERS if adapter.supported and adapter.name not in covered)

    assert missing == []


def test_wallet_extractors_have_adapter_packs() -> None:
    covered = {pack.expected_adapter for pack in WALLET_PACKS}
    base = source_adapters.SourceAdapter.extract_wallet_identifiers
    missing = sorted(
        adapter.name
        for adapter in source_adapters.ADAPTERS
        if adapter.__class__.extract_wallet_identifiers is not base and adapter.name not in covered
    )

    assert missing == []


def test_adapter_pack_contracts_are_complete() -> None:
    assert len({pack.id for pack in ALL_PACKS}) == len(ALL_PACKS)
    for pack in ALL_PACKS:
        assert pack.adapter == pack.expected_adapter
        assert pack.raw_dir.is_dir()
        assert pack.capabilities
        if pack.supports("normalize"):
            assert (pack.expected_dir / "canonical_events.json").exists()
            assert (pack.expected_dir / "canonical_balances.json").exists()
            assert (pack.expected_dir / "exceptions.json").exists()
        if pack.supports("wallet"):
            assert (pack.expected_dir / "wallet_evidence.json").exists()
            assert (pack.expected_dir / "wallet_issues.json").exists()


@pytest.mark.parametrize("pack", NORMALIZATION_PACKS, ids=lambda pack: pack.id)
def test_normalization_source_packs(pack, tmp_path: Path) -> None:
    raw_dir = stage_adapter_pack(pack, tmp_path)
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


@pytest.mark.parametrize("pack", WALLET_PACKS, ids=lambda pack: pack.id)
def test_wallet_source_packs(pack, tmp_path: Path) -> None:
    raw_dir = stage_adapter_pack(pack, tmp_path)
    evidence, issues, summary = wallet_inventory.profile_wallet_identifiers(
        pack.source,
        raw_dir,
        adapter_name=pack.adapter_name_override,
    )

    assert summary["adapter"] == pack.expected_adapter
    assert strip_dynamic_wallet_paths(evidence) == pack.expected_json("wallet_evidence")
    assert strip_dynamic_issue_paths(issues) == pack.expected_json("wallet_issues")
