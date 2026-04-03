"""CoinTracking CSV output adapter."""

from __future__ import annotations

from pathlib import Path

from tallylot.domain.transactions import (
    FactLegPolicy,
    LegKind,
    LegShapeLimit,
    TransactionFact,
)
from tallylot.domain.types import AdapterId
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.output_adapters import OutputRenderPolicy, RenderedArtifact

from .rendering import render as render_output


class CoinTrackingCsvAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("cointracking_csv"),
        display_name="CoinTracking CSV",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.OUTPUT_RENDER}),
        description="Render transaction facts into CoinTracking-compatible CSV rows.",
    )
    render_policy = OutputRenderPolicy(
        shape_policy=FactLegPolicy(
            limits=(
                LegShapeLimit(
                    kind=LegKind.PRIMARY,
                    min_count=1,
                    max_count=2,
                    max_positive_count=1,
                    max_negative_count=1,
                ),
                LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_positive_count=0, max_negative_count=1),
            )
        ),
        requires_projection_hint=True,
    )

    def render(self, facts: tuple[TransactionFact, ...], output_path: Path) -> RenderedArtifact:
        return render_output(facts, output_path)


ADAPTER = CoinTrackingCsvAdapter()
