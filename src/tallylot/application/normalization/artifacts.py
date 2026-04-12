"""Normalization artifact writing."""

from __future__ import annotations

from pathlib import Path

from tallylot.application.balances import (
    BALANCE_REFERENCE_FILENAME,
    BALANCE_REFERENCE_ISSUE_FILENAME,
    BALANCE_SNAPSHOT_FILENAME,
)
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import EvidenceRepositoryPort
from tallylot.ports.facts import FactRepositoryPort

from .models import NormalizationOutputs


def write_normalization_artifacts(
    output_dir: Path,
    *,
    facts: FactRepositoryPort,
    evidence: EvidenceRepositoryPort,
    artifacts: ArtifactStorePort,
    outputs: NormalizationOutputs,
) -> None:
    facts.write_facts(output_dir / "facts.csv", outputs.facts)
    artifacts.write_json(
        output_dir / "fact_annotations.json",
        [record.to_json() for record in outputs.fact_annotations],
    )
    artifacts.write_json(
        output_dir / "location_annotations.json",
        [record.to_json() for record in outputs.location_annotations],
    )
    evidence.write_balance_snapshots(
        output_dir / BALANCE_SNAPSHOT_FILENAME,
        outputs.balance_snapshots,
    )
    evidence.write_balance_references(
        output_dir / BALANCE_REFERENCE_FILENAME,
        outputs.balance_references,
    )
    if outputs.balance_reference_issues:
        evidence.write_issue_records(
            output_dir / BALANCE_REFERENCE_ISSUE_FILENAME,
            outputs.balance_reference_issues,
        )
    evidence.write_issue_records(output_dir / "exceptions.csv", outputs.issues)
    evidence.write_review_records(
        output_dir / "normalization_reviews.csv", outputs.reviews
    )
    evidence.write_location_inventory(
        output_dir / "location_inventory.csv", outputs.location_inventory
    )
