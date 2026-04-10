from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from tallylot.application.reconciliation import (
    BalanceCheckRequest,
    BalanceCoverageRequest,
    BalanceSummaryRequest,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.composition.runtime import (
    balance_check_workflow,
    balance_coverage_workflow,
    balance_summary_workflow,
)
from tallylot.infrastructure.serialization import FilesystemArtifactStore

from .models import (
    CAPTURE_REGISTRY_COMPARISON_HEADER,
    MetricCollectionRequest,
    ParityReportRequest,
    RAW_CAPTURE_COMPARISON_HEADER,
    RECONCILIATION_COMPARISON_HEADER,
    ReplayResult,
    SOURCE_METRIC_COMPARISON_HEADER,
    SourceMetrics,
    WorkspaceMetrics,
)


def _run_reconciliation(
    workspace_root: Path,
    report_dir: Path,
) -> dict[str, dict[str, int]]:
    input_root = workspace_root / "working" / "normalized" / "sources"
    reconciliation_dir = report_dir / "reconciliation"
    coverage_output = reconciliation_dir / "balance_coverage.csv"
    check_output_root = reconciliation_dir / "checks"
    summary_output = reconciliation_dir / "balance_summary.json"
    coverage_response = balance_coverage_workflow().execute(
        BalanceCoverageRequest(
            input_root_ref=to_resource_ref(input_root),
            coverage_output_ref=to_resource_ref(coverage_output),
        )
    )
    check_response = balance_check_workflow().execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(check_output_root),
        )
    )
    balance_summary_workflow().execute(
        BalanceSummaryRequest(
            coverage_input_ref=coverage_response.coverage_output_ref,
            check_summary_input_ref=check_response.check_summary_output_ref,
            summary_output_ref=to_resource_ref(summary_output),
        )
    )
    payload = json.loads(summary_output.read_text(encoding="utf-8"))
    return {
        "coverage_status_counts": {
            key: int(value)
            for key, value in dict(payload.get("coverage_status_counts", {})).items()
        },
        "check_status_counts": {
            key: int(value)
            for key, value in dict(payload.get("check_status_counts", {})).items()
        },
        "blocker_kind_counts": {
            key: int(value)
            for key, value in dict(payload.get("blocker_kind_counts", {})).items()
        },
    }


def _raw_capture_signature(
    _artifacts: FilesystemArtifactStore,
    raw_capture_root: Path,
) -> tuple[str, ...]:
    signatures: list[str] = []
    for file_path in sorted(
        path for path in raw_capture_root.rglob("*") if path.is_file()
    ):
        relative_path = file_path.relative_to(raw_capture_root).as_posix()
        if relative_path in {"capture.json", "manifest.csv", "manifest_issues.csv"}:
            continue
        signatures.append(
            "|".join(
                (
                    relative_path,
                    hashlib.sha256(file_path.read_bytes()).hexdigest(),
                    str(file_path.stat().st_size),
                )
            )
        )
    return tuple(sorted(signatures))


