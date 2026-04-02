from __future__ import annotations

import re

ALLOWED_TYPES = (
    "feat",
    "fix",
    "refactor",
    "docs",
    "test",
    "chore",
    "build",
    "ci",
    "perf",
    "revert",
)
TYPE_PATTERN = "|".join(ALLOWED_TYPES)
SCOPE_PATTERN = r"[a-z0-9]+(?:-[a-z0-9]+)*"
SUBJECT_PATTERN = re.compile(rf"^(?:{TYPE_PATTERN})(?:\(({SCOPE_PATTERN})\))?: (?P<summary>.+)$")
MERGE_SUBJECT_PATTERN = re.compile(r"^Merge (?:branch|pull request) ")
FOOTER_PATTERN = re.compile(r"^(?:BREAKING CHANGE|[A-Za-z][A-Za-z0-9-]*):(?: .+)?$")
LABEL_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9 -]*:(?: .+)?$")


def validate_subject_line(subject: str, *, allow_merge: bool = True) -> tuple[str, ...]:
    if allow_merge and MERGE_SUBJECT_PATTERN.match(subject):
        return ()

    errors: list[str] = []
    if len(subject) > 72:
        errors.append("subject must be 72 characters or fewer")
    if subject.endswith("."):
        errors.append("subject must not end with a period")
    if SUBJECT_PATTERN.fullmatch(subject) is None:
        allowed_types = ", ".join(ALLOWED_TYPES)
        errors.append(
            "subject must match `type(scope): imperative summary` or "
            f"`type: imperative summary` using one of: {allowed_types}"
        )
    return tuple(errors)


def _skip_blank_lines(lines: tuple[str, ...], index: int) -> int:
    while index < len(lines) and lines[index] == "":
        index += 1
    return index


def _validate_section_bullets(
    lines: tuple[str, ...],
    *,
    section: str,
    start_index: int,
) -> tuple[int, tuple[str, ...]]:
    errors: list[str] = []
    index = start_index
    bullet_count = 0
    while index < len(lines) and lines[index] != "":
        if not lines[index].startswith("- "):
            errors.append(f"`{section}:` entries must use `- ` bullets")
            while index < len(lines) and lines[index] != "":
                index += 1
            break
        bullet_count += 1
        index += 1

    if bullet_count == 0:
        errors.append(f"`{section}:` must contain at least one bullet")
    return index, tuple(errors)


def _validate_required_section(
    lines: tuple[str, ...],
    *,
    section: str,
    start_index: int,
) -> tuple[int, tuple[str, ...]]:
    index = _skip_blank_lines(lines, start_index)
    if index >= len(lines) or lines[index] != f"{section}:":
        return index, (f"missing `{section}:` section",)
    return _validate_section_bullets(lines, section=section, start_index=index + 1)


def _validate_trailing_lines(
    lines: tuple[str, ...],
    *,
    start_index: int,
    allow_footers: bool,
) -> tuple[str, ...]:
    errors: list[str] = []
    index = start_index
    while index < len(lines):
        line = lines[index]
        if line == "":
            index += 1
            continue
        if allow_footers and FOOTER_PATTERN.fullmatch(line) is not None:
            index += 1
            continue
        if LABEL_PATTERN.fullmatch(line) is not None:
            errors.append(f"unsupported structured label: {line}")
        else:
            errors.append(f"unexpected trailing content: {line}")
        index += 1
    return tuple(errors)


def validate_structured_sections(
    lines: tuple[str, ...],
    *,
    required_sections: tuple[str, ...],
    require_body: bool,
    label: str,
    allow_footers: bool,
) -> tuple[str, ...]:
    errors: list[str] = []
    if require_body and len(lines) == 1:
        sections = ", ".join(f"`{section}:`" for section in required_sections)
        errors.append(f"{label} body is required with {sections} sections")
        return tuple(errors)

    index = 2
    if len(lines) > 1 and lines[1] != "":
        errors.append("insert a blank line between the subject and the body")

    for section in required_sections:
        index, section_errors = _validate_required_section(lines, section=section, start_index=index)
        errors.extend(section_errors)

    errors.extend(_validate_trailing_lines(lines, start_index=index, allow_footers=allow_footers))
    return tuple(errors)
