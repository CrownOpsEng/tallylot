from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeGuard

import yaml

from repo_support.paths import repo_root

from .catalog import (
    BannedAlias,
    PathException,
    TargetNamingCatalog,
    iter_target_naming_paths,
    load_target_naming_catalog,
)

FRONTMATTER_PATTERN = re.compile(r"\A---\n(.*?)\n---(?:\n|\Z)", re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")
PASCAL_TOKEN_PATTERN = re.compile(
    r"\b[A-Z][A-Za-z0-9]+(?:"
    r"Set|Facts|State|Record|Ref|Id|Value|Status|Purpose|Facet|"
    r"Assertion|Event|Leg|Pool|Inputs|Outputs"
    r")\b"
)
SNAKE_IDENTIFIER_PATTERN = re.compile(
    r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)*(?:_id|_ref|_refs|_slug)\b"
)
SUPPORT_PATH_PATTERN = re.compile(r"\bsupport/([a-z0-9_.-]+(?:/[a-z0-9_.-]+)*)\b")
VOCABULARY_BLOCK_PATTERN = re.compile(
    r"^- `(?P<label>[^`]+)`:\n(?P<body>(?:  - `[^`]+`\n)+)",
    re.MULTILINE,
)
HEADING_VOCABULARY_PATTERN = re.compile(
    r"^### `(?P<heading>[^`]+)`\n\nShared vocabulary:\n\n(?P<body>(?:- `[^`]+`\n)+)",
    re.MULTILINE,
)
BODY_VALUE_PATTERN = re.compile(r"- `([^`]+)`")
CANONICAL_PATH_PREFIXES = (
    "application/",
    "domain/",
    "working/",
    "support/",
    "compatibility/",
)


@dataclass(frozen=True)
class NamingFinding:
    path: str
    finding_class: str
    offending: str
    replacement: str | None
    detail: str
    exception_rule: str | None = None


def audit_target_naming(
    catalog: TargetNamingCatalog | None = None,
) -> tuple[NamingFinding, ...]:
    loaded = catalog or load_target_naming_catalog()
    root = repo_root()
    findings: list[NamingFinding] = []
    for path in iter_target_naming_paths(loaded):
        relative_path = path.relative_to(root).as_posix()
        findings.extend(
            _analyze_file(relative_path, path.read_text(encoding="utf-8"), loaded)
        )
    return tuple(findings)


