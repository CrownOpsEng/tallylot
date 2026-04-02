from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from tools.message_standards import validate_structured_sections, validate_subject_line


def _normalize_body_lines(body: str) -> tuple[str, ...]:
    lines = tuple(line.rstrip() for line in body.splitlines())
    while lines and lines[-1] == "":
        lines = lines[:-1]
    return lines


def validate_pr_title(title: str) -> tuple[str, ...]:
    stripped = title.strip()
    if stripped == "":
        return ("PR title is required",)
    return validate_subject_line(stripped, allow_merge=False)


def validate_pr_body(body: str) -> tuple[str, ...]:
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


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate pull request title and body for squash merges.")
    parser.add_argument("--title", required=True, help="Pull request title.")
    parser.add_argument("--body", required=True, help="Pull request body.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_argument_parser().parse_args(argv)

    errors = [*validate_pr_title(args.title), *validate_pr_body(args.body)]
    if not errors:
        return 0

    print("pull request metadata failed validation:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
