"""Overlap artifact rendering for staging workflows."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.ports.output_workflows import OverlapResult

from .constants import OVERLAP_FLAGGED_HEADER


def summary_int(summary: Mapping[str, JsonValue], key: str) -> int:
    value = summary.get(key, 0)
    return value if isinstance(value, int) else 0


def write_overlap_artifacts(
    output_dir: Path,
    result: OverlapResult,
    *,
    write_json: Callable[[Path, JsonValue], None],
    write_rows: Callable[[Path, tuple[str, ...], Iterable[dict[str, str]]], None],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "overlap_summary.json", result.summary)
    write_rows(output_dir / "overlap_flagged_rows.csv", OVERLAP_FLAGGED_HEADER, result.flagged_rows)
