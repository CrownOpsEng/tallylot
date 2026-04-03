"""Filesystem storage implementation."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.domain.models import (
    CanonicalBalance,
    CanonicalEvent,
    IssueRecord,
    NormalizationReviewRecord,
)
from crypto_reconciliation.infrastructure.serialization.csv_io import write_rows


class FilesystemStorage:
    def write_canonical_events(self, path: Path, events: tuple[CanonicalEvent, ...]) -> None:
        write_rows(
            path,
            (
                "event_id",
                "source",
                "adapter_id",
                "account",
                "wallet",
                "timestamp",
                "event_kind",
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
                "render_type",
                "render_exchange",
                "render_group",
                "render_comment",
                "render_comment_mode",
                "render_tx_id",
                "render_tx_id_mode",
                "render_allowed_types",
                "render_match_window_seconds",
                "render_fee_tolerance",
                "render_notes",
            ),
            (event.to_row() for event in events),
        )

    def write_canonical_balances(self, path: Path, balances: tuple[CanonicalBalance, ...]) -> None:
        write_rows(
            path,
            ("source", "account", "wallet", "asset", "quantity", "as_of", "balance_kind", "notes"),
            (balance.to_row() for balance in balances),
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
