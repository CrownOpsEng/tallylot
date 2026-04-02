"""Shared adapter support contracts."""

from .intake import match_intake_by_path_or_header, no_intake_route
from .issues import IssueSpec, ReviewSpec, issue_record, review_record
from .locations import (
    BTC_ADDRESS_PATTERN,
    EVM_ADDRESS_PATTERN,
    SOLANA_ADDRESS_PATTERN,
    TRON_ADDRESS_PATTERN,
    LocationIssueSpec,
    LocationRecordSpec,
    canonical_location_id_from_identifier,
    is_onchain_canonical_location_id,
    location_id_from_parts,
    location_identifier_kind,
    location_issue,
    location_record,
    normalized_identifier,
)
from .precision import (
    DecimalPrecisionCheck,
    DecimalPrecisionExpectation,
    check_decimal_precision,
    decimal_fraction_digits,
)
from .rows import (
    CsvRowContext,
    collect_csv_row_results,
    group_csv_row_contexts,
    iter_csv_row_contexts,
    matching_file_paths,
    read_csv_header,
    read_csv_rows,
    skip_files_outside_profile_families,
)
from .timezones import TimezoneReviewPolicy, passed_timezone_summary, reviewed_timezone_summary
from .translation import (
    FileTranslationContext,
    FileTranslationResult,
    FileTranslationRule,
    translate_file_families,
)

__all__ = [
    "BTC_ADDRESS_PATTERN",
    "EVM_ADDRESS_PATTERN",
    "SOLANA_ADDRESS_PATTERN",
    "TRON_ADDRESS_PATTERN",
    "CsvRowContext",
    "DecimalPrecisionCheck",
    "DecimalPrecisionExpectation",
    "FileTranslationContext",
    "FileTranslationResult",
    "FileTranslationRule",
    "IssueSpec",
    "LocationIssueSpec",
    "LocationRecordSpec",
    "ReviewSpec",
    "TimezoneReviewPolicy",
    "canonical_location_id_from_identifier",
    "check_decimal_precision",
    "collect_csv_row_results",
    "decimal_fraction_digits",
    "group_csv_row_contexts",
    "is_onchain_canonical_location_id",
    "issue_record",
    "iter_csv_row_contexts",
    "location_id_from_parts",
    "location_identifier_kind",
    "location_issue",
    "location_record",
    "match_intake_by_path_or_header",
    "matching_file_paths",
    "no_intake_route",
    "normalized_identifier",
    "passed_timezone_summary",
    "read_csv_header",
    "read_csv_rows",
    "review_record",
    "reviewed_timezone_summary",
    "skip_files_outside_profile_families",
    "translate_file_families",
]
