"""Application-owned filesystem guards for workspace-oriented workflows."""

from __future__ import annotations

from pathlib import Path


def _resolve_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        _resolve_path(path).relative_to(_resolve_path(root))
    except ValueError:
        return False
    return True


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_output_not_within_input_tree(
    input_root: Path,
    output_path: Path,
    *,
    input_label: str,
    output_label: str,
) -> None:
    if _path_is_within(output_path, input_root):
        raise ValueError(
            f"{output_label} must not be inside {input_label}: {output_path}"
        )


def iter_tree_files(
    root: Path, *, exclude_paths: tuple[Path, ...] = ()
) -> tuple[Path, ...]:
    excluded = {_resolve_path(path) for path in exclude_paths}
    return tuple(
        sorted(
            candidate
            for candidate in root.rglob("*")
            if candidate.is_file() and _resolve_path(candidate) not in excluded
        )
    )
