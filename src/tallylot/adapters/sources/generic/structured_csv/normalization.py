"""Structured CSV normalization workflow."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from tallylot.adapters.support import (
    CsvRowContext,
    location_id_from_parts,
    read_csv_header,
    read_csv_row_contexts,
)
from tallylot.adapters.support.drafts import (
    EconomicActivityDraft,
    translation_batch_from_drafts,
)
from tallylot.adapters.support.issues import IssueSpec, issue_record
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.locations import LocationKind
from tallylot.domain.types import LocationId
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch

from tallylot.application.evidence.location_inventory import (
    LocationInventoryBuildSpec,
    build_location_inventory_record,
)
from tallylot.ports.evidence import LocationInventoryRecord

from .contracts import REQUIRED_HEADER, TRANSACTIONS_FILENAME
from .feedback import StructuredCsvFeedbackFactory
from .translation import translate_row
from .validation import StructuredCsvRowValidator


def translate_structured_csv(
    profile: SourceProfile,
    raw_dir: Path,
    *,
    adapter_id: str,
) -> SourceTranslationBatch:
    path = raw_dir / TRANSACTIONS_FILENAME
    feedback = StructuredCsvFeedbackFactory(profile=profile, adapter_id=adapter_id)
    validator = StructuredCsvRowValidator(feedback=feedback)
    if read_csv_header(path) != REQUIRED_HEADER:
        return translation_batch_from_drafts(
            issues=(
                issue_record(
                    IssueSpec(
                        issue_id=f"{profile.source}:schema",
                        source=str(profile.source),
                        adapter_id=adapter_id,
                        severity="high",
                        kind="invalid_schema",
                        message="transactions.csv does not match the structured CSV schema.",
                        raw_file=TRANSACTIONS_FILENAME,
                    )
                ),
            ),
        )
    return _normalized_result(
        profile,
        read_csv_row_contexts(path),
        feedback,
        validator,
    )


def _normalized_result(
    profile: SourceProfile,
    row_contexts: tuple[CsvRowContext, ...],
    feedback: StructuredCsvFeedbackFactory,
    validator: StructuredCsvRowValidator,
) -> SourceTranslationBatch:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    reviews: list[NormalizationReviewRecord] = []
    location_rows: dict[str, LocationInventoryRecord] = {}
    for row_context in row_contexts:
        index = row_context.row_index
        row = row_context.row
        row_issue = validator.validate_row(
            cast(dict[str, str | None], row),
            index,
        )
        if row_issue is not None:
            issues.append(row_issue)
            continue
        draft, row_reviews = _normalize_valid_row(
            profile,
            row,
            index,
            validator=validator,
        )
        drafts.append(draft)
        reviews.extend(row_reviews)
        location_rows[
            _location_id(profile, row["account"].strip(), row["wallet"].strip())
        ] = _location_record(
            profile,
            row["account"].strip(),
            row["wallet"].strip(),
        )
    reviews.extend(_dataset_reviews(feedback, has_transactions=bool(drafts)))
    return translation_batch_from_drafts(
        drafts,
        issues=_issues_with_no_valid_rows(
            profile,
            feedback.adapter_id,
            issues,
            has_transactions=bool(drafts),
        ),
        reviews=reviews,
        location_inventory=tuple(location_rows.values()),
    )


def _normalize_valid_row(
    profile: SourceProfile,
    row: dict[str, str],
    index: int,
    *,
    validator: StructuredCsvRowValidator,
) -> tuple[EconomicActivityDraft, tuple[NormalizationReviewRecord, ...]]:
    return translate_row(profile, row, index, validator=validator)


def _location_id(profile: SourceProfile, account: str, wallet: str) -> LocationId:
    return location_id_from_parts(str(profile.source), account, wallet)


def _location_record(
    profile: SourceProfile,
    account: str,
    wallet: str,
) -> LocationInventoryRecord:
    location_id = _location_id(profile, account, wallet)
    parent_location_id = (
        None
        if account == wallet
        else location_id_from_parts(str(profile.source), account)
    )
    return build_location_inventory_record(
        LocationInventoryBuildSpec(
            source=str(profile.source),
            location_id=location_id,
            location_kind=LocationKind.SUBACCOUNT
            if account != wallet
            else LocationKind.ACCOUNT,
            location_label=wallet,
            identifier_kind="account_wallet",
            identifier_value=f"{account}:{wallet}",
            parent_location_id=parent_location_id,
            location_path=(account, wallet) if account != wallet else (wallet,),
            network_scope="",
            controller=account,
            parent_location_label="" if parent_location_id is None else account,
            evidence_kind="normalized_transactions",
            confidence="high",
            evidence_provenance=ProvenanceLocator.from_reference_ref(
                TRANSACTIONS_FILENAME
            ),
        )
    )


def _dataset_reviews(
    feedback: StructuredCsvFeedbackFactory,
    *,
    has_transactions: bool,
) -> tuple[NormalizationReviewRecord, ...]:
    if not has_transactions:
        return ()
    return (
        feedback.dataset_review(
            "timestamp_timezone_assumed_utc",
            (
                "Structured CSV timestamps are timezone-naive; normalization assigns UTC "
                "and those timestamps should be validated against the source system."
            ),
        ),
    )


def _issues_with_no_valid_rows(
    profile: SourceProfile,
    adapter_id: str,
    issues: list[IssueRecord],
    *,
    has_transactions: bool,
) -> list[IssueRecord]:
    if has_transactions:
        return issues
    return [
        *issues,
        issue_record(
            IssueSpec(
                issue_id=f"{profile.source}:no_valid_rows",
                source=str(profile.source),
                adapter_id=adapter_id,
                severity="high",
                kind="no_valid_rows",
                message="No valid rows were available for normalization.",
                raw_file=TRANSACTIONS_FILENAME,
            )
        ),
    ]
