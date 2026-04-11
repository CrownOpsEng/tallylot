"""I/O helpers for balance check artifact management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tallylot.application.balances.filenames import (
    BALANCE_ASSERTION_FILENAME,
    BALANCE_CHECK_SUMMARY_FILENAME,
    BALANCE_RECONCILIATION_SUMMARY_FILENAME,
)
from tallylot.application.balances.inputs import BalanceSourceDir
from tallylot.application.workspace.filesystem import (
    ensure_output_not_within_input_tree,
)
from tallylot.domain.balances import BalanceReference
from tallylot.domain.issues import IssueRecord
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import EvidenceRepositoryPort, ISSUE_HEADER


@dataclass(frozen=True)
class BalanceReferenceCacheUpdate:
    existing_references: tuple[BalanceReference, ...]
    resolved_references: tuple[BalanceReference, ...]
    reference_issues: tuple[IssueRecord, ...]


_GENERATED_OUTPUT_FILENAMES = (
    BALANCE_ASSERTION_FILENAME,
    BALANCE_CHECK_SUMMARY_FILENAME,
    BALANCE_RECONCILIATION_SUMMARY_FILENAME,
    "cross_source_assertions.csv",
    "cross_source_issues.csv",
    "cross_source_summary.json",
    "reconciliation_issues.csv",
)


def ensure_balance_check_output_root_is_safe(
    input_root: Path,
    output_root: Path,
) -> None:
    ensure_output_not_within_input_tree(
        input_root,
        output_root,
        input_label="balance input root",
        output_label="balance check output root",
    )


def ensure_balance_source_output_paths_are_safe(
    source_dir: BalanceSourceDir,
    output_root: Path,
) -> None:
    for input_label, input_path in (
        ("balance facts input", source_dir.facts_path),
        ("balance snapshot input", source_dir.snapshot_path),
        ("balance reference input", source_dir.reference_path),
    ):
        ensure_output_not_within_input_tree(
            input_path,
            output_root,
            input_label=input_label,
            output_label="balance check output root",
        )


def ensure_balance_output_paths_are_distinct(*paths: Path) -> None:
    seen_paths: set[Path] = set()
    for path in paths:
        if path in seen_paths:
            raise ValueError(f"balance check outputs must be distinct: {path}")
        seen_paths.add(path)


def clear_generated_balance_check_outputs(output_root: Path) -> None:
    for filename in _GENERATED_OUTPUT_FILENAMES:
        path = output_root / filename
        if path.is_file() or path.is_symlink():
            path.unlink()


def clear_generated_balance_reference_issue_output(path: Path) -> None:
    if path.is_file() or path.is_symlink():
        path.unlink()


def persist_balance_reference_cache(
    *,
    source_dir: BalanceSourceDir,
    artifacts: ArtifactStorePort,
    evidence: EvidenceRepositoryPort,
    update: BalanceReferenceCacheUpdate,
) -> None:
    merged_references = {
        (
            reference.target,
            reference.reference_kind.value,
            reference.observed_at,
            reference.observed_precision.value,
            reference.support_ref,
        ): reference
        for reference in (*update.existing_references, *update.resolved_references)
    }
    evidence.write_balance_references(
        source_dir.reference_path,
        tuple(
            merged_references[key]
            for key in sorted(
                merged_references,
                key=lambda item: (
                    str(item[0].source),
                    str(item[0].location_id),
                    str(item[0].instrument_id),
                    item[0].balance_kind,
                    item[0].target_at,
                    item[1],
                    item[2],
                ),
            )
        ),
    )
    if update.reference_issues:
        artifacts.write_rows(
            source_dir.reference_issue_path,
            ISSUE_HEADER,
            tuple(issue.to_row() for issue in update.reference_issues),
        )
    else:
        clear_generated_balance_reference_issue_output(source_dir.reference_issue_path)


def read_rows_if_present(
    artifacts: ArtifactStorePort,
    path: Path,
) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    return artifacts.read_rows(path)
