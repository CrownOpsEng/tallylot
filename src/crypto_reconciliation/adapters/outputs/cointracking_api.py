"""Stub CoinTracking API output adapter entry point."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.domain.models import AdapterCapability, AdapterManifest, CanonicalEvent
from crypto_reconciliation.domain.types import AdapterId
from crypto_reconciliation.ports.adapters import RenderedArtifact
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.output_workflows import BaselineArtifacts, ScreeningResult


class CoinTrackingApiStubAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("cointracking_api"),
        display_name="CoinTracking API",
        version="0.0.0",
        capabilities=frozenset({AdapterCapability.OUTPUT_RENDER}),
        supported=False,
        description="Reserved API adapter entry point.",
    )

    def render(self, events: tuple[CanonicalEvent, ...], output_path: Path) -> RenderedArtifact:
        del events, output_path
        raise NotImplementedError(
            "CoinTracking API integration is intentionally stubbed in this phase.",
        )

    def candidate_artifact_name(self) -> str:
        return "cointracking_api_candidate.json"

    def match_candidate(self, candidate_path: Path, artifacts: ArtifactStorePort) -> int:
        del candidate_path, artifacts
        return 0

    def screen_candidate(
        self,
        candidate_path: Path,
        baseline_export_dir: Path,
        artifacts: ArtifactStorePort,
    ) -> ScreeningResult:
        del candidate_path, baseline_export_dir, artifacts
        raise NotImplementedError("CoinTracking API review workflows are intentionally stubbed in this phase.")

    def match_baseline_exports(self, export_dir: Path, artifacts: ArtifactStorePort) -> int:
        del export_dir, artifacts
        return 0

    def build_baseline_artifacts(self, export_dir: Path, artifacts: ArtifactStorePort) -> BaselineArtifacts:
        del export_dir, artifacts
        raise NotImplementedError("CoinTracking API review workflows are intentionally stubbed in this phase.")


ADAPTER = CoinTrackingApiStubAdapter()
