"""Normalization artifact writing."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.ports.evidence import EvidenceRepositoryPort
from crypto_reconciliation.ports.facts import FactRepositoryPort

from .models import NormalizationOutputs


def write_normalization_artifacts(
    output_dir: Path,
    *,
    facts: FactRepositoryPort,
    evidence: EvidenceRepositoryPort,
    outputs: NormalizationOutputs,
) -> None:
    facts.write_facts(output_dir / "facts.csv", outputs.facts)
    evidence.write_balance_snapshots(output_dir / "balances.csv", outputs.derived_balances)
    evidence.write_balance_evidence(output_dir / "balance_evidence.csv", outputs.balance_evidence)
    evidence.write_issue_records(output_dir / "exceptions.csv", outputs.issues)
    evidence.write_review_records(output_dir / "normalization_reviews.csv", outputs.reviews)
    evidence.write_wallet_inventory(output_dir / "wallet_inventory.csv", outputs.wallet_inventory)
