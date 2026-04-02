"""Normalization artifact writing."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.storage import StoragePort

from .models import NormalizationOutputs

WALLET_INVENTORY_HEADER = (
    "source",
    "capture_path",
    "wallet_id",
    "identifier_kind",
    "normalized_identifier",
    "display_identifier",
    "network_scope",
    "controller",
    "account_label",
    "evidence_kind",
    "evidence_path",
    "confidence",
    "account",
    "wallet",
    "identifier_value",
    "notes",
)


def write_normalization_artifacts(
    output_dir: Path,
    *,
    storage: StoragePort,
    artifacts: ArtifactStorePort,
    outputs: NormalizationOutputs,
) -> None:
    storage.write_transactions(output_dir / "transactions.csv", outputs.transactions)
    storage.write_balances(output_dir / "balances.csv", outputs.derived_balances)
    storage.write_balance_evidence(output_dir / "balance_evidence.csv", outputs.balance_evidence)
    storage.write_issue_records(output_dir / "exceptions.csv", outputs.issues)
    storage.write_review_records(output_dir / "normalization_reviews.csv", outputs.reviews)
    artifacts.write_rows(
        output_dir / "wallet_inventory.csv",
        WALLET_INVENTORY_HEADER,
        (record.to_row() for record in outputs.wallet_inventory),
    )
