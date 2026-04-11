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
    CaptureRegistryMetrics,
    MetricCollectionRequest,
    ParityReportRequest,
    RAW_CAPTURE_COMPARISON_HEADER,
    RECONCILIATION_COMPARISON_HEADER,
    ReplayResult,
    SOURCE_METRIC_COMPARISON_HEADER,
    SourceMetrics,
    WorkspaceMetrics,
)
from .source_metric_parity import build_source_metric_row


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
    capture_registry_rows: dict[str, CaptureRegistryMetrics] = {}
    capture_key_counts: dict[str, int] = {}
    for row in request.latest_capture_rows:
        source = row.get("source", "")
        if request.selected_sources and source not in request.selected_sources:
            continue
        manifest_fingerprint = row.get("manifest_fingerprint", "")
        key = _capture_registry_key(
            source=source,
            manifest_fingerprint=manifest_fingerprint,
            key_counts=capture_key_counts,
        )
        capture_registry_rows[key] = CaptureRegistryMetrics(
            source=source,
            status=row.get("status", ""),
            file_count=row.get("file_count", ""),
            manifest_fingerprint=manifest_fingerprint,
            observed_period_start=row.get("observed_period_start", ""),
            observed_period_end=row.get("observed_period_end", ""),
            capture_root_ref_present=bool(row.get("capture_root_ref", "").strip()),
        )
        raw_capture_root = request.resolve_capture_root(workspace_root, row)
        if raw_capture_root is not None and raw_capture_root.is_dir():
            raw_capture_signatures[key] = _raw_capture_signature(raw_capture_root)

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
            snapshot_count=len(
                artifacts.read_rows(source_root / "balance_snapshots.csv")
            ),
            reference_count=len(
                artifacts.read_rows(source_root / "balance_references.csv")
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


def _capture_registry_key(
    *,
    source: str,
    manifest_fingerprint: str,
    key_counts: dict[str, int],
) -> str:
    base_key = f"{source}:{manifest_fingerprint or '<missing-manifest>'}"
    key_counts[base_key] = key_counts.get(base_key, 0) + 1
    occurrence = key_counts[base_key]
    if occurrence == 1:
        return base_key
    return f"{base_key}#{occurrence}"


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


def _presence(value: bool) -> str:
    return "yes" if value else "no"


def write_parity_report(request: ParityReportRequest) -> ReplayResult:
    artifacts = request.artifacts
    report_dir = request.report_dir
    reference_metrics = request.reference_metrics
    candidate_metrics = request.candidate_metrics
    mismatch_count = 0
    expected_difference_count = 0
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
        reference_row = reference_metrics.capture_registry_rows.get(key)
        candidate_row = candidate_metrics.capture_registry_rows.get(key)
        status = (
            "match" if reference_row == candidate_row and reference_row else "mismatch"
        )
        mismatch_count += int(status == "mismatch")
        capture_rows.append(
            {
                "capture_key": key,
                "status": status,
                "reference_source": reference_row.source if reference_row else "",
                "candidate_source": candidate_row.source if candidate_row else "",
                "reference_status": reference_row.status if reference_row else "",
                "candidate_status": candidate_row.status if candidate_row else "",
                "reference_file_count": (
                    reference_row.file_count if reference_row else ""
                ),
                "candidate_file_count": (
                    candidate_row.file_count if candidate_row else ""
                ),
                "reference_manifest_fingerprint": (
                    reference_row.manifest_fingerprint if reference_row else ""
                ),
                "candidate_manifest_fingerprint": (
                    candidate_row.manifest_fingerprint if candidate_row else ""
                ),
                "reference_observed_period_start": (
                    reference_row.observed_period_start if reference_row else ""
                ),
                "candidate_observed_period_start": (
                    candidate_row.observed_period_start if candidate_row else ""
                ),
                "reference_observed_period_end": (
                    reference_row.observed_period_end if reference_row else ""
                ),
                "candidate_observed_period_end": (
                    candidate_row.observed_period_end if candidate_row else ""
                ),
                "reference_capture_root_ref_present": (
                    _presence(reference_row.capture_root_ref_present)
                    if reference_row
                    else ""
                ),
                "candidate_capture_root_ref_present": (
                    _presence(candidate_row.capture_root_ref_present)
                    if candidate_row
                    else ""
                ),
            }
        )

    source_rows: list[dict[str, str]] = []
    for source in sorted(
        set(reference_metrics.source_metrics)
        | set(candidate_metrics.source_metrics)
        | request.expected_differences.sources()
    ):
        reference_metric = reference_metrics.source_metrics.get(source)
        candidate_metric = candidate_metrics.source_metrics.get(source)
        expected_difference = request.expected_differences.for_source(source)
        source_comparison = build_source_metric_row(
            source=source,
            reference_metric=reference_metric,
            candidate_metric=candidate_metric,
            expected_difference=expected_difference,
        )
        mismatch_count += int(source_comparison.is_mismatch)
        expected_difference_count += int(source_comparison.uses_expected_difference)
        source_rows.append(source_comparison.row)

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
            "expected_difference_count": expected_difference_count,
            "declared_expected_difference_count": (
                request.expected_differences.declared_count()
            ),
            "passed": mismatch_count == 0,
            "passed_with_expected_differences": (
                mismatch_count == 0 and expected_difference_count > 0
            ),
            "pass_status": (
                "failed"
                if mismatch_count
                else (
                    "passed-with-expected-differences"
                    if expected_difference_count
                    else "clean"
                )
            ),
        },
    )
    return ReplayResult(
        report_dir=report_dir,
        candidate_workspace=request.candidate_workspace,
        reference_capture_count=len(reference_metrics.capture_registry_rows),
        candidate_capture_count=len(candidate_metrics.capture_registry_rows),
        mismatch_count=mismatch_count,
        expected_difference_count=expected_difference_count,
        passed_with_expected_differences=(
            mismatch_count == 0 and expected_difference_count > 0
        ),
    )
