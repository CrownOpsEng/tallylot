from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

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
SECTION_PATTERN = re.compile(r"^(?:Why|What|Checks):(?: .+)?$")
FOOTER_PATTERN = re.compile(r"^(?:BREAKING CHANGE|[A-Za-z][A-Za-z0-9-]*):(?: .+)?$")
LABEL_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9 -]*:(?: .+)?$")


@dataclass(frozen=True)
class CommitMessage:
    label: str
    text: str


def normalize_message_lines(message: str) -> tuple[str, ...]:
    lines: list[str] = []
    for raw_line in message.splitlines():
        line = raw_line.rstrip()
        if line.lstrip().startswith("#"):
            continue
        lines.append(line)

    while lines and lines[-1] == "":
        lines.pop()
    return tuple(lines)


def validate_commit_message_text(message: str) -> tuple[str, ...]:
    lines = normalize_message_lines(message)
    if not lines or lines[0] == "":
        return ("commit message subject is required",)

    subject = lines[0]
    if MERGE_SUBJECT_PATTERN.match(subject):
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
    if len(lines) > 1 and lines[1] != "":
        errors.append("insert a blank line between the subject and the body")

    for line in lines[2:]:
        if line == "":
            continue
        if SECTION_PATTERN.fullmatch(line) is not None:
            continue
        if FOOTER_PATTERN.fullmatch(line) is not None:
            continue
        if LABEL_PATTERN.fullmatch(line) is not None:
            errors.append(f"unsupported structured label: {line}")

    return tuple(errors)


def load_commit_message_file(path: Path) -> CommitMessage:
    return CommitMessage(label=str(path), text=path.read_text(encoding="utf-8"))


def load_commit_messages_from_range(rev_range: str) -> tuple[CommitMessage, ...]:
    revision_result = subprocess.run(
        ["git", "rev-list", "--reverse", rev_range],
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
        messages.append(CommitMessage(label=f"commit {commit_id[:7]}", text=message_result.stdout))
    return tuple(messages)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate commit messages for this repo.")
    parser.add_argument("message_files", metavar="MESSAGE_FILE", nargs="*", help="Path to commit message file.")
    parser.add_argument("--rev-range", dest="rev_range", help="Git revision range to validate.")
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_argument_parser().parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.message_files and args.rev_range is None:
        print("provide a commit message file or --rev-range", file=sys.stderr)
        return 2

    messages: list[CommitMessage] = []
    if args.rev_range is not None:
        messages.extend(load_commit_messages_from_range(args.rev_range))
    messages.extend(load_commit_message_file(Path(path)) for path in args.message_files)

    has_errors = False
    for message in messages:
        errors = validate_commit_message_text(message.text)
        if not errors:
            continue
        has_errors = True
        print(f"{message.label} failed validation:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)

    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
