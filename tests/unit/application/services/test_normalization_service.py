from __future__ import annotations

import json
from pathlib import Path

from crypto_reconciliation.application.dtos import NormalizeRequest
from crypto_reconciliation.infrastructure.serialization.csv_io import read_rows
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tests.support.services import build_normalization_service


def test_normalization_service_filters_events_outside_explicit_window(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        (
            "timestamp,event_kind,asset_in,amount_in,asset_out,amount_out,"
            "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
            "2023-08-04 10:00:00,Trade,BTC,1.0,CAD,10.0,CAD,0.1,tx-early,early,Fixture,Primary\n"
            "2023-08-06 10:00:00,Trade,ETH,2.0,CAD,20.0,CAD,0.2,tx-keep,keep,Fixture,Primary\n"
        ),
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="fixture_source",
            raw_dir=raw_dir,
            output_dir=output_dir,
            window_start="2023-08-05 08:34:05",
            window_end="2025-12-31 23:59:59",
        )
    )

    canonical_rows = read_rows(output_dir / "canonical_events.csv")
    candidate_rows = read_rows(output_dir / "cointracking_candidate.csv")
    summary = json.loads((output_dir / "normalization_summary.json").read_text(encoding="utf-8"))
    profile = json.loads((output_dir / "profile.json").read_text(encoding="utf-8"))

    assert response.event_count == 1
    assert len(canonical_rows) == 1
    assert canonical_rows[0]["tx_hash"] == "tx-keep"
    assert len(candidate_rows) == 1
    assert candidate_rows[0]["Tx-ID"] == "tx-keep"
    assert summary["event_count"] == 1
    assert summary["events_outside_normalization_window"] == 1
    assert summary["normalization_window_start"] == "2023-08-05 08:34:05"
    assert summary["normalization_window_end"] == "2025-12-31 23:59:59"
    assert profile["normalization_hints"]["normalization_window_start"] == "2023-08-05 08:34:05"
    assert profile["normalization_hints"]["normalization_window_end"] == "2025-12-31 23:59:59"
