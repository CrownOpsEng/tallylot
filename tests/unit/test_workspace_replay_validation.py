from __future__ import annotations

import json
from pathlib import Path

import pytest

from tallylot.infrastructure.serialization import FilesystemArtifactStore
from tallylot.ports.captures import SOURCE_CAPTURE_HEADER
from tools.workspace_replay_validation.comparison import (
    _raw_capture_signature,
    collect_workspace_metrics,
    write_parity_report,
)
from tools.workspace_replay_validation.expected_differences import (
    load_expected_differences,
)
from tools.workspace_replay_validation.models import (
    CaptureRegistryMetrics,
    ExpectedDifferenceSet,
    ExpectedMetricDifference,
    MetricCollectionRequest,
    ParityReportRequest,
    SourceMetrics,
    WorkspaceMetrics,
)
from tools.workspace_replay_validation.workflow import _reference_captures


def _empty_reconciliation_counts(
    _workspace_root: Path,
    _report_dir: Path,
) -> dict[str, dict[str, int]]:
    return {}


def _missing_capture_root(
    _workspace_root: Path,
    _row: dict[str, str],
) -> Path | None:
    return None


def test_reference_captures_ignore_non_materialized_registry_rows(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv",
        SOURCE_CAPTURE_HEADER,
        (
            {
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "source": "coinbase",
                "capture_label": "2026-03-23T14-15-16Z",
                "status": "normalized",
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/coinbase",
                "capture_root_ref": "evidence/raw/source/coinbase/2026-03-23T14-15-16Z",
                "manifest_fingerprint": "manifest:present",
                "file_count": "1",
                "observed_period_start": "2026-03-23",
                "observed_period_end": "2026-03-23",
                "observed_group_count": "1",
                "supersedes_capture_uid": "",
                "notes": "",
            },
            {
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9F",
                "source": "coinbase",
                "capture_label": "2026-03-24T14-15-16Z",
                "status": "duplicate_blocked",
                "intake_started_at": "2026-03-24 14:15:16",
                "intake_completed_at": "2026-03-24 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/coinbase",
                "capture_root_ref": "evidence/raw/source/coinbase/2026-03-24T14-15-16Z",
                "manifest_fingerprint": "manifest:missing",
                "file_count": "1",
                "observed_period_start": "2026-03-24",
                "observed_period_end": "2026-03-24",
                "observed_group_count": "1",
                "supersedes_capture_uid": "",
                "notes": "",
            },
        ),
    )
    present_root = (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "coinbase"
        / "2026-03-23T14-15-16Z"
    )
    present_root.mkdir(parents=True)
    (present_root / "capture.json").write_text("{}", encoding="utf-8")
    (present_root / "manifest.csv").write_text(
        "relative_path,sha256,size_bytes\n", encoding="utf-8"
    )

    captures = _reference_captures(
        artifacts=artifacts,
        workspace_root=workspace_root,
        selected_sources=frozenset(),
    )

    assert len(captures) == 1
    assert captures[0].manifest_fingerprint == "manifest:present"


