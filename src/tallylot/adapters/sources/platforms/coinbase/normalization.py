"""Coinbase retail normalization orchestration."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.support import IssueSpec, issue_record, read_csv_row_contexts
from tallylot.adapters.support.drafts import (
    EconomicActivityDraft,
    TranslationBatchDrafts,
    translation_batch_from_drafts,
)
from tallylot.domain.issues import IssueRecord
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch

from .asset_migrations import normalize_asset_migration as _normalize_asset_migration
from .matching import retail_path as _retail_path
from .retail_rows import normalize_retail_row as _normalize_row


def translate_coinbase_exports(
    profile: SourceProfile, raw_dir: Path
) -> SourceTranslationBatch:
    retail_path = _retail_path(raw_dir)
    if retail_path is None:
        return translation_batch_from_drafts(
            TranslationBatchDrafts(
                issues=(
                    issue_record(
                        IssueSpec(
                            source=str(profile.source),
                            adapter_id="coinbase",
                            issue_id="coinbase:missing_retail_csv",
                            kind="missing_required_input",
                            message="Coinbase retail all-time CSV is required for deterministic normalization.",
                            severity="high",
                        )
                    ),
                ),
            )
        )

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
