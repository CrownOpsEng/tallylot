#!/usr/bin/env python3

"""Canonical raw-export layout helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


RAW_EXPORTS_DIRNAME = "01_raw_exports"
SOURCE_BRANCH = "source"
PORTFOLIO_BRANCH = "portfolio"
COINTRACKING_SYSTEM = "cointracking"
COINTRACKING_BASELINE_CAPTURE = "2023-08-05_full_export"
COINTRACKING_HISTORY_CAPTURE = "history"


@dataclass(frozen=True)
class CapturePathInfo:
    branch: str
    source_folder: str
    capture_path: Path


def raw_exports_root(repo_root: Path) -> Path:
    return repo_root / RAW_EXPORTS_DIRNAME


def source_root(repo_root: Path) -> Path:
    return raw_exports_root(repo_root) / SOURCE_BRANCH


def source_capture_root(repo_root: Path, source_folder: str) -> Path:
    return source_root(repo_root) / source_folder


def portfolio_root(repo_root: Path) -> Path:
    return raw_exports_root(repo_root) / PORTFOLIO_BRANCH


def portfolio_system_root(repo_root: Path, system_folder: str) -> Path:
    return portfolio_root(repo_root) / system_folder


def cointracking_portfolio_root(repo_root: Path) -> Path:
    return portfolio_system_root(repo_root, COINTRACKING_SYSTEM)


def cointracking_baseline_dir(repo_root: Path) -> Path:
    return cointracking_portfolio_root(repo_root) / COINTRACKING_BASELINE_CAPTURE


def cointracking_history_root(repo_root: Path) -> Path:
    return cointracking_portfolio_root(repo_root) / COINTRACKING_HISTORY_CAPTURE


def parse_capture_path(capture_path: str) -> CapturePathInfo | None:
    parts = Path(capture_path).parts
    if len(parts) >= 4 and parts[0] == RAW_EXPORTS_DIRNAME:
        if parts[1] == SOURCE_BRANCH:
            return CapturePathInfo(branch=SOURCE_BRANCH, source_folder=parts[2], capture_path=Path(*parts))
        if parts[1] == PORTFOLIO_BRANCH:
            return CapturePathInfo(branch=PORTFOLIO_BRANCH, source_folder=parts[2], capture_path=Path(*parts))
    return None
