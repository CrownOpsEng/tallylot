from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence

from tools.message_standards import validate_structured_sections, validate_subject_line


def _normalize_body_lines(body: str) -> tuple[str, ...]:
    lines: list[str] = []
    in_html_comment = False

    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if in_html_comment:
            if "-->" in stripped:
                in_html_comment = False
            continue

        if stripped.startswith("<!--"):
            if "-->" not in stripped:
                in_html_comment = True
            continue

        lines.append(line)

    while lines and lines[-1] == "":
        lines.pop()
    return tuple(lines)


def _parse_required_sections(body: str) -> dict[str, tuple[str, ...]]:
    sections = ("Why", "What", "Checks", "Included checkpoints")
    parsed: dict[str, list[str]] = {section: [] for section in sections}
    current_section: str | None = None

    for line in _normalize_body_lines(body):
        if line in {f"{section}:" for section in sections}:
            current_section = line[:-1]
            continue
        if line == "":
            current_section = None
            continue
        if current_section is None:
            continue
        parsed[current_section].append(line)

    return {section: tuple(values) for section, values in parsed.items()}


def _normalize_checkpoint_entry(entry: str) -> str:
    text = entry.removeprefix("- ").strip()
    if text.startswith("`") and text.endswith("`") and len(text) >= 2:
        return text[1:-1]
    return text


def _load_commit_subjects(base_sha: str, head_sha: str) -> tuple[str, ...]:
    revision_result = subprocess.run(
        ["git", "log", "--format=%s", "--reverse", f"{base_sha}..{head_sha}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(line for line in revision_result.stdout.splitlines() if line)


def _validate_pr_title(title: str) -> tuple[str, ...]:
    stripped = title.strip()
    if stripped == "":
        return ("PR title is required",)
    return validate_subject_line(stripped, allow_merge=False)


def _validate_pr_body(body: str) -> tuple[str, ...]:
    lines = _normalize_body_lines(body)
    if not lines:
        return ("PR body is required",)
    return validate_structured_sections(
        ("placeholder", "", *lines),
        required_sections=("Why", "What", "Checks", "Included checkpoints"),
        require_body=True,
        label="PR",
        allow_footers=False,
    )


def _validate_pr_checkpoints(body: str, *, base_sha: str, head_sha: str) -> tuple[str, ...]:
    parsed_sections = _parse_required_sections(body)
    checkpoint_entries = parsed_sections["Included checkpoints"]
    normalized_entries = tuple(_normalize_checkpoint_entry(entry) for entry in checkpoint_entries)
    actual_subjects = _load_commit_subjects(base_sha, head_sha)

    errors: list[str] = []
    for entry, normalized in zip(checkpoint_entries, normalized_entries, strict=False):
        if not entry.startswith("- `") or not entry.endswith("`"):
            errors.append("`Included checkpoints:` entries must wrap commit subjects in backticks")
            break

        if validate_subject_line(normalized, allow_merge=False):
            errors.append("`Included checkpoints:` entries must be exact Conventional Commit subjects")
            break

    if normalized_entries != actual_subjects:
        errors.append("`Included checkpoints:` must exactly match the branch commit subjects in order")
    return tuple(errors)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate pull request title and body for squash merges.")
    parser.add_argument("--title", required=True, help="Pull request title.")
    parser.add_argument("--body", required=True, help="Pull request body.")
    parser.add_argument("--base-sha", help="Base commit SHA for validating included checkpoints.")
    parser.add_argument("--head-sha", help="Head commit SHA for validating included checkpoints.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_argument_parser().parse_args(argv)

    errors = [*_validate_pr_title(args.title), *_validate_pr_body(args.body)]
    if args.base_sha and args.head_sha:
        errors.extend(_validate_pr_checkpoints(args.body, base_sha=args.base_sha, head_sha=args.head_sha))
    if not errors:
        return 0

    print("pull request metadata failed validation:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
