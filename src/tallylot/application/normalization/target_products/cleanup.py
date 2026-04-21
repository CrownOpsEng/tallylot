"""Owned cleanup helpers for target-product execution."""

from __future__ import annotations

from pathlib import Path


def prune_owned_paths(paths: tuple[Path, ...]) -> None:
    for path in paths:
        if path.is_file():
            path.unlink()
