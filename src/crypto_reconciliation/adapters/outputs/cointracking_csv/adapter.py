"""CoinTracking CSV output adapter."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.domain.models import AdapterCapability, AdapterManifest, CanonicalEvent
from crypto_reconciliation.domain.types import AdapterId
from crypto_reconciliation.ports.adapters import RenderedArtifact
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.output_workflows import BaselineArtifacts, ScreeningResult

from . import baseline as baseline_support
from . import screening
from .rendering import render as render_output
from .schema import CANDIDATE_ARTIFACT_NAME


class CoinTrackingCsvAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("cointracking_csv"),
        display_name="CoinTracking CSV",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.OUTPUT_RENDER, AdapterCapability.REVIEW}),
        description="Render canonical events into CoinTracking-compatible CSV rows and review CoinTracking exports.",
    )

    def render(self, events: tuple[CanonicalEvent, ...], output_path: Path) -> RenderedArtifact:
        return render_output(events, output_path)

    def candidate_artifact_name(self) -> str:
        return CANDIDATE_ARTIFACT_NAME

    def match_candidate(self, candidate_path: Path, artifacts: ArtifactStorePort) -> int:
        return screening.match_candidate(candidate_path, artifacts)

    def screen_candidate(
        self,
        candidate_path: Path,
        baseline_export_dir: Path,
        artifacts: ArtifactStorePort,
    ) -> ScreeningResult:
        return screening.screen_candidate(candidate_path, baseline_export_dir, artifacts)

    def match_baseline_exports(self, export_dir: Path, artifacts: ArtifactStorePort) -> int:
        del artifacts
        return baseline_support.match_baseline_exports(export_dir)

    def build_baseline_artifacts(self, export_dir: Path, artifacts: ArtifactStorePort) -> BaselineArtifacts:
        return baseline_support.build_baseline_artifacts(export_dir, artifacts)


ADAPTER = CoinTrackingCsvAdapter()
