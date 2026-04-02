from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.application.normalization import (
    filter_drafts_by_window,
    filter_issues_by_window,
    filter_reviews_by_window,
)
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    AccountingIntentHint,
    EconomicKind,
    LegKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.types import LocationId
from tallylot.ports.source_translation import EconomicActivityDraft, classification, economic_leg


def test_filter_drafts_by_window_excludes_rows_before_start() -> None:
    early = _draft("txn-1", "2023-08-05 08:34:04")
    in_window = _draft("txn-2", "2023-08-05 08:34:05")

    filtered, excluded_count = filter_drafts_by_window(
        (early, in_window),
        window_start="2023-08-05 08:34:05",
        window_end=None,
    )

    assert filtered == (in_window,)
    assert excluded_count == 1


def test_filter_issues_by_window_excludes_timestamped_issues_before_start() -> None:
    filtered, excluded_count = filter_issues_by_window(
        (
            IssueRecord(
                issue_id="before",
                source="Binance",
                adapter_id="binance",
                severity="medium",
                kind="unsupported_group",
                message="before",
                context_timestamp="2023-08-05 08:34:04",
            ),
            IssueRecord(
                issue_id="inside",
                source="Binance",
                adapter_id="binance",
                severity="medium",
                kind="unsupported_group",
                message="inside",
                context_timestamp="2023-08-05 08:34:05",
            ),
            IssueRecord(
                issue_id="untimed",
                source="Binance",
                adapter_id="binance",
                severity="medium",
                kind="unsupported_group",
                message="untimed",
            ),
        ),
        window_start="2023-08-05 08:34:05",
        window_end=None,
    )

    assert excluded_count == 1
    assert [issue.issue_id for issue in filtered] == ["inside", "untimed"]


def test_filter_issues_by_window_excludes_untimed_activity_scoped_issues() -> None:
    filtered, excluded_count = filter_issues_by_window(
        (
            IssueRecord(
                issue_id="dataset",
                source="Binance",
                adapter_id="binance",
                severity="medium",
                kind="unsupported_group",
                message="dataset",
            ),
            IssueRecord(
                issue_id="row",
                source="Binance",
                adapter_id="binance",
                severity="medium",
                kind="unsupported_group",
                message="row",
                raw_file="transactions.csv",
                raw_row_ref="2",
            ),
        ),
        window_start="2023-08-05 08:34:05",
        window_end=None,
    )

    assert excluded_count == 1
    assert [issue.issue_id for issue in filtered] == ["dataset"]


def test_filter_reviews_by_window_keeps_dataset_reviews_and_filters_row_reviews() -> None:
    filtered, excluded_count = filter_reviews_by_window(
        (
            NormalizationReviewRecord(
                review_id="dataset",
                source="fixture",
                adapter_id="structured_csv",
                scope="dataset",
                kind="timezone_timezone_assumed_utc",
                message="dataset review",
            ),
            NormalizationReviewRecord(
                review_id="before",
                source="fixture",
                adapter_id="structured_csv",
                scope="row",
                kind="outbound_amount_sign_normalized",
                message="before",
                context_timestamp="2023-08-05 08:34:04",
                raw_file="transactions.csv",
                raw_row_ref="2",
            ),
            NormalizationReviewRecord(
                review_id="inside",
                source="fixture",
                adapter_id="structured_csv",
                scope="row",
                kind="outbound_amount_sign_normalized",
                message="inside",
                context_timestamp="2023-08-05 08:34:05",
                raw_file="transactions.csv",
                raw_row_ref="3",
            ),
        ),
        window_start="2023-08-05 08:34:05",
        window_end=None,
    )

    assert excluded_count == 1
    assert [review.review_id for review in filtered] == ["dataset", "inside"]


def test_filter_reviews_by_window_excludes_untimed_non_dataset_reviews() -> None:
    filtered, excluded_count = filter_reviews_by_window(
        (
            NormalizationReviewRecord(
                review_id="dataset",
                source="fixture",
                adapter_id="structured_csv",
                scope="dataset",
                kind="timezone_timezone_assumed_utc",
                message="dataset review",
            ),
            NormalizationReviewRecord(
                review_id="row",
                source="fixture",
                adapter_id="structured_csv",
                scope="row",
                kind="outbound_amount_sign_normalized",
                message="row review",
                raw_file="transactions.csv",
                raw_row_ref="2",
            ),
        ),
        window_start="2023-08-05 08:34:05",
        window_end=None,
    )

    assert excluded_count == 1
    assert [review.review_id for review in filtered] == ["dataset"]


def _draft(transaction_id: str, timestamp: str) -> EconomicActivityDraft:
    return EconomicActivityDraft(
        activity_id=transaction_id,
        source="fixture-source",
        adapter_id="fixture-adapter",
        timestamp=datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC),
        location_id=LocationId("fixture-account:fixture-wallet"),
        classification=classification(
            economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
            accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
            tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
            projection_hint=ProjectionHint.DEPOSIT,
        ),
        legs=(economic_leg(leg_id="primary_btc", kind=LegKind.PRIMARY, instrument="BTC", quantity=Decimal("1")),),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
    )
