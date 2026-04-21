"""Owned cleanup helpers for target-product execution."""

from __future__ import annotations

from pathlib import Path
import shutil


def pruned_refs(
    *, prior_refs: tuple[str, ...], current_refs: tuple[str, ...]
) -> tuple[str, ...]:
    return tuple(sorted(set(prior_refs) - set(current_refs)))


def prune_product_roots(workspace_root: Path, refs: tuple[str, ...]) -> None:
    for ref in refs:
        root = (workspace_root / ref).parent
        if root.exists():
            shutil.rmtree(root)


def prune_owned_paths(paths: tuple[Path, ...]) -> None:
    for path in paths:
        if path.is_file():
            path.unlink()
