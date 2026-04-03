"""Row-diff service for candidate versus reference slices."""

from __future__ import annotations

from collections import Counter

from tallylot.ports.artifacts import ArtifactStorePort
from tools.oracles.contracts import SourceDiffRequest, SourceDiffResponse


class SourceDiffService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: SourceDiffRequest) -> SourceDiffResponse:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        candidate_rows = self._artifacts.read_rows(request.candidate_path)
        reference_rows = self._artifacts.read_rows(request.reference_path)
        candidate_counts = Counter(_row_signature(row) for row in candidate_rows)
        reference_counts = Counter(_row_signature(row) for row in reference_rows)

        candidate_only = _expand_rows(candidate_counts - reference_counts)
        reference_only = _expand_rows(reference_counts - candidate_counts)
        matched_count = sum((candidate_counts & reference_counts).values())
        header = _diff_header(candidate_rows, reference_rows)

        self._artifacts.write_rows(request.output_dir / "candidate_only.csv", header, candidate_only)
        self._artifacts.write_rows(request.output_dir / "reference_only.csv", header, reference_only)
        self._artifacts.write_json(
            request.output_dir / "diff_summary.json",
            {
                "candidate_only_count": len(candidate_only),
                "reference_only_count": len(reference_only),
                "matched_count": matched_count,
            },
        )
        return SourceDiffResponse(
            output_dir=request.output_dir,
            candidate_only_count=len(candidate_only),
            reference_only_count=len(reference_only),
            matched_count=matched_count,
        )


def _row_signature(row: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((key, value or "") for key, value in row.items()))


def _expand_rows(counter: Counter[tuple[tuple[str, str], ...]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for signature, count in sorted(counter.items()):
        row = dict(signature)
        for _ in range(count):
            rows.append(row)
    return rows


def _diff_header(candidate_rows: list[dict[str, str]], reference_rows: list[dict[str, str]]) -> tuple[str, ...]:
    ordered_fields: list[str] = []
    for row in (*candidate_rows, *reference_rows):
        for field in row:
            if field not in ordered_fields:
                ordered_fields.append(field)
    return tuple(ordered_fields)
