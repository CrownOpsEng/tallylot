"""Coinbase retail translation helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re

from tallylot.adapters.support import IssueSpec, issue_record, read_csv_row_contexts
from tallylot.adapters.support.drafts import (
    EconomicActivityDraft,
    TranslationBatchDrafts,
    translation_batch_from_drafts,
)
from tallylot.domain.issues import IssueRecord
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch
from tallylot.ports.translation_inputs import (
    TranslationCoverageMode,
    TranslationCoverageWindow,
    TranslationFreshness,
    TranslationFreshnessKind,
    TranslationInputCandidate,
    TranslationInputPlan,
    TranslationSelectionMode,
    translation_input_content_fingerprint,
    translation_input_coverage_from_inventory_entry,
)

from .asset_migrations import normalize_asset_migration as _normalize_asset_migration
from .matching import RETAIL_HEADER
from .retail_rows import normalize_retail_row as _normalize_row

_SELECTION_GROUP = "coinbase:retail_export"
_FAMILY_ID = "retail_export"
_EXPORT_DATE_PREFIX_PATTERN = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})\b")


def describe_translation_inputs(
    profile: SourceProfile, raw_dir: Path
) -> tuple[TranslationInputCandidate, ...]:
    del raw_dir
    candidates: list[TranslationInputCandidate] = []
    for entry in _retail_inventory_entries(profile):
        coverage = translation_input_coverage_from_inventory_entry(entry)
        freshness = _candidate_freshness(entry)
        candidates.append(
            TranslationInputCandidate(
                candidate_id=_candidate_id(entry),
                selection_group=_SELECTION_GROUP,
                family_id=_FAMILY_ID,
                member_relative_paths=(entry.relative_path,),
                selection_mode=TranslationSelectionMode.REPLACEABLE_RANGE,
                coverage=coverage,
                freshness=freshness,
                content_fingerprint=translation_input_content_fingerprint(
                    member_sha256s=(entry.sha256,),
                    family_id=_FAMILY_ID,
                    selection_group=_SELECTION_GROUP,
                    selection_mode=TranslationSelectionMode.REPLACEABLE_RANGE,
                ),
                comparison_key=_SELECTION_GROUP,
                description=_candidate_description(entry, coverage),
                comparable=True,
            )
        )
    return tuple(candidates)


def translate_selected_inputs(
    profile: SourceProfile,
    raw_dir: Path,
    plan: TranslationInputPlan,
) -> SourceTranslationBatch:
    candidates = {
        candidate.candidate_id: candidate
        for candidate in describe_translation_inputs(profile, raw_dir)
    }
    if not plan.selected_candidate_ids:
        return _missing_retail_csv_batch(profile)
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    for candidate_id in plan.selected_candidate_ids:
        candidate = candidates.get(candidate_id)
        if candidate is None:
            raise ValueError(
                f"translation plan selected unknown Coinbase candidate: {candidate_id}"
            )
        for member_relative_path in candidate.member_relative_paths:
            path = _entry_path(raw_dir, member_relative_path)
            if path is None:
                raise ValueError(
                    f"selected Coinbase candidate member is missing from raw capture: {member_relative_path}"
                )
            selected_batch = _translate_retail_file(profile, path)
            drafts.extend(selected_batch.drafts)
            issues.extend(selected_batch.issues)
    return translation_batch_from_drafts(
        TranslationBatchDrafts(drafts=tuple(drafts), issues=tuple(issues))
    )


def translate_coinbase_exports(
    profile: SourceProfile, raw_dir: Path
) -> SourceTranslationBatch:
    candidates = describe_translation_inputs(profile, raw_dir)
    if not candidates:
        return _missing_retail_csv_batch(profile)
    if len(candidates) > 1:
        raise ValueError(
            "Coinbase retail translation requires translation input planning when "
            "more than one retail export candidate is present"
        )
    candidate = next(iter(candidates))
    return translate_selected_inputs(
        profile,
        raw_dir,
        TranslationInputPlan(
            selected_candidate_ids=(candidate.candidate_id,),
            decisions=(),
            blocked=False,
        ),
    )


def _translate_retail_file(
    profile: SourceProfile, retail_path: Path
) -> SourceTranslationBatch:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    asset_migrations: dict[str, list[dict[str, str]]] = {}
    for row_context in read_csv_row_contexts(retail_path):
        index = row_context.row_index
        row = row_context.row
        row_id = (row.get("ID") or "").strip()
        tx_type = (row.get("Transaction Type") or "").strip().lower()
        if tx_type == "asset migration":
            timestamp = (row.get("Timestamp") or "").strip()
            asset_migrations.setdefault(timestamp, []).append(row)
            continue
        try:
            drafts.append(_normalize_row(profile, retail_path.name, row))
        except ValueError as error:
            issues.append(
                issue_record(
                    IssueSpec(
                        source=str(profile.source),
                        adapter_id="coinbase",
                        issue_id=f"coinbase:{retail_path.name}:{row_id or tx_type or 'row'}",
                        kind="unsupported_row",
                        message=str(error),
                        raw_file=retail_path.name,
                        raw_row_ref=f"row:{index}",
                    )
                )
            )
    for timestamp, rows in sorted(asset_migrations.items()):
        try:
            drafts.append(
                _normalize_asset_migration(profile, retail_path.name, timestamp, rows)
            )
        except ValueError as error:
            issues.append(
                issue_record(
                    IssueSpec(
                        source=str(profile.source),
                        adapter_id="coinbase",
                        issue_id=f"coinbase:{retail_path.name}:asset_migration:{timestamp}",
                        kind="unsupported_row",
                        message=str(error),
                        raw_file=retail_path.name,
                        raw_row_ref=timestamp,
                    )
                )
            )
    return translation_batch_from_drafts(
        TranslationBatchDrafts(drafts=tuple(drafts), issues=tuple(issues))
    )


def _missing_retail_csv_batch(profile: SourceProfile) -> SourceTranslationBatch:
    return translation_batch_from_drafts(
        TranslationBatchDrafts(
            issues=(
                issue_record(
                    IssueSpec(
                        source=str(profile.source),
                        adapter_id="coinbase",
                        issue_id="coinbase:missing_retail_csv",
                        kind="missing_required_input",
                        message=(
                            "Coinbase retail all-time CSV is required for deterministic normalization."
                        ),
                        severity="high",
                    )
                ),
            ),
        )
    )


def _retail_inventory_entries(
    profile: SourceProfile,
) -> tuple[FileInventoryEntry, ...]:
    return tuple(
        entry
        for entry in sorted(profile.file_inventory, key=lambda item: item.relative_path)
        if _is_retail_export_entry(entry)
    )


def _is_retail_export_entry(entry: FileInventoryEntry) -> bool:
    if entry.suffix.lower() != ".csv" or entry.row_count in {None, 0}:
        return False
    return entry.header == RETAIL_HEADER


def _candidate_id(entry: FileInventoryEntry) -> str:
    return f"{_SELECTION_GROUP}:{entry.relative_path}"


def _candidate_freshness(entry: FileInventoryEntry) -> TranslationFreshness:
    export_timestamp = _export_timestamp_from_entry(entry)
    if export_timestamp is not None:
        return TranslationFreshness(
            kind=TranslationFreshnessKind.EXPORT_TIMESTAMP,
            timestamp=export_timestamp,
            rank=None,
        )
    rank = 2 if _is_all_time_export(entry) else 1
    return TranslationFreshness(
        kind=TranslationFreshnessKind.ADAPTER_RANK,
        timestamp=None,
        rank=rank,
    )


def _candidate_description(
    entry: FileInventoryEntry,
    coverage: TranslationCoverageWindow,
) -> str:
    if coverage.mode is TranslationCoverageMode.UNKNOWN:
        return f"Coinbase retail export file {entry.relative_path}"
    start = _coverage_text(coverage.start_at)
    end = _coverage_text(coverage.end_at)
    if start and end:
        return f"Coinbase retail export file {entry.relative_path} covering {start} to {end} UTC"
    return f"Coinbase retail export file {entry.relative_path}"


def _coverage_text(value: object) -> str:
    if not isinstance(value, datetime):
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _entry_path(raw_dir: Path, relative_path: str) -> Path | None:
    candidate = raw_dir / relative_path
    if candidate.exists():
        return candidate
    return None


def _export_timestamp_from_entry(entry: FileInventoryEntry) -> datetime | None:
    if entry.export_timestamp.strip():
        return datetime.strptime(entry.export_timestamp, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=UTC
        )
    match = _EXPORT_DATE_PREFIX_PATTERN.match(entry.relative_path)
    if match is None:
        return None
    return datetime.strptime(match.group("date"), "%Y-%m-%d").replace(tzinfo=UTC)


def _is_all_time_export(entry: FileInventoryEntry) -> bool:
    normalized_path = entry.relative_path.lower()
    return "all time" in normalized_path or "all-time" in normalized_path
