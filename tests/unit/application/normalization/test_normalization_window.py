from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.application.normalization import (
    filter_facts_by_window,
    filter_issues_by_window,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import (
    EconomicKind,
    EconomicLeg,
    FactClassification,
    JournalIntent,
    ProjectionType,
    TaxTreatmentCode,
    TransactionFact,
)
from tallylot.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId


def test_filter_facts_by_window_returns_original_events_without_bounds() -> None:
    event = _transaction("txn-1", "2023-08-05 08:34:04")

    filtered, excluded_count = filter_facts_by_window((event,), window_start=None, window_end=None)

    assert filtered == (event,)
    assert excluded_count == 0


def test_filter_facts_by_window_excludes_rows_before_start() -> None:
    early = _transaction("txn-1", "2023-08-05 08:34:04")
    in_window = _transaction("txn-2", "2023-08-05 08:34:05")

    filtered, excluded_count = filter_facts_by_window(
        (early, in_window),
        window_start="2023-08-05 08:34:05",
        window_end=None,
    )

    assert filtered == (in_window,)
    assert excluded_count == 1


def test_filter_facts_by_window_excludes_rows_after_end() -> None:
    in_window = _transaction("txn-1", "2023-08-05 08:34:04")
    late = _transaction("txn-2", "2023-08-05 08:34:06")

    filtered, excluded_count = filter_facts_by_window(
        (in_window, late),
        window_start=None,
        window_end="2023-08-05 08:34:05",
    )

    assert filtered == (in_window,)
    assert excluded_count == 1


def test_filter_facts_by_window_keeps_only_events_inside_both_bounds() -> None:
    early = _transaction("txn-1", "2023-08-05 08:34:03")
    in_window = _transaction("txn-2", "2023-08-05 08:34:04")
    late = _transaction("txn-3", "2023-08-05 08:34:06")

    filtered, excluded_count = filter_facts_by_window(
        (early, in_window, late),
        window_start="2023-08-05 08:34:04",
        window_end="2023-08-05 08:34:05",
    )

    assert filtered == (in_window,)
    assert excluded_count == 2


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


def _transaction(transaction_id: str, timestamp: str) -> TransactionFact:
    return TransactionFact(
        fact_id=TransactionId(transaction_id),
        source=SourceId("fixture-source"),
        adapter_id=AdapterId("fixture-adapter"),
        timestamp=datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC),
        account="fixture-account",
        wallet="fixture-wallet",
        classification=FactClassification(
            economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
            journal_intent=JournalIntent.FUNDING_INFLOW,
            tax_treatment_code=TaxTreatmentCode.NON_TAXABLE_TRANSFER_IN,
            projection_type=ProjectionType.DEPOSIT,
        ),
        legs=(EconomicLeg(direction="in", asset=AssetSymbol("BTC"), amount=Decimal("1")),),
    )
