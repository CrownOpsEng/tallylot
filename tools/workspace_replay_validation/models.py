from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tallylot.infrastructure.serialization import FilesystemArtifactStore

RAW_CAPTURE_COMPARISON_HEADER = (
    "capture_key",
    "status",
    "reference_file_count",
    "candidate_file_count",
    "missing_files",
    "extra_files",
)
CAPTURE_REGISTRY_COMPARISON_HEADER = (
    "capture_key",
    "status",
    "reference_status",
    "candidate_status",
    "reference_file_count",
    "candidate_file_count",
    "reference_observed_period_start",
    "candidate_observed_period_start",
    "reference_observed_period_end",
    "candidate_observed_period_end",
)
SOURCE_METRIC_COMPARISON_HEADER = (
    "source",
    "status",
    "reference_fact_count",
    "candidate_fact_count",
    "reference_balance_count",
    "candidate_balance_count",
    "reference_balance_evidence_count",
    "candidate_balance_evidence_count",
    "reference_issue_count",
    "candidate_issue_count",
    "reference_review_count",
    "candidate_review_count",
)
RECONCILIATION_COMPARISON_HEADER = (
    "metric_group",
    "metric_name",
    "status",
    "reference_value",
    "candidate_value",
)


@dataclass(frozen=True)
class ReferenceCapture:
    source: str
    manifest_fingerprint: str
    raw_capture_root: Path
    report_slug: str

    @property
    def key(self) -> str:
        return f"{self.source}:{self.manifest_fingerprint}"


@dataclass(frozen=True)
class SourceMetrics:
    source: str
    fact_count: int
    balance_count: int
    balance_evidence_count: int
    issue_count: int
    review_count: int


@dataclass(frozen=True)
class WorkspaceMetrics:
    raw_capture_signatures: dict[str, tuple[str, ...]]
    capture_registry_rows: dict[str, dict[str, str]]
    source_metrics: dict[str, SourceMetrics]
    reconciliation_status_counts: dict[str, dict[str, int]]


@dataclass(frozen=True)
class MetricCollectionRequest:
    artifacts: FilesystemArtifactStore
    workspace_root: Path
    selected_sources: frozenset[str]
    reconciliation_report_dir: Path
    latest_capture_rows: tuple[dict[str, str], ...]
    resolve_capture_root: Callable[[Path, dict[str, str]], Path | None]


@dataclass(frozen=True)
class ParityReportRequest:
    artifacts: FilesystemArtifactStore
    report_dir: Path
    reference_workspace: Path
    candidate_workspace: Path
    reference_metrics: WorkspaceMetrics
    candidate_metrics: WorkspaceMetrics


@dataclass(frozen=True)
class ReplayResult:
    report_dir: Path
    candidate_workspace: Path
    reference_capture_count: int
    candidate_capture_count: int
    mismatch_count: int
