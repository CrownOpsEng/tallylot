from __future__ import annotations

from pathlib import Path

from tallylot.application.normalization.issue_context import (
    enrich_issue_context_timestamps,
    enrich_review_context_timestamps,
)
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.ports.source_profiles import FileInventoryEntry


def test_enrich_issue_context_timestamps_uses_profiled_row_reference(tmp_path: Path) -> None:
    path = tmp_path / "activity.csv"
    path.write_text(
        "transaction_date,activity_type,activity_sub_type\n2023-09-22,staking,REWARD\n",
        encoding="utf-8",
    )
    issues = (
        IssueRecord(
            issue_id="wealthsimple:activity.csv:row:2",
            source="Future Broker",
            adapter_id="wealthsimple",
            severity="medium",
            kind="unsupported_row",
            message="Unsupported Wealthsimple crypto activity: staking/REWARD",
            raw_file="activity.csv",
            raw_row_ref="row:2",
        ),
    )
    inventory = (
        FileInventoryEntry(
            relative_path="activity.csv",
            suffix=".csv",
            size_bytes=path.stat().st_size,
            sha256="fixture",
            source_path=str(path),
            date_field="transaction_date",
            timezone_mode="date_only",
        ),
    )

    enriched = enrich_issue_context_timestamps(issues, raw_dir=tmp_path, inventory=inventory)

    assert enriched[0].context_timestamp == "2023-09-22 00:00:00"


def test_enrich_issue_context_timestamps_parses_grouped_timestamp_references(tmp_path: Path) -> None:
    path = tmp_path / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv"
    path.write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,23-03-23 04:00:00,Funding,Transfer Between Main and Funding Wallet,USDT,-10,\n",
        encoding="utf-8",
    )
    issues = (
        IssueRecord(
            issue_id="binance:group",
            source="Binance",
            adapter_id="binance",
            severity="medium",
            kind="unsupported_group",
            message="Unsupported Binance transaction-history operations: Transfer Between Main and Funding Wallet",
            raw_file=path.name,
            raw_row_ref="group:23-03-23 04:00:00:Funding",
        ),
    )
    inventory = (
        FileInventoryEntry(
            relative_path=path.name,
            suffix=".csv",
            size_bytes=path.stat().st_size,
            sha256="fixture",
            source_path=str(path),
            date_field="Time",
            timezone_mode="filename_offset",
            timezone_value="UTC-06:00",
        ),
    )

    enriched = enrich_issue_context_timestamps(issues, raw_dir=tmp_path, inventory=inventory)

    assert enriched[0].context_timestamp == "2023-03-23 04:00:00"


def test_enrich_review_context_timestamps_uses_profiled_row_reference(tmp_path: Path) -> None:
    path = tmp_path / "activity.csv"
    path.write_text(
        "transaction_date,activity_type,activity_sub_type\n2023-09-22,staking,REWARD\n",
        encoding="utf-8",
    )
    reviews = (
        NormalizationReviewRecord(
            review_id="structured_csv:activity.csv:row:2",
            source="Future Broker",
            adapter_id="structured_csv",
            scope="row",
            kind="outbound_amount_sign_normalized",
            message="amount_out was normalized",
            raw_file="activity.csv",
            raw_row_ref="row:2",
            field_name="amount_out",
        ),
    )
    inventory = (
        FileInventoryEntry(
            relative_path="activity.csv",
            suffix=".csv",
            size_bytes=path.stat().st_size,
            sha256="fixture",
            source_path=str(path),
            date_field="transaction_date",
            timezone_mode="date_only",
        ),
    )

    enriched = enrich_review_context_timestamps(reviews, raw_dir=tmp_path, inventory=inventory)

    assert enriched[0].context_timestamp == "2023-09-22 00:00:00"


def test_enrich_review_context_timestamps_parses_grouped_timestamp_references(tmp_path: Path) -> None:
    path = tmp_path / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv"
    path.write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,23-03-23 04:00:00,Funding,Transfer Between Main and Funding Wallet,USDT,-10,\n",
        encoding="utf-8",
    )
    reviews = (
        NormalizationReviewRecord(
            review_id="binance:group",
            source="Binance",
            adapter_id="binance",
            scope="row",
            kind="outbound_amount_sign_normalized",
            message="normalized sign",
            raw_file=path.name,
            raw_row_ref="group:23-03-23 04:00:00:Funding",
            field_name="change",
        ),
    )
    inventory = (
        FileInventoryEntry(
            relative_path=path.name,
            suffix=".csv",
            size_bytes=path.stat().st_size,
            sha256="fixture",
            source_path=str(path),
            date_field="Time",
            timezone_mode="filename_offset",
            timezone_value="UTC-06:00",
        ),
    )

    enriched = enrich_review_context_timestamps(reviews, raw_dir=tmp_path, inventory=inventory)

    assert enriched[0].context_timestamp == "2023-03-23 04:00:00"
