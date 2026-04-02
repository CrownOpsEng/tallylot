"""Filesystem storage implementation."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.domain.models import (
    BalanceEvidence,
    BalanceSnapshot,
    IssueRecord,
    NormalizationReviewRecord,
)
from crypto_reconciliation.domain.models.transactions import NormalizedTransaction
from crypto_reconciliation.infrastructure.serialization.csv_io import write_rows


class FilesystemStorage:
    def write_transactions(self, path: Path, transactions: tuple[NormalizedTransaction, ...]) -> None:
        write_rows(
            path,
            (
                "transaction_id",
                "source",
                "adapter_id",
                "account",
                "wallet",
                "timestamp",
                "category",
                "economic_kind",
                "projection_type",
                "journal_intent",
                "tax_treatment_code",
                "provider_operation_key",
                "operation_group_id",
                "description",
                "asset_in",
                "amount_in",
                "asset_out",
                "amount_out",
                "fee_asset",
                "fee_amount",
                "tx_hash",
                "raw_file",
                "raw_row_ref",
                "confidence",
                "status",
            ),
            (transaction.to_row() for transaction in transactions),
        )

    def write_balances(self, path: Path, balances: tuple[BalanceSnapshot, ...]) -> None:
        write_rows(
            path,
            ("source", "account", "wallet", "asset", "quantity", "as_of", "balance_kind", "notes"),
            (balance.to_row() for balance in balances),
        )

    def write_balance_evidence(self, path: Path, evidence: tuple[BalanceEvidence, ...]) -> None:
        write_rows(
            path,
            ("source", "account", "wallet", "asset", "quantity", "as_of", "balance_kind", "evidence_ref", "notes"),
            (record.to_row() for record in evidence),
        )

    def write_issue_records(self, path: Path, issues: tuple[IssueRecord, ...]) -> None:
        write_rows(
            path,
            (
                "issue_id",
                "source",
                "adapter_id",
                "severity",
                "kind",
                "message",
                "context_timestamp",
                "raw_file",
                "raw_row_ref",
                "status",
            ),
            (issue.to_row() for issue in issues),
        )

    def write_review_records(
        self,
        path: Path,
        reviews: tuple[NormalizationReviewRecord, ...],
    ) -> None:
        write_rows(
            path,
            (
                "review_id",
                "source",
                "adapter_id",
                "scope",
                "kind",
                "message",
                "raw_file",
                "raw_row_ref",
                "field_name",
                "original_value",
                "normalized_value",
                "status",
            ),
            (review.to_row() for review in reviews),
        )
