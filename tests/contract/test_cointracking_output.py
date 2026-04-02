from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.outputs.cointracking_csv import COINTRACKING_HEADER
from crypto_reconciliation.application.dtos import NormalizeRequest, RenderCoinTrackingRequest
from crypto_reconciliation.application.services.normalize import NormalizationService
from crypto_reconciliation.application.services.profile import ProfileService
from crypto_reconciliation.application.services.render import CoinTrackingRenderService
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization.csv_io import read_rows
from crypto_reconciliation.infrastructure.storage import FilesystemStorage


def test_cointracking_output_matches_expected_schema(
    structured_source_dir: Path,
    tmp_path: Path,
) -> None:
    registry = build_registry()
    normalization = NormalizationService(registry, ProfileService(registry), FilesystemStorage())
    render = CoinTrackingRenderService(registry)
    normalized_dir = tmp_path / "normalized"

    normalization.execute(
        NormalizeRequest(
            source="fixture_source",
            raw_dir=structured_source_dir,
            output_dir=normalized_dir,
        )
    )
    output_path = tmp_path / "cointracking.csv"
    render.execute(
        RenderCoinTrackingRequest(
            canonical_events_path=normalized_dir / "canonical_events.csv",
            output_path=output_path,
        )
    )

    rows = read_rows(output_path)

    assert tuple(rows[0]) == COINTRACKING_HEADER
    assert len(rows) == 2