def test_raw_capture_signature_ignores_derived_capture_files(tmp_path: Path) -> None:
    raw_capture_root = tmp_path / "capture"
    raw_capture_root.mkdir()
    (raw_capture_root / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (raw_capture_root / "capture.json").write_text("{}", encoding="utf-8")
    (raw_capture_root / "manifest.csv").write_text("header\n", encoding="utf-8")
    (raw_capture_root / "manifest_issues.csv").write_text("header\n", encoding="utf-8")

    signature = _raw_capture_signature(raw_capture_root)

    assert len(signature) == 1
    assert signature[0].startswith("transactions.csv|")


def test_workspace_metrics_keep_non_materialized_duplicate_registry_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "report"
    (workspace_root / "working" / "normalized" / "sources").mkdir(parents=True)
    monkeypatch.setattr(
        "tools.workspace_replay_validation.comparison._run_reconciliation",
        _empty_reconciliation_counts,
    )

    metrics = collect_workspace_metrics(
        MetricCollectionRequest(
            artifacts=FilesystemArtifactStore(),
            workspace_root=workspace_root,
            selected_sources=frozenset(),
            reconciliation_report_dir=report_dir,
            latest_capture_rows=(
                {
                    "source": "binance",
                    "status": "normalized",
                    "file_count": "1",
                    "manifest_fingerprint": "manifest:fixture",
                    "observed_period_start": "2026-03-01",
                    "observed_period_end": "2026-03-31",
                    "capture_root_ref": "",
                },
                {
                    "source": "binance",
                    "status": "duplicate_blocked",
                    "file_count": "1",
                    "manifest_fingerprint": "manifest:fixture",
                    "observed_period_start": "2026-03-01",
                    "observed_period_end": "2026-03-31",
                    "capture_root_ref": "",
                },
            ),
            resolve_capture_root=_missing_capture_root,
        )
    )

    assert set(metrics.capture_registry_rows) == {
        "binance:manifest:fixture",
        "binance:manifest:fixture#2",
    }
    assert not metrics.raw_capture_signatures
    assert metrics.capture_registry_rows[
        "binance:manifest:fixture"
    ] == CaptureRegistryMetrics(
        source="binance",
        status="normalized",
        file_count="1",
        manifest_fingerprint="manifest:fixture",
        observed_period_start="2026-03-01",
        observed_period_end="2026-03-31",
        capture_root_ref_present=False,
    )
    assert (
        metrics.capture_registry_rows["binance:manifest:fixture#2"].status
        == "duplicate_blocked"
    )


def test_capture_registry_parity_compares_full_semantic_surface(
    tmp_path: Path,
) -> None:
    report_dir = tmp_path / "report"
    artifacts = FilesystemArtifactStore()
    reference_metrics = _workspace_metrics(
        capture_registry_rows={
            "coinbase:manifest:fixture": CaptureRegistryMetrics(
                source="coinbase",
                status="normalized",
                file_count="2",
                manifest_fingerprint="manifest:fixture",
                observed_period_start="2026-03-01",
                observed_period_end="2026-03-31",
                capture_root_ref_present=True,
            )
        }
    )
    candidate_metrics = _workspace_metrics(
        capture_registry_rows={
            "coinbase:manifest:fixture": CaptureRegistryMetrics(
                source="coinbase",
                status="normalized",
                file_count="2",
                manifest_fingerprint="manifest:fixture",
                observed_period_start="2026-03-01",
                observed_period_end="2026-03-31",
                capture_root_ref_present=False,
            )
        }
    )

    result = write_parity_report(
        ParityReportRequest(
            artifacts=artifacts,
            report_dir=report_dir,
            reference_workspace=tmp_path / "reference",
            candidate_workspace=tmp_path / "candidate",
            reference_metrics=reference_metrics,
            candidate_metrics=candidate_metrics,
        )
    )
    rows = artifacts.read_rows(report_dir / "capture_registry_parity.csv")

    assert result.mismatch_count == 1
    assert rows == [
        {
            "capture_key": "coinbase:manifest:fixture",
            "status": "mismatch",
            "reference_source": "coinbase",
            "candidate_source": "coinbase",
            "reference_status": "normalized",
            "candidate_status": "normalized",
            "reference_file_count": "2",
            "candidate_file_count": "2",
            "reference_manifest_fingerprint": "manifest:fixture",
            "candidate_manifest_fingerprint": "manifest:fixture",
            "reference_observed_period_start": "2026-03-01",
            "candidate_observed_period_start": "2026-03-01",
            "reference_observed_period_end": "2026-03-31",
            "candidate_observed_period_end": "2026-03-31",
            "reference_capture_root_ref_present": "yes",
            "candidate_capture_root_ref_present": "no",
        }
    ]


def test_expected_difference_fixture_accepts_source_and_pack_deltas(
    tmp_path: Path,
) -> None:
    fixture_path = tmp_path / "expected-differences.json"
    fixture_path.write_text(
        json.dumps(
            {
                "sources": {
                    "binance": {
                        "issue_count_delta": 1,
                        "reason": "shared extraction emits one extra review issue",
                    }
                },
                "packs": {
                    "shakepay/cash_crypto_mix": {
                        "source": "shakepay",
                        "review_count_delta": -1,
                        "reason": "fixture intentionally drops a stale review",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    expected_differences = load_expected_differences(fixture_path)

    assert expected_differences.for_source("binance") == ExpectedMetricDifference(
        source="binance",
        issue_count_delta=1,
        review_count_delta=0,
        reason=("source binance: shared extraction emits one extra review issue"),
    )
    assert expected_differences.for_source("shakepay") == ExpectedMetricDifference(
        source="shakepay",
        issue_count_delta=0,
        review_count_delta=-1,
        reason=(
            "pack shakepay/cash_crypto_mix: fixture intentionally drops a stale review"
        ),
    )


def test_expected_difference_fixture_rejects_forbidden_tolerances(
    tmp_path: Path,
) -> None:
    fixture_path = tmp_path / "expected-differences.json"
    fixture_path.write_text(
        json.dumps(
            {
                "sources": {
                    "binance": {
                        "issue_count_delta": 1,
                        "fact_count_delta": 1,
                        "reason": "facts must never be tolerated",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="fact_count_delta"):
        load_expected_differences(fixture_path)


def test_expected_difference_fixture_requires_reason(tmp_path: Path) -> None:
    fixture_path = tmp_path / "expected-differences.json"
    fixture_path.write_text(
        json.dumps({"sources": {"binance": {"issue_count_delta": 1}}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="reason"):
        load_expected_differences(fixture_path)


def test_source_metric_parity_allows_declared_issue_review_drift_only(
    tmp_path: Path,
) -> None:
    report_dir = tmp_path / "report"
    artifacts = FilesystemArtifactStore()

    result = write_parity_report(
        ParityReportRequest(
            artifacts=artifacts,
            report_dir=report_dir,
            reference_workspace=tmp_path / "reference",
            candidate_workspace=tmp_path / "candidate",
            reference_metrics=_workspace_metrics(
                source_metrics={
                    "binance": SourceMetrics(
                        source="binance",
                        fact_count=4,
                        balance_count=2,
                        balance_evidence_count=2,
                        issue_count=1,
                        review_count=3,
                    )
                }
            ),
            candidate_metrics=_workspace_metrics(
                source_metrics={
                    "binance": SourceMetrics(
                        source="binance",
                        fact_count=4,
                        balance_count=2,
                        balance_evidence_count=2,
                        issue_count=2,
                        review_count=1,
                    )
                }
            ),
            expected_differences=ExpectedDifferenceSet(
                differences_by_source={
                    "binance": ExpectedMetricDifference(
                        source="binance",
                        issue_count_delta=1,
                        review_count_delta=-2,
                        reason="source binance: parser issue taxonomy changed",
                    )
                }
            ),
        )
    )
    summary = json.loads((report_dir / "summary.json").read_text(encoding="utf-8"))
    source_rows = artifacts.read_rows(report_dir / "source_metrics_parity.csv")

    assert result.mismatch_count == 0
    assert result.expected_difference_count == 1
    assert result.passed_with_expected_differences is True
    assert summary["pass_status"] == "passed-with-expected-differences"
    assert source_rows[0]["status"] == "expected_difference"
    assert source_rows[0]["hard_metric_status"] == "match"
    assert source_rows[0]["issue_count_status"] == "permitted_drift"
    assert source_rows[0]["review_count_status"] == "permitted_drift"


@pytest.mark.parametrize(
    "candidate_metric",
    (
        SourceMetrics(
            source="binance",
            fact_count=5,
            balance_count=2,
            balance_evidence_count=2,
            issue_count=2,
            review_count=1,
        ),
        SourceMetrics(
            source="binance",
            fact_count=4,
            balance_count=3,
            balance_evidence_count=2,
            issue_count=2,
            review_count=1,
        ),
        SourceMetrics(
            source="binance",
            fact_count=4,
            balance_count=2,
            balance_evidence_count=3,
            issue_count=2,
            review_count=1,
        ),
    ),
    ids=("fact-count", "balance-count", "balance-evidence-count"),
)
def test_source_metric_parity_rejects_fact_balance_or_evidence_drift(
    tmp_path: Path,
    candidate_metric: SourceMetrics,
) -> None:
    report_dir = tmp_path / "report"
    artifacts = FilesystemArtifactStore()

    result = write_parity_report(
        ParityReportRequest(
            artifacts=artifacts,
            report_dir=report_dir,
            reference_workspace=tmp_path / "reference",
            candidate_workspace=tmp_path / "candidate",
            reference_metrics=_workspace_metrics(
                source_metrics={
                    "binance": SourceMetrics(
                        source="binance",
                        fact_count=4,
                        balance_count=2,
                        balance_evidence_count=2,
                        issue_count=1,
                        review_count=1,
                    )
                }
            ),
            candidate_metrics=_workspace_metrics(
                source_metrics={"binance": candidate_metric}
            ),
            expected_differences=ExpectedDifferenceSet(
                differences_by_source={
                    "binance": ExpectedMetricDifference(
                        source="binance",
                        issue_count_delta=1,
                        review_count_delta=0,
                        reason="source binance: issue taxonomy changed",
                    )
                }
            ),
        )
    )
    source_rows = artifacts.read_rows(report_dir / "source_metrics_parity.csv")

    assert result.mismatch_count == 1
    assert source_rows[0]["status"] == "mismatch"
    assert source_rows[0]["hard_metric_status"] == "mismatch"


def test_source_metric_parity_rejects_unused_expected_difference(
    tmp_path: Path,
) -> None:
    report_dir = tmp_path / "report"
    artifacts = FilesystemArtifactStore()

    result = write_parity_report(
        ParityReportRequest(
            artifacts=artifacts,
            report_dir=report_dir,
            reference_workspace=tmp_path / "reference",
            candidate_workspace=tmp_path / "candidate",
            reference_metrics=_workspace_metrics(),
            candidate_metrics=_workspace_metrics(),
            expected_differences=ExpectedDifferenceSet(
                differences_by_source={
                    "binance": ExpectedMetricDifference(
                        source="binance",
                        issue_count_delta=1,
                        review_count_delta=0,
                        reason="source binance: stale fixture entry",
                    )
                }
            ),
        )
    )
    source_rows = artifacts.read_rows(report_dir / "source_metrics_parity.csv")

    assert result.mismatch_count == 1
    assert source_rows[0]["source"] == "binance"
    assert source_rows[0]["status"] == "mismatch"
    assert source_rows[0]["hard_metric_status"] == "mismatch"


def test_raw_completeness_drift_is_a_hard_mismatch(tmp_path: Path) -> None:
    report_dir = tmp_path / "report"

    result = write_parity_report(
        ParityReportRequest(
            artifacts=FilesystemArtifactStore(),
            report_dir=report_dir,
            reference_workspace=tmp_path / "reference",
            candidate_workspace=tmp_path / "candidate",
            reference_metrics=_workspace_metrics(
                raw_capture_signatures={
                    "binance:manifest:fixture": ("transactions.csv|abc|12",)
                }
            ),
            candidate_metrics=_workspace_metrics(
                raw_capture_signatures={
                    "binance:manifest:fixture": ("transactions.csv|def|12",)
                }
            ),
        )
    )

    assert result.mismatch_count == 1


def test_reconciliation_status_regression_is_a_hard_mismatch(
    tmp_path: Path,
) -> None:
    report_dir = tmp_path / "report"

    result = write_parity_report(
        ParityReportRequest(
            artifacts=FilesystemArtifactStore(),
            report_dir=report_dir,
            reference_workspace=tmp_path / "reference",
            candidate_workspace=tmp_path / "candidate",
            reference_metrics=_workspace_metrics(
                reconciliation_status_counts={"coverage_status_counts": {"covered": 1}}
            ),
            candidate_metrics=_workspace_metrics(
                reconciliation_status_counts={"coverage_status_counts": {"covered": 0}}
            ),
        )
    )

    assert result.mismatch_count == 1


def _workspace_metrics(
    *,
    raw_capture_signatures: dict[str, tuple[str, ...]] | None = None,
    capture_registry_rows: dict[str, CaptureRegistryMetrics] | None = None,
    source_metrics: dict[str, SourceMetrics] | None = None,
    reconciliation_status_counts: dict[str, dict[str, int]] | None = None,
) -> WorkspaceMetrics:
    return WorkspaceMetrics(
        raw_capture_signatures=raw_capture_signatures or {},
        capture_registry_rows=capture_registry_rows or {},
        source_metrics=source_metrics or {},
        reconciliation_status_counts=reconciliation_status_counts or {},
    )
