"""Shared adapter support contracts."""

from .intake import match_intake_by_path_or_header, no_intake_route
from .issues import IssueSpec, ReviewSpec, issue_record, review_record
from .rows import (
    CsvRowContext,
    collect_csv_row_results,
    group_csv_row_contexts,
    iter_csv_row_contexts,
    matching_file_paths,
    read_csv_header,
    read_csv_rows,
)
from .timezones import TimezoneReviewPolicy, passed_timezone_summary, reviewed_timezone_summary
from .translation import FileTranslationContext, FileTranslationResult, FileTranslationRule, translate_file_families
from .wallets import (
    BTC_ADDRESS_PATTERN,
    EVM_ADDRESS_PATTERN,
    SOLANA_ADDRESS_PATTERN,
    TRON_ADDRESS_PATTERN,
    WalletIssueSpec,
    WalletRecordSpec,
    normalized_identifier,
    wallet_identifier_kind,
    wallet_issue,
    wallet_record,
)

__all__ = [
    "BTC_ADDRESS_PATTERN",
    "EVM_ADDRESS_PATTERN",
    "SOLANA_ADDRESS_PATTERN",
    "TRON_ADDRESS_PATTERN",
    "CsvRowContext",
    "FileTranslationContext",
    "FileTranslationResult",
    "FileTranslationRule",
    "IssueSpec",
    "ReviewSpec",
    "TimezoneReviewPolicy",
    "WalletIssueSpec",
    "WalletRecordSpec",
    "collect_csv_row_results",
    "group_csv_row_contexts",
    "issue_record",
    "iter_csv_row_contexts",
    "match_intake_by_path_or_header",
    "matching_file_paths",
    "no_intake_route",
    "normalized_identifier",
    "passed_timezone_summary",
    "read_csv_header",
    "read_csv_rows",
    "review_record",
    "reviewed_timezone_summary",
    "translate_file_families",
    "wallet_identifier_kind",
    "wallet_issue",
    "wallet_record",
]