def _analyze_file(
    relative_path: str,
    text: str,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    summary_text = _frontmatter_summary(text)
    if summary_text is not None:
        findings.extend(
            _banned_alias_findings(
                relative_path,
                summary_text,
                catalog.aliases,
                summary_only=True,
            )
        )
    findings.extend(
        _banned_alias_findings(
            relative_path,
            text,
            catalog.aliases,
            summary_only=False,
        )
    )
    findings.extend(
        _unauthorized_exception_findings(relative_path, text, catalog.exceptions)
    )
    findings.extend(
        _unknown_identifier_findings(
            relative_path,
            text,
            catalog.canonical_tokens,
            catalog.exceptions,
        )
    )
    findings.extend(_flat_support_path_findings(relative_path, text))
    findings.extend(_record_family_findings(relative_path, text, catalog))
    findings.extend(_vocabulary_block_findings(relative_path, text, catalog))
    return tuple(findings)


def _frontmatter_summary(text: str) -> str | None:
    match = FRONTMATTER_PATTERN.match(text)
    if match is None:
        return None
    loaded: object = yaml.safe_load(match.group(1))
    if not _is_object_mapping(loaded):
        return None
    summary = _normalize_mapping(loaded).get("summary")
    return summary if isinstance(summary, str) else None


def _banned_alias_findings(
    path: str,
    text: str,
    aliases: tuple[BannedAlias, ...],
    *,
    summary_only: bool,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    for alias in aliases:
        if not alias.applies_to(path, summary_only=summary_only):
            continue
        if alias.term not in text:
            continue
        findings.append(
            NamingFinding(
                path=path,
                finding_class=alias.finding_class,
                offending=alias.term,
                replacement=alias.replacement,
                detail=f"replace {alias.term!r} with {alias.replacement!r}",
            )
        )
    return tuple(findings)


def _unauthorized_exception_findings(
    path: str,
    text: str,
    exceptions: tuple[PathException, ...],
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    exception_terms = {
        term for exception in exceptions for term in exception.allowed_terms
    }
    for term in sorted(exception_terms):
        if term not in text:
            continue
        if _matching_exception(path, term, exceptions) is not None:
            continue
        findings.append(
            NamingFinding(
                path=path,
                finding_class="unauthorized-exception-term",
                offending=term,
                replacement=None,
                detail=(
                    "move the term to an allowed locality or replace it with "
                    "a canonical target name"
                ),
            )
        )
    return tuple(findings)


def _matching_exception(
    path: str,
    term: str,
    exceptions: tuple[PathException, ...],
) -> PathException | None:
    for exception in exceptions:
        if exception.applies_to(path, term):
            return exception
    return None


def _unknown_identifier_findings(
    path: str,
    text: str,
    canonical_tokens: frozenset[str],
    exceptions: tuple[PathException, ...],
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    seen: set[str] = set()
    for token in _inline_identifier_tokens(text):
        if token in seen:
            continue
        seen.add(token)
        if token in canonical_tokens:
            continue
        if _matching_exception(path, token, exceptions) is not None:
            continue
        findings.append(
            NamingFinding(
                path=path,
                finding_class="unknown-target-identifier",
                offending=token,
                replacement=(
                    "add the canonical term to "
                    "tools/target_naming_catalog.yaml or replace it with "
                    "an existing canonical name"
                ),
                detail="target-like identifier is not declared in the naming catalog",
            )
        )
    return tuple(findings)


def _inline_identifier_tokens(text: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for match in INLINE_CODE_PATTERN.finditer(text):
        content = match.group(1)
        if re.fullmatch(r"(?:[a-z0-9_.-]+/)+[a-z0-9_.-]+/?", content):
            if content.startswith(CANONICAL_PATH_PREFIXES):
                tokens.append(content)
            continue
        tokens.extend(PASCAL_TOKEN_PATTERN.findall(content))
        tokens.extend(SNAKE_IDENTIFIER_PATTERN.findall(content))
    tokens.extend(PASCAL_TOKEN_PATTERN.findall(text))
    return tuple(dict.fromkeys(tokens))


def _flat_support_path_findings(path: str, text: str) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    for match in SUPPORT_PATH_PATTERN.finditer(text):
        full_path = match.group(0)
        remainder = match.group(1)
        if remainder.split("/")[0] in {"gap", "review", "readiness"}:
            continue
        findings.append(
            NamingFinding(
                path=path,
                finding_class="flat-support-path",
                offending=full_path,
                replacement=(
                    "use support/gap/, support/review/, or support/readiness/ "
                    "with a family-mirrored basename"
                ),
                detail="shared support paths must stay nested by family",
            )
        )
    return tuple(findings)


def _is_object_mapping(value: object) -> TypeGuard[Mapping[object, object]]:
    return isinstance(value, Mapping)


def _normalize_mapping(value: Mapping[object, object]) -> Mapping[str, object]:
    normalized: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError("frontmatter keys must be strings")
        normalized[key] = item
    return normalized


def _record_family_findings(
    path: str,
    text: str,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    for family in catalog.records:
        if path not in family.required_in:
            continue
        present_tokens = [token for token in family.required_tokens if token in text]
        if not present_tokens:
            continue
        missing_tokens = [
            token for token in family.required_tokens if token not in text
        ]
        if not missing_tokens:
            continue
        findings.append(
            NamingFinding(
                path=path,
                finding_class="record-family-mismatch",
                offending=family.record,
                replacement=", ".join(family.required_tokens),
                detail=(
                    f"{family.stem} family must keep "
                    f"{', '.join(family.required_tokens)} together in owner docs"
                ),
            )
        )
    return tuple(findings)


def _vocabulary_block_findings(
    path: str,
    text: str,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    nested_blocks: dict[str, list[tuple[str, ...]]] = {}
    for match in VOCABULARY_BLOCK_PATTERN.finditer(text):
        nested_blocks.setdefault(match.group("label"), []).append(
            tuple(BODY_VALUE_PATTERN.findall(match.group("body")))
        )
    heading_blocks: dict[str, list[tuple[str, ...]]] = {}
    for match in HEADING_VOCABULARY_PATTERN.finditer(text):
        heading_blocks.setdefault(match.group("heading"), []).append(
            tuple(BODY_VALUE_PATTERN.findall(match.group("body")))
        )
    for check in catalog.vocabularies.checks:
        if check.path != path:
            continue
        actual_blocks = (
            nested_blocks.get(check.label)
            if check.block_type == "nested_list"
            else heading_blocks.get(check.label)
        )
        if actual_blocks is None:
            findings.append(
                NamingFinding(
                    path=path,
                    finding_class="missing-vocabulary-block",
                    offending=check.label,
                    replacement=check.vocabulary,
                    detail="expected vocabulary block is missing from the enforced surface",
                )
            )
            continue
        expected_values = (
            check.expected_values
            if check.expected_values
            else catalog.vocabularies.values[check.vocabulary]
        )
        if expected_values in actual_blocks:
            continue
        findings.append(
            NamingFinding(
                path=path,
                finding_class="vocabulary-drift",
                offending=check.label,
                replacement=", ".join(expected_values),
                detail=(
                    f"expected {check.vocabulary} values {expected_values}, "
                    f"found {tuple(actual_blocks)}"
                ),
            )
        )
    return tuple(findings)


__all__ = ["NamingFinding", "audit_target_naming"]
