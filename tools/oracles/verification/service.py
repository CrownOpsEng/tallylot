"""Verification comparison service."""

from __future__ import annotations

from pathlib import Path

from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort
from tools.oracles.contracts import VerificationCompareRequest, VerificationCompareResponse

from .summary import summarize_verification_exports


class VerificationCompareService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: VerificationCompareRequest) -> VerificationCompareResponse:
        summary = self._summarize(request.previous_dir, request.current_dir)
        request.output_dir.mkdir(parents=True, exist_ok=True)
        self._write_artifacts(request.output_dir, summary)
        return VerificationCompareResponse(
            output_dir=request.output_dir,
            changed_reports=_summary_int(summary, "changed_reports"),
            gate_suggestion=_summary_str(summary, "gate_suggestion"),
        )

    def _summarize(self, previous_dir: Path, current_dir: Path) -> dict[str, JsonValue]:
        return summarize_verification_exports(previous_dir, current_dir, self._artifacts)

    def _write_artifacts(self, output_dir: Path, summary: dict[str, JsonValue]) -> None:
        self._artifacts.write_json(output_dir / "verification_summary.json", summary)
        self._artifacts.write_rows(
            output_dir / "new_validate_issue_rows.csv",
            _summary_headers(summary, "new_validate_issue_rows", default=("Issue",)),
            _summary_rows(summary, "new_validate_issue_rows"),
        )
        self._artifacts.write_rows(
            output_dir / "resolved_validate_issue_rows.csv",
            _summary_headers(summary, "resolved_validate_issue_rows", default=("Issue",)),
            _summary_rows(summary, "resolved_validate_issue_rows"),
        )
        self._artifacts.write_rows(
            output_dir / "new_missing_transaction_rows.csv",
            _summary_headers(summary, "new_missing_transaction_rows", default=("Type",)),
            _summary_rows(summary, "new_missing_transaction_rows"),
        )
        self._artifacts.write_rows(
            output_dir / "resolved_missing_transaction_rows.csv",
            _summary_headers(summary, "resolved_missing_transaction_rows", default=("Type",)),
            _summary_rows(summary, "resolved_missing_transaction_rows"),
        )
        self._artifacts.write_rows(
            output_dir / "current_balance_deltas.csv",
            ("ticker", "reference_amount", "current_amount", "difference"),
            _summary_rows(summary, "current_balance_deltas"),
        )
        self._artifacts.write_rows(
            output_dir / "exchange_balance_deltas.csv",
            ("exchange", "currency", "reference_amount", "current_amount", "difference"),
            _summary_rows(summary, "exchange_balance_deltas"),
        )
        self._artifacts.write_rows(
            output_dir / "current_duplicate_transaction_rows.csv",
            _summary_headers(summary, "current_duplicate_transaction_rows", default=("",)),
            _summary_rows(summary, "current_duplicate_transaction_rows"),
        )


def _summary_headers(
    summary: dict[str, JsonValue],
    key: str,
    *,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    rows = _summary_rows(summary, key)
    if not rows:
        return default
    return tuple(sorted({column for row in rows for column in row}))


def _summary_rows(summary: dict[str, JsonValue], key: str) -> list[dict[str, str]]:
    value = summary.get(key, [])
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        rows.append({str(column): "" if cell is None else str(cell) for column, cell in item.items()})
    return rows


def _summary_int(summary: dict[str, JsonValue], key: str) -> int:
    value = summary.get(key, 0)
    return int(value) if isinstance(value, int) else 0


def _summary_str(summary: dict[str, JsonValue], key: str) -> str:
    value = summary.get(key, "")
    return value if isinstance(value, str) else ""