def collect_workspace_metrics(request: MetricCollectionRequest) -> WorkspaceMetrics:
    artifacts = request.artifacts
    workspace_root = request.workspace_root
    raw_capture_signatures: dict[str, tuple[str, ...]] = {}
    capture_registry_rows: dict[str, dict[str, str]] = {}
    for row in request.latest_capture_rows:
        source = row.get("source", "")
        if request.selected_sources and source not in request.selected_sources:
            continue
        raw_capture_root = request.resolve_capture_root(workspace_root, row)
        if raw_capture_root is None or not raw_capture_root.is_dir():
            continue
        key = f"{source}:{row.get('manifest_fingerprint', '')}"
        raw_capture_signatures[key] = _raw_capture_signature(
            artifacts, raw_capture_root
        )
        capture_registry_rows[key] = {
            "status": row.get("status", ""),
            "file_count": row.get("file_count", ""),
            "observed_period_start": row.get("observed_period_start", ""),
            "observed_period_end": row.get("observed_period_end", ""),
        }

    source_metrics: dict[str, SourceMetrics] = {}
    assembled_root = workspace_root / "working" / "normalized" / "sources"
    if not assembled_root.is_dir():
        raise ValueError(
            f"workspace does not contain assembled source datasets: {assembled_root}"
        )
    for source_root in sorted(
        path for path in assembled_root.iterdir() if path.is_dir()
    ):
        if (
            request.selected_sources
            and source_root.name not in request.selected_sources
        ):
            continue
        issue_rows = artifacts.read_rows(source_root / "exceptions.csv")
        assembly_issue_rows = (
            artifacts.read_rows(source_root / "assembly_issues.csv")
            if (source_root / "assembly_issues.csv").is_file()
            else []
        )
        source_metrics[source_root.name] = SourceMetrics(
            source=source_root.name,
            fact_count=len(artifacts.read_rows(source_root / "facts.csv")),
            balance_count=len(artifacts.read_rows(source_root / "balances.csv")),
            balance_evidence_count=len(
                artifacts.read_rows(source_root / "balance_evidence.csv")
            ),
            issue_count=len(issue_rows) + len(assembly_issue_rows),
            review_count=len(
                artifacts.read_rows(source_root / "normalization_reviews.csv")
            ),
        )
    reconciliation_status_counts = _run_reconciliation(
        workspace_root, request.reconciliation_report_dir
    )
    return WorkspaceMetrics(
        raw_capture_signatures=raw_capture_signatures,
        capture_registry_rows=capture_registry_rows,
        source_metrics=source_metrics,
        reconciliation_status_counts=reconciliation_status_counts,
    )


def _compare_signatures(
    reference: tuple[str, ...],
    candidate: tuple[str, ...],
) -> tuple[str, str]:
    reference_set = set(reference)
    candidate_set = set(candidate)
    missing = ",".join(sorted(reference_set - candidate_set))
    extra = ",".join(sorted(candidate_set - reference_set))
    return missing, extra


def _write_rows(
    artifacts: FilesystemArtifactStore,
    path: Path,
    header: tuple[str, ...],
    rows: Iterable[dict[str, str]],
) -> None:
    artifacts.write_rows(path, header, tuple(rows))


