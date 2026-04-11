from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.message_standards import (
    AUTHORED_COMMIT_REQUIRED_SECTIONS,
    GENERATED_MAINLINE_COMMIT_OPTIONAL_SECTIONS,
    validate_structured_sections,
    validate_subject_line,
)

SQUASH_PR_SUBJECT_PATTERN = re.compile(r" \(\#\d+\)$")
ISSUE_CLOSING_KEYWORD_PATTERN = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?) #\d+\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CommitMessage:
    label: str
    text: str


def _normalize_message_lines(message: str) -> tuple[str, ...]:
    lines: list[str] = []
    for raw_line in message.splitlines():
        line = raw_line.rstrip()
        if line.lstrip().startswith("#"):
            continue
        lines.append(line)

    while lines and lines[-1] == "":
        lines.pop()
    return tuple(lines)


def _validate_commit_message_text(message: str) -> tuple[str, ...]:
    lines = _normalize_message_lines(message)
    if not lines or lines[0] == "":
        return ("commit message subject is required",)

    subject = lines[0]
    is_generated_mainline_commit = SQUASH_PR_SUBJECT_PATTERN.search(subject) is not None
    optional_sections = (
        GENERATED_MAINLINE_COMMIT_OPTIONAL_SECTIONS
        if is_generated_mainline_commit
        else ()
    )

    errors = [
        *validate_subject_line(subject),
        *validate_structured_sections(
            lines,
            required_sections=AUTHORED_COMMIT_REQUIRED_SECTIONS,
            optional_sections=optional_sections,
            require_body=True,
            label="commit message",
            allow_footers=True,
        ),
    ]
    if not is_generated_mainline_commit:
        for line in lines[2:]:
            if ISSUE_CLOSING_KEYWORD_PATTERN.search(line):
                errors.append(
                    "authored commit messages must not use issue-closing keywords; use the PR `Why:` section instead"
                )
                break
    return tuple(errors)


def _load_commit_message_file(path: Path) -> CommitMessage:
    return CommitMessage(label=str(path), text=path.read_text(encoding="utf-8"))


def _fallback_rev_range(rev_range: str) -> str | None:
    if ".." not in rev_range:
        return None
    _, head_ref = rev_range.split("..", 1)
    if head_ref == "":
        return None
    return f"{head_ref}^!"


def _load_commit_messages_from_range(rev_range: str) -> tuple[CommitMessage, ...]:
    try:
        revision_result = subprocess.run(
            ["git", "rev-list", "--reverse", rev_range],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        fallback_range = _fallback_rev_range(rev_range)
        if fallback_range is None:
            raise
        revision_result = subprocess.run(
            ["git", "rev-list", "--reverse", fallback_range],
            check=True,
            capture_output=True,
            text=True,
        )
    commit_ids = tuple(line for line in revision_result.stdout.splitlines() if line)
    messages: list[CommitMessage] = []
    for commit_id in commit_ids:
        message_result = subprocess.run(
            ["git", "show", "--quiet", "--format=%B", commit_id],
            check=True,
            capture_output=True,
            text=True,
        )
        messages.append(
            CommitMessage(label=f"commit {commit_id[:7]}", text=message_result.stdout)
        )
    return tuple(messages)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate commit messages for this repo."
    )
    parser.add_argument(
        "message_files",
        metavar="MESSAGE_FILE",
        nargs="*",
        help="Path to commit message file.",
    )
    parser.add_argument(
        "--rev-range", dest="rev_range", help="Git revision range to validate."
    )
    return parser


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _build_argument_parser().parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    if not args.message_files and args.rev_range is None:
        print("provide a commit message file or --rev-range", file=sys.stderr)
        return 2

    messages: list[CommitMessage] = []
    if args.rev_range is not None:
        messages.extend(_load_commit_messages_from_range(args.rev_range))
    messages.extend(
        _load_commit_message_file(Path(path)) for path in args.message_files
    )

    has_errors = False
    for message in messages:
        errors = _validate_commit_message_text(message.text)
        if not errors:
            continue
        has_errors = True
        print(f"{message.label} failed validation:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)

    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
