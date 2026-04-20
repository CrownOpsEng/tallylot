from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from repo_support.paths import adapter_packs_root
from tallylot.adapters.sources.platforms.coinbase.adapter import _CoinbaseAdapter
from tallylot.adapters.sources.platforms.coinbase.matching import RETAIL_HEADER
from tallylot.adapters.sources.platforms.coinbase.timestamps import (
    parse_retail_timestamp,
)
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.application.profiling import BuildProfileUseCase
from tallylot.domain.transactions import LegKind, ProjectionHint
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.source_adapters import SourceAdapter
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile


def _profile_and_adapter(
    source: str, raw_dir: Path
) -> tuple[SourceProfile, SourceAdapter]:
    registry = build_registry()
    profile = BuildProfileUseCase(registry, FilesystemArtifactStore()).create_profile(
        source, raw_dir
    )
    return profile, registry.source_adapter(str(profile.adapter_id))


def test_parse_retail_timestamp_preserves_utc_clock_time() -> None:
    parsed = parse_retail_timestamp("2025-10-17 13:38:17 UTC")

    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == "2025-10-17 13:38:17"


def test_parse_retail_timestamp_accepts_fractional_second_z_suffix() -> None:
    parsed = parse_retail_timestamp("2021-05-10T02:37:18.689Z")

    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == "2021-05-10 02:37:18"


def test_coinbase_adapter_matches_retail_header_without_source_label(
    tmp_path: Path,
) -> None:
    inventory = (
        FileInventoryEntry(
            relative_path="retail-export.csv",
            suffix=".csv",
            size_bytes=1,
            sha256="abc",
            header=RETAIL_HEADER,
        ),
    )

    assert _CoinbaseAdapter().match("future_exchange", tmp_path, inventory) == 100


def test_coinbase_adapter_uses_retail_family_without_filename_dependency() -> None:
    raw_dir = adapter_packs_root() / "coinbase" / "retail_buy_renamed" / "raw"

    profile, adapter = _profile_and_adapter("Future Exchange", raw_dir)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert str(profile.adapter_id) == "coinbase"
    assert len(facts) == 1
    assert facts[0].raw_file == "retail-export.csv"
    assert facts[0].projection_hint == ProjectionHint.TRADE
    primary_legs = tuple(leg for leg in facts[0].legs if leg.kind is LegKind.PRIMARY)
    charge_legs = tuple(leg for leg in facts[0].legs if leg.kind is LegKind.CHARGE)
    assert primary_legs[0].leg_id == "primary_in"
    assert primary_legs[0].quantity == Decimal("0.01")
    assert str(primary_legs[0].instrument_id) == "symbol:BTC@coinbase"
    assert primary_legs[1].leg_id == "primary_out"
    assert primary_legs[1].quantity == Decimal("-600")
    assert str(primary_legs[1].instrument_id) == "symbol:CAD@coinbase"
    assert charge_legs[0].leg_id == "fee"
    assert charge_legs[0].quantity == Decimal("-10")
    assert str(charge_legs[0].instrument_id) == "symbol:CAD@coinbase"
    assert result.issues == ()