def write_parity_report(request: ParityReportRequest) -> ReplayResult:
    artifacts = request.artifacts
    report_dir = request.report_dir
    reference_metrics = request.reference_metrics
    candidate_metrics = request.candidate_metrics
    mismatch_count = 0
    raw_rows: list[dict[str, str]] = []
    for key in sorted(
        set(reference_metrics.raw_capture_signatures)
        | set(candidate_metrics.raw_capture_signatures)
    ):
        reference_signature = reference_metrics.raw_capture_signatures.get(key, ())
        candidate_signature = candidate_metrics.raw_capture_signatures.get(key, ())
        missing, extra = _compare_signatures(reference_signature, candidate_signature)
        status = "match" if not missing and not extra else "mismatch"
        mismatch_count += int(status == "mismatch")
        raw_rows.append(
            {
                "capture_key": key,
                "status": status,
                "reference_file_count": str(len(reference_signature)),
                "candidate_file_count": str(len(candidate_signature)),
                "missing_files": missing,
                "extra_files": extra,
            }
        )

    capture_rows: list[dict[str, str]] = []
    for key in sorted(
        set(reference_metrics.capture_registry_rows)
        | set(candidate_metrics.capture_registry_rows)
    ):
        reference_row = reference_metrics.capture_registry_rows.get(key, {})
        candidate_row = candidate_metrics.capture_registry_rows.get(key, {})
        status = (
            "match" if reference_row == candidate_row and reference_row else "mismatch"
        )
        mismatch_count += int(status == "mismatch")
        capture_rows.append(
            {
                "capture_key": key,
                "status": status,
                "reference_status": reference_row.get("status", ""),
                "candidate_status": candidate_row.get("status", ""),
                "reference_file_count": reference_row.get("file_count", ""),
                "candidate_file_count": candidate_row.get("file_count", ""),
                "reference_observed_period_start": reference_row.get(
                    "observed_period_start", ""
                ),
                "candidate_observed_period_start": candidate_row.get(
                    "observed_period_start", ""
                ),
                "reference_observed_period_end": reference_row.get(
                    "observed_period_end", ""
                ),
                "candidate_observed_period_end": candidate_row.get(
                    "observed_period_end", ""
                ),
            }
        )

    source_rows: list[dict[str, str]] = []
    for source in sorted(
        set(reference_metrics.source_metrics) | set(candidate_metrics.source_metrics)
    ):
        reference_metric = reference_metrics.source_metrics.get(source)
        candidate_metric = candidate_metrics.source_metrics.get(source)
        status = (
            "match"
            if reference_metric == candidate_metric and reference_metric is not None
            else "mismatch"
        )
        mismatch_count += int(status == "mismatch")
        source_rows.append(
            {
                "source": source,
                "status": status,
                "reference_fact_count": str(
                    reference_metric.fact_count if reference_metric else ""
                ),
                "candidate_fact_count": str(
                    candidate_metric.fact_count if candidate_metric else ""
                ),
                "reference_balance_count": str(
                    reference_metric.balance_count if reference_metric else ""
                ),
                "candidate_balance_count": str(
                    candidate_metric.balance_count if candidate_metric else ""
                ),
                "reference_balance_evidence_count": str(
                    reference_metric.balance_evidence_count if reference_metric else ""
                ),
                "candidate_balance_evidence_count": str(
                    candidate_metric.balance_evidence_count if candidate_metric else ""
                ),
                "reference_issue_count": str(
                    reference_metric.issue_count if reference_metric else ""
                ),
                "candidate_issue_count": str(
                    candidate_metric.issue_count if candidate_metric else ""
                ),
                "reference_review_count": str(
                    reference_metric.review_count if reference_metric else ""
                ),
                "candidate_review_count": str(
                    candidate_metric.review_count if candidate_metric else ""
                ),
            }
        )

    reconciliation_rows: list[dict[str, str]] = []
    for group_name in sorted(
        set(reference_metrics.reconciliation_status_counts)
        | set(candidate_metrics.reconciliation_status_counts)
    ):
        reference_group = reference_metrics.reconciliation_status_counts.get(
            group_name, {}
        )
        candidate_group = candidate_metrics.reconciliation_status_counts.get(
            group_name, {}
        )
        for metric_name in sorted(set(reference_group) | set(candidate_group)):
            reference_value = reference_group.get(metric_name, 0)
            candidate_value = candidate_group.get(metric_name, 0)
            status = "match" if reference_value == candidate_value else "mismatch"
            mismatch_count += int(status == "mismatch")
            reconciliation_rows.append(
                {
                    "metric_group": group_name,
                    "metric_name": metric_name,
                    "status": status,
                    "reference_value": str(reference_value),
                    "candidate_value": str(candidate_value),
                }
            )

    _write_rows(
        artifacts,
        report_dir / "raw_capture_parity.csv",
        RAW_CAPTURE_COMPARISON_HEADER,
        raw_rows,
    )
    _write_rows(
        artifacts,
        report_dir / "capture_registry_parity.csv",
        CAPTURE_REGISTRY_COMPARISON_HEADER,
        capture_rows,
    )
    _write_rows(
        artifacts,
        report_dir / "source_metrics_parity.csv",
        SOURCE_METRIC_COMPARISON_HEADER,
        source_rows,
    )
    _write_rows(
        artifacts,
        report_dir / "reconciliation_status_parity.csv",
        RECONCILIATION_COMPARISON_HEADER,
        reconciliation_rows,
    )
    artifacts.write_json(
        report_dir / "summary.json",
        {
            "reference_workspace": str(request.reference_workspace),
            "candidate_workspace": str(request.candidate_workspace),
            "reference_capture_count": len(reference_metrics.capture_registry_rows),
            "candidate_capture_count": len(candidate_metrics.capture_registry_rows),
            "mismatch_count": mismatch_count,
            "passed": mismatch_count == 0,
        },
    )
    return ReplayResult(
        report_dir=report_dir,
        candidate_workspace=request.candidate_workspace,
        reference_capture_count=len(reference_metrics.capture_registry_rows),
        candidate_capture_count=len(candidate_metrics.capture_registry_rows),
        mismatch_count=mismatch_count,
    )
