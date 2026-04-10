"""Assemble accepted capture-normalized artifacts into source datasets."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import cast

from tallylot.application.intake.captures.persistence import (
    append_capture_status_record,
    update_source_inventory_summary,
)
from tallylot.application.normalization.capture_paths import (
    capture_normalized_root,
    source_assembled_root,
)
from tallylot.application.normalization.contracts import (
    AssembleSourceRequest,
    AssembleSourceResponse,
)
from tallylot.application.resource_refs import path_from_ref, to_resource_ref
from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import (
    BALANCE_CONFIRMATION_HEADER,
    BALANCE_EVIDENCE_HEADER,
    BALANCE_SNAPSHOT_HEADER,
    ISSUE_HEADER,
    LOCATION_INVENTORY_HEADER,
    NORMALIZATION_REVIEW_HEADER,
)
from tallylot.ports.facts import FACT_HEADER

from .merge import (
    balance_semantic_key,
    ConflictPolicy,
    CsvArtifactMergeSpec,
    merge_csv_artifact,
    merge_json_array_artifact,
    row_key,
)

_ASSEMBLY_INCLUDED_STATUSES = frozenset({"normalized", "assembly_included"})
_ASSEMBLY_EXCLUDED_STATUSES = frozenset(
    {"duplicate_blocked", "overlap_review_required", "superseded"}
)


class AssembleSourceUseCase:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: AssembleSourceRequest) -> AssembleSourceResponse:
        workspace_root = path_from_ref(request.workspace_root_ref)
        output_root = (
            path_from_ref(request.assembled_output_ref)
            if request.assembled_output_ref is not None
            else source_assembled_root(workspace_root, request.source)
        )
        capture_rows = _latest_capture_rows_for_source(
            self._read_capture_registry(workspace_root), request.source
        )
        included_rows, excluded_rows = _partition_capture_rows(capture_rows)
        included_capture_roots = tuple(
            capture_normalized_root(workspace_root, row["capture_uid"])
            for row in included_rows
            if capture_normalized_root(workspace_root, row["capture_uid"]).is_dir()
        )
        missing_capture_rows = tuple(
            row
            for row in included_rows
            if not capture_normalized_root(workspace_root, row["capture_uid"]).is_dir()
        )

        facts, fact_issues = merge_csv_artifact(
            self._artifacts,
            included_capture_roots,
            CsvArtifactMergeSpec(
                filename="facts.csv",
                header=FACT_HEADER,
                conflict_policy=ConflictPolicy(
                    semantic_key=lambda row: row.get("fact_id", ""),
                    conflict_key=row_key,
                    message=(
                        "Source assembly found conflicting fact rows for the same "
                        "fact_id."
                    ),
                ),
            ),
            source=request.source,
        )
        fact_annotations = merge_json_array_artifact(
            included_capture_roots,
            filename="fact_annotations.json",
        )
        balances, balance_issues = merge_csv_artifact(
            self._artifacts,
            included_capture_roots,
            CsvArtifactMergeSpec(
                filename="balances.csv",
                header=BALANCE_SNAPSHOT_HEADER,
                conflict_policy=ConflictPolicy(
                    semantic_key=balance_semantic_key,
                    conflict_key=lambda row: row.get("quantity", ""),
                    message=(
                        "Source assembly found conflicting balances for the same "
                        "semantic key."
                    ),
                ),
            ),
            source=request.source,
        )
        balance_evidence, balance_evidence_issues = merge_csv_artifact(
            self._artifacts,
            included_capture_roots,
            CsvArtifactMergeSpec(
                filename="balance_evidence.csv",
                header=BALANCE_EVIDENCE_HEADER,
                conflict_policy=ConflictPolicy(
                    semantic_key=balance_semantic_key,
                    conflict_key=lambda row: row.get("quantity", ""),
                    message=(
                        "Source assembly found conflicting balance evidence "
                        "quantities for the same semantic key."
                    ),
                ),
            ),
            source=request.source,
        )
        balance_confirmations, confirmation_issues = merge_csv_artifact(
            self._artifacts,
            included_capture_roots,
            CsvArtifactMergeSpec(
                filename="balance_confirmations.csv",
                header=BALANCE_CONFIRMATION_HEADER,
                conflict_policy=ConflictPolicy(
                    semantic_key=balance_semantic_key,
                    conflict_key=lambda row: row.get("quantity", ""),
                    message=(
                        "Source assembly found conflicting balance confirmations "
                        "for the same semantic key."
                    ),
                ),
            ),
            source=request.source,
        )
        exceptions, _ = merge_csv_artifact(
            self._artifacts,
            included_capture_roots,
            CsvArtifactMergeSpec(
                filename="exceptions.csv",
                header=ISSUE_HEADER,
            ),
            source=request.source,
        )
        reviews, _ = merge_csv_artifact(
            self._artifacts,
            included_capture_roots,
            CsvArtifactMergeSpec(
                filename="normalization_reviews.csv",
                header=NORMALIZATION_REVIEW_HEADER,
            ),
            source=request.source,
        )
        location_inventory, _ = merge_csv_artifact(
            self._artifacts,
            included_capture_roots,
            CsvArtifactMergeSpec(
                filename="location_inventory.csv",
                header=LOCATION_INVENTORY_HEADER,
            ),
            source=request.source,
        )
        assembly_issues = (
            *fact_issues,
            *balance_issues,
            *balance_evidence_issues,
            *confirmation_issues,
            *(
                _missing_capture_issue(request.source, row)
                for row in missing_capture_rows
            ),
        )

        self._artifacts.write_rows(output_root / "facts.csv", FACT_HEADER, facts)
        self._artifacts.write_json(
            output_root / "fact_annotations.json",
            cast(JsonValue, fact_annotations),
        )
        self._artifacts.write_rows(
            output_root / "balances.csv", BALANCE_SNAPSHOT_HEADER, balances
        )
        self._artifacts.write_rows(
            output_root / "balance_evidence.csv",
            BALANCE_EVIDENCE_HEADER,
            balance_evidence,
        )
        if balance_confirmations:
            self._artifacts.write_rows(
                output_root / "balance_confirmations.csv",
                BALANCE_CONFIRMATION_HEADER,
                balance_confirmations,
            )
        self._artifacts.write_rows(
            output_root / "exceptions.csv", ISSUE_HEADER, exceptions
        )
        self._artifacts.write_rows(
            output_root / "normalization_reviews.csv",
            NORMALIZATION_REVIEW_HEADER,
            reviews,
        )
        self._artifacts.write_rows(
            output_root / "location_inventory.csv",
            LOCATION_INVENTORY_HEADER,
            location_inventory,
        )
        self._artifacts.write_rows(
            output_root / "assembly_issues.csv",
            ISSUE_HEADER,
            (issue.to_row() for issue in assembly_issues),
        )
        self._artifacts.write_json(
            output_root / "assembly_summary.json",
            cast(
                JsonValue,
                {
                    "source": request.source,
                    "included_capture_count": len(included_capture_roots),
                    "excluded_capture_count": len(excluded_rows)
                    + len(missing_capture_rows),
                    "fact_count": len(facts),
                    "balance_count": len(balances),
                    "balance_evidence_count": len(balance_evidence),
                    "issue_count": len(exceptions) + len(assembly_issues),
                    "review_count": len(reviews),
                    "included_capture_uids": [
                        row["capture_uid"]
                        for row in included_rows
                        if capture_normalized_root(
                            workspace_root, row["capture_uid"]
                        ).is_dir()
                    ],
                    "excluded_capture_uids": [
                        *(row["capture_uid"] for row in excluded_rows),
                        *(row["capture_uid"] for row in missing_capture_rows),
                    ],
                },
            ),
        )

        for row in included_rows:
            status = (
                "assembly_included"
                if row not in missing_capture_rows
                else "assembly_excluded"
            )
            append_capture_status_record(
                artifacts=self._artifacts,
                workspace_root=workspace_root,
                capture_uid=row["capture_uid"],
                status=status,
            )
        for row in excluded_rows:
            append_capture_status_record(
                artifacts=self._artifacts,
                workspace_root=workspace_root,
                capture_uid=row["capture_uid"],
                status="assembly_excluded",
                notes=f"Excluded from source assembly from status {row.get('status', '')}.",
            )
        update_source_inventory_summary(
            artifacts=self._artifacts,
            workspace_root=workspace_root,
            source=request.source,
            status="assembled",
            assembly_status="assembled",
            assembled_root_ref=_workspace_relative_ref(workspace_root, output_root),
        )
        return AssembleSourceResponse(
            assembled_output_ref=to_resource_ref(output_root),
            included_capture_count=len(included_capture_roots),
            excluded_capture_count=len(excluded_rows) + len(missing_capture_rows),
            fact_count=len(facts),
            balance_count=len(balances),
            balance_evidence_count=len(balance_evidence),
            issue_count=len(exceptions) + len(assembly_issues),
            review_count=len(reviews),
        )

    def _read_capture_registry(self, workspace_root: Path) -> list[dict[str, str]]:
        path = workspace_root / "analysis" / "inventory" / "source_captures.csv"
        if not path.exists():
            return []
        return self._artifacts.read_rows(path)


def _latest_capture_rows_for_source(
    rows: list[dict[str, str]],
    source: str,
) -> tuple[dict[str, str], ...]:
    latest_by_uid: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("source", "") != source:
            continue
        capture_uid = row.get("capture_uid", "")
        if capture_uid:
            latest_by_uid[capture_uid] = row
    return tuple(latest_by_uid[uid] for uid in sorted(latest_by_uid))


def _partition_capture_rows(
    rows: tuple[dict[str, str], ...],
) -> tuple[tuple[dict[str, str], ...], tuple[dict[str, str], ...]]:
    included: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []
    for row in rows:
        status = row.get("status", "")
        if status in _ASSEMBLY_INCLUDED_STATUSES:
            included.append(row)
        elif status in _ASSEMBLY_EXCLUDED_STATUSES:
            excluded.append(row)
        else:
            excluded.append(row)
    return tuple(included), tuple(excluded)


def _missing_capture_issue(source: str, row: Mapping[str, str]) -> IssueRecord:
    capture_uid = row.get("capture_uid", "")
    return IssueRecord(
        issue_id=f"assembly:{source}:missing_normalized_capture:{capture_uid}",
        source=source,
        adapter_id="source_assembly",
        severity="high",
        kind="assembly_missing_normalized_capture",
        message="Source assembly skipped a capture because its normalized root was not present.",
        raw_file="source_captures.csv",
        raw_row_ref=capture_uid,
    )


def _workspace_relative_ref(workspace_root: Path, path: Path) -> str:
    try:
        return path.relative_to(workspace_root).as_posix()
    except ValueError:
        return path.as_posix()
