from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlparse

from .state import AGENTS_ROOT, DOCS_ROOT, REPO_ROOT, display_path

INLINE_LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
REFERENCE_LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\]\[([^\]]*)\]")
SHORTCUT_REFERENCE_LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\](?![\[(])")
REFERENCE_DEFINITION_PATTERN = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s*(\S.*?)\s*$")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
BARE_UV_LINE_PATTERN = re.compile(r"^uv (run|sync)\b")
BARE_UV_INLINE_PATTERN = re.compile(r"`(uv (?:run|sync)\b[^`]*)`")
FENCE_PATTERN = re.compile(r"^\s{0,3}([`~]{3,})(.*)$")


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
    active_fence: str | None = None
    for line in text.splitlines():
        fence_match = FENCE_PATTERN.match(line)
        if fence_match is not None:
            fence = fence_match.group(1)
            fence_char = fence[0]
            fence_length = len(fence)
            if active_fence is None:
                active_fence = fence_char * fence_length
                continue
            if active_fence[0] == fence_char and fence_length >= len(active_fence):
                active_fence = None
                continue
        if active_fence is not None:
            continue
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
    counts: Counter[str] = Counter()
    for line in text.splitlines():
        match = HEADING_PATTERN.match(line)
        if match is None:
            continue
        base_anchor = normalize_anchor(match.group(2))
        if not base_anchor:
            continue
        duplicate_count = counts[base_anchor]
        anchor = base_anchor if duplicate_count == 0 else f"{base_anchor}-{duplicate_count}"
        counts[base_anchor] += 1
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


def reference_definitions(text: str) -> dict[str, str]:
    definitions: dict[str, str] = {}
    for line in text.splitlines():
        match = REFERENCE_DEFINITION_PATTERN.match(line)
        if match is None:
            continue
        definitions[match.group(1).strip().lower()] = markdown_target(match.group(2))
    return definitions


def inline_targets(text: str) -> list[str]:
    return [markdown_target(match.group(2)) for match in INLINE_LINK_PATTERN.finditer(text)]


def reference_targets(text: str) -> list[str]:
    definitions = reference_definitions(text)
    targets: list[str] = []
    for match in REFERENCE_LINK_PATTERN.finditer(text):
        label = match.group(2).strip() or match.group(1).strip()
        if label.lower() in definitions:
            targets.append(definitions[label.lower()])
    for match in SHORTCUT_REFERENCE_LINK_PATTERN.finditer(text):
        label = match.group(1).strip()
        if label.lower() in definitions:
            targets.append(definitions[label.lower()])
    return targets


def markdown_targets(text: str) -> list[str]:
    return [*inline_targets(text), *reference_targets(text)]


def validate_markdown_links(paths: Iterable[Path]) -> None:
    anchor_cache: dict[Path, set[str]] = {}
    for path in paths:
        text = text_without_fenced_code(path.read_text(encoding="utf-8"))
        for target in markdown_targets(text):
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


def bare_uv_examples(path: Path) -> tuple[str, ...]:
    offenders: list[str] = []
    text = text_without_fenced_code(path.read_text(encoding="utf-8"))
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312"'):
            continue
        if BARE_UV_LINE_PATTERN.match(stripped):
            offenders.append(stripped)
            continue
        offenders.extend(match.group(1) for match in BARE_UV_INLINE_PATTERN.finditer(line))
    return tuple(offenders)


def validate_uv_examples(paths: Iterable[Path]) -> None:
    offenders: dict[str, tuple[str, ...]] = {}
    for path in paths:
        examples = bare_uv_examples(path)
        if examples:
            offenders[display_path(path)] = examples
    if offenders:
        raise ValueError(f"markdown surfaces contain bare uv examples: {offenders}")
