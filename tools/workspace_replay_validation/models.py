from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
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
    "reference_source",
    "candidate_source",
    "reference_status",
    "candidate_status",
    "reference_file_count",
    "candidate_file_count",
    "reference_manifest_fingerprint",
    "candidate_manifest_fingerprint",
    "reference_observed_period_start",
    "candidate_observed_period_start",
    "reference_observed_period_end",
    "candidate_observed_period_end",
    "reference_capture_root_ref_present",
    "candidate_capture_root_ref_present",
)
SOURCE_METRIC_COMPARISON_HEADER = (
    "source",
    "status",
    "hard_metric_status",
    "issue_count_status",
    "review_count_status",
    "reference_fact_count",
    "candidate_fact_count",
    "reference_snapshot_count",
    "candidate_snapshot_count",
    "reference_reference_count",
    "candidate_reference_count",
    "reference_issue_count",
    "candidate_issue_count",
    "reference_review_count",
    "candidate_review_count",
    "expected_issue_count_delta",
    "expected_review_count_delta",
    "expected_difference_reason",
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
class WorkspaceReplayValidationRequest:
    reference_workspace: Path
    candidate_workspace: Path
    report_dir: Path
    selected_sources: frozenset[str]
    inspect_archives: bool
    expected_differences_path: Path | None = None


@dataclass(frozen=True)
class SourceMetrics:
    source: str
    fact_count: int
    snapshot_count: int
    reference_count: int
    issue_count: int
    review_count: int


@dataclass(frozen=True)
class CaptureRegistryMetrics:
    source: str
    status: str
    file_count: str
    manifest_fingerprint: str
    observed_period_start: str
    observed_period_end: str
    capture_root_ref_present: bool


@dataclass(frozen=True)
class ExpectedMetricDifference:
    source: str
    issue_count_delta: int
    review_count_delta: int
    reason: str


@dataclass(frozen=True)
class ExpectedDifferenceSet:
    differences_by_source: dict[str, ExpectedMetricDifference]

    @classmethod
    def empty(cls) -> ExpectedDifferenceSet:
        return cls(differences_by_source={})

    def for_source(self, source: str) -> ExpectedMetricDifference | None:
        return self.differences_by_source.get(source)

    def sources(self) -> frozenset[str]:
        return frozenset(self.differences_by_source)

    def limited_to_sources(self, sources: frozenset[str]) -> ExpectedDifferenceSet:
        if not sources:
            return self
        return ExpectedDifferenceSet(
            differences_by_source={
                source: difference
                for source, difference in self.differences_by_source.items()
                if source in sources
            }
        )

    def declared_count(self) -> int:
        return len(self.differences_by_source)


@dataclass(frozen=True)
class WorkspaceMetrics:
    raw_capture_signatures: dict[str, tuple[str, ...]]
    capture_registry_rows: dict[str, CaptureRegistryMetrics]
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
    expected_differences: ExpectedDifferenceSet = field(
        default_factory=ExpectedDifferenceSet.empty
    )


@dataclass(frozen=True)
class ReplayResult:
    report_dir: Path
    candidate_workspace: Path
    reference_capture_count: int
    candidate_capture_count: int
    mismatch_count: int
    expected_difference_count: int
    passed_with_expected_differences: bool
