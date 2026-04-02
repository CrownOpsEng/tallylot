from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.outputs.cointracking_csv import COINTRACKING_HEADER
from crypto_reconciliation.application.models.output import RenderOutputRequest
from crypto_reconciliation.application.models.source import NormalizeRequest
from crypto_reconciliation.infrastructure.serialization.csv_io import read_rows
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tests.support.services import build_normalization_service, build_render_service


def test_cointracking_output_matches_expected_schema(
    structured_source_dir: Path,
    tmp_path: Path,
) -> None:
    artifacts = FilesystemArtifactStore()
    normalization = build_normalization_service(artifacts=artifacts)
    render = build_render_service(artifacts=artifacts)
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
        RenderOutputRequest(
            output_adapter="cointracking_csv",
            canonical_events_path=normalized_dir / "canonical_events.csv",
            output_path=output_path,
        )
    )

    rows = read_rows(output_path)

    assert tuple(rows[0]) == COINTRACKING_HEADER
    assert len(rows) == 2
    assert not (normalized_dir / "cointracking_candidate.csv").exists()
