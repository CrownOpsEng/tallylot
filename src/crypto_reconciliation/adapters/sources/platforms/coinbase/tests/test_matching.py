from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.sources.platforms.coinbase.adapter import CoinbaseAdapter
from crypto_reconciliation.adapters.sources.platforms.coinbase.matching import RETAIL_HEADER
from crypto_reconciliation.adapters.sources.platforms.coinbase.timestamps import parse_retail_timestamp
from crypto_reconciliation.application.profiling import BuildProfileUseCase
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from crypto_reconciliation.ports.source_adapters import SourceAdapter
from crypto_reconciliation.ports.source_profiles import FileInventoryEntry, SourceProfile

FIXTURE_ROOT = Path(__file__).resolve().parents[7] / "tests" / "fixtures" / "adapter_packs"


def _profile_and_adapter(source: str, raw_dir: Path) -> tuple[SourceProfile, SourceAdapter]:
    registry = build_registry()
    profile = BuildProfileUseCase(registry, FilesystemArtifactStore()).create_profile(source, raw_dir)
    return profile, registry.source_adapter(str(profile.adapter_id))


def test_parse_retail_timestamp_preserves_utc_clock_time() -> None:
    parsed = parse_retail_timestamp("2025-10-17 13:38:17 UTC")

    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == "2025-10-17 13:38:17"


def test_coinbase_adapter_matches_retail_header_without_source_label(tmp_path: Path) -> None:
    inventory = (
        FileInventoryEntry(
            relative_path="retail-export.csv",
            suffix=".csv",
            size_bytes=1,
            sha256="abc",
            header=RETAIL_HEADER,
        ),
    )

    assert CoinbaseAdapter().match("future_exchange", tmp_path, inventory) == 100


def test_coinbase_adapter_uses_retail_family_without_filename_dependency() -> None:
    raw_dir = FIXTURE_ROOT / "coinbase" / "retail_buy_renamed" / "raw"

    profile, adapter = _profile_and_adapter("Future Exchange", raw_dir)
    result = adapter.translate(profile, raw_dir)

    assert str(profile.adapter_id) == "coinbase"
    assert len(result.facts) == 1
    assert result.facts[0].raw_file == "retail-export.csv"
    assert result.facts[0].category == "trade"
    assert result.issues == ()
