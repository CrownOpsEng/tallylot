from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlparse

from .state import AGENTS_ROOT, DOCS_ROOT, REPO_ROOT, display_path

MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def repo_markdown_paths() -> tuple[Path, ...]:
    return (
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        *sorted(DOCS_ROOT.rglob("*.md")),
        *sorted((REPO_ROOT / ".claude" / "commands").glob("*.md")),
        *sorted(AGENTS_ROOT.rglob("*.md")),
    )


def text_without_fenced_code(text: str) -> str:
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append(line)
    return "\n".join(lines)


def normalize_anchor(heading: str) -> str:
    text = re.sub(r"\[([^\]]+)]\([^)]+\)", r"\1", heading)
    text = text.replace("`", "")
    text = text.strip().lower()
    text = "".join(character for character in text if character.isalnum() or character in {" ", "-", "_"})
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def heading_anchors(path: Path) -> set[str]:
    text = text_without_fenced_code(path.read_text(encoding="utf-8"))
    anchors: set[str] = set()
    for line in text.splitlines():
        match = HEADING_PATTERN.match(line)
        if match is None:
            continue
        anchor = normalize_anchor(match.group(2))
        if anchor:
            anchors.add(anchor)
    return anchors


def markdown_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        return target[1:-1].strip()
    parts = target.split()
    if not parts:
        raise ValueError("Markdown link target is empty")
    return parts[0]


def validate_markdown_links(paths: Iterable[Path]) -> None:
    anchor_cache: dict[Path, set[str]] = {}
    for path in paths:
        text = text_without_fenced_code(path.read_text(encoding="utf-8"))
        for match in MARKDOWN_LINK_PATTERN.finditer(text):
            target = markdown_target(match.group(1))
            parsed = urlparse(target)
            if parsed.scheme in {"http", "https", "mailto"}:
                continue

            target_path_text, anchor = target, None
            if "#" in target:
                target_path_text, anchor = target.split("#", 1)

            if not target_path_text:
                target_path = path
            else:
                target_path = (path.parent / target_path_text).resolve()
                if not target_path.exists():
                    raise ValueError(f"{path} links to missing path {target_path_text}")

            if anchor is None:
                continue

            if target_path.suffix != ".md":
                raise ValueError(f"{path} uses a Markdown anchor on non-Markdown target {target}")

            anchors = anchor_cache.setdefault(target_path, heading_anchors(target_path))
            if anchor not in anchors:
                target_label = display_path(target_path) if target_path != path else display_path(path)
                raise ValueError(f"{path} links to missing anchor #{anchor} in {target_label}")
