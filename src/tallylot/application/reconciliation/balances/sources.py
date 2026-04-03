"""Source discovery helpers for balance reconciliation workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BALANCE_SNAPSHOT_FILENAME = "balances.csv"
BALANCE_EVIDENCE_FILENAME = "balance_evidence.csv"


@dataclass(frozen=True)
class BalanceSourceDir:
    name: str
    root: Path

    @property
    def snapshot_path(self) -> Path:
        return self.root / BALANCE_SNAPSHOT_FILENAME

    @property
    def evidence_path(self) -> Path:
        return self.root / BALANCE_EVIDENCE_FILENAME

    def output_root(self, base_output_root: Path, *, single_source: bool) -> Path:
        return base_output_root if single_source else base_output_root / self.name


def discover_balance_source_dirs(input_root: Path) -> tuple[BalanceSourceDir, ...]:
    if not input_root.is_dir():
        raise ValueError(f"balance input root must be a directory: {input_root}")
    if source_dir_input(input_root):
        return (BalanceSourceDir(name=input_root.name, root=input_root),)
    return tuple(
        BalanceSourceDir(name=source_dir.name, root=source_dir)
        for source_dir in sorted(input_root.iterdir())
        if source_dir.is_dir() and _has_balance_inputs(source_dir)
    )


def select_balance_source_dirs(
    source_dirs: tuple[BalanceSourceDir, ...],
    requested_sources: tuple[str, ...],
) -> tuple[BalanceSourceDir, ...]:
    if not requested_sources:
        return source_dirs
    selected = tuple(
        source_dir for source_dir in source_dirs if source_dir.name in requested_sources
    )
    selected_names = {source_dir.name for source_dir in selected}
    missing = tuple(
        source for source in requested_sources if source not in selected_names
    )
    if missing:
        raise ValueError(f"unknown balance source selection: {', '.join(missing)}")
    return selected


def source_dir_input(input_root: Path) -> bool:
    return _has_balance_inputs(input_root)


def _has_balance_inputs(path: Path) -> bool:
    return (path / BALANCE_SNAPSHOT_FILENAME).is_file() or (
        path / BALANCE_EVIDENCE_FILENAME
    ).is_file()
