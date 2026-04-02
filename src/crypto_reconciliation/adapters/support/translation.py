"""Shared source-file translation workflow for provider adapters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from crypto_reconciliation.domain.models import IssueRecord, SourceProfile

from .drafts import EconomicActivityDraft
from .issues import IssueSpec, issue_record
from .rows import matching_file_paths

type FileTranslator = Callable[
    ["FileTranslationContext"],
    tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]],
]
type RuleMatcher = Callable[[Path], bool]


@dataclass
class FileTranslationContext:
    profile: SourceProfile
    path: Path
    family: str
    state: dict[str, object]


@dataclass(frozen=True)
class FileTranslationRule:
    family: str
    matches_path: RuleMatcher
    translate: FileTranslator
    priority: int = 100


@dataclass(frozen=True)
class FileTranslationResult:
    drafts: tuple[EconomicActivityDraft, ...] = ()
    issues: tuple[IssueRecord, ...] = ()
    unmatched_paths: tuple[str, ...] = ()


def translate_file_families(
    raw_dir: Path,
    *,
    profile: SourceProfile,
    rules: tuple[FileTranslationRule, ...],
    pattern: str = "*.csv",
    state: dict[str, object] | None = None,
) -> FileTranslationResult:
    translation_state = state if state is not None else {}
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    unmatched_paths: list[str] = []
    matched_files: list[tuple[int, str, Path, FileTranslationRule]] = []
    adapter_id = str(profile.adapter_id)
    source = str(profile.source)
    for path in matching_file_paths(raw_dir, pattern=pattern):
        matching_rules: list[FileTranslationRule] = [candidate for candidate in rules if candidate.matches_path(path)]
        if not matching_rules:
            unmatched_paths.append(path.name)
            issues.append(
                issue_record(
                    IssueSpec(
                        issue_id=f"{adapter_id}:{path.name}:unmatched_file",
                        source=source,
                        adapter_id=adapter_id,
                        kind="unsupported_file",
                        message=f"No translation rule registered for source file: {path.name}",
                        raw_file=path.name,
                    )
                )
            )
            continue
        if len(matching_rules) > 1:
            issues.append(
                issue_record(
                    IssueSpec(
                        issue_id=f"{adapter_id}:{path.name}:ambiguous_file_match",
                        source=source,
                        adapter_id=adapter_id,
                        kind="ambiguous_file_match",
                        message=(
                            "Multiple translation rules matched source file "
                            f"{path.name}: {', '.join(rule.family for rule in matching_rules)}"
                        ),
                        raw_file=path.name,
                        status="needs_review",
                    )
                )
            )
            continue
        matching_rule = matching_rules[0]
        matched_files.append((matching_rule.priority, path.as_posix(), path, matching_rule))
    for _, _, path, rule in sorted(matched_files):
        try:
            translated_drafts, translated_issues = rule.translate(
                FileTranslationContext(
                    profile=profile,
                    path=path,
                    family=rule.family,
                    state=translation_state,
                )
            )
        except ValueError as error:
            issues.append(
                issue_record(
                    IssueSpec(
                        issue_id=f"{adapter_id}:{path.name}:translation_error",
                        source=source,
                        adapter_id=adapter_id,
                        kind="translation_error",
                        message=f"{rule.family} translation failed for {path.name}: {error}",
                        raw_file=path.name,
                        status="needs_review",
                    )
                )
            )
            continue
        drafts.extend(translated_drafts)
        issues.extend(translated_issues)
    return FileTranslationResult(
        drafts=tuple(drafts),
        issues=tuple(issues),
        unmatched_paths=tuple(unmatched_paths),
    )
