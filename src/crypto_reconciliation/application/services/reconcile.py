"""Source reconciliation service."""

from __future__ import annotations

import hashlib

from crypto_reconciliation.application.dtos import SourceReconcileRequest, SourceReconcileResponse
from crypto_reconciliation.ports.artifacts import ArtifactStorePort


class SourceReconciliationService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: SourceReconcileRequest) -> SourceReconcileResponse:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        candidate_rows = self._artifacts.read_rows(request.candidate_path)
        reference_rows = self._artifacts.read_rows(request.reference_path)
        candidate_index = {_row_fingerprint(row): row for row in candidate_rows}
        reference_index = {_row_fingerprint(row): row for row in reference_rows}

        candidate_only = [candidate_index[key] for key in sorted(candidate_index.keys() - reference_index.keys())]
        reference_only = [reference_index[key] for key in sorted(reference_index.keys() - candidate_index.keys())]
        matched_count = len(candidate_index.keys() & reference_index.keys())
        header = (
            tuple(candidate_rows[0].keys())
            if candidate_rows
            else tuple(reference_rows[0].keys())
            if reference_rows
            else ()
        )

        self._artifacts.write_rows(request.output_dir / "candidate_only.csv", header, candidate_only)
        self._artifacts.write_rows(request.output_dir / "reference_only.csv", header, reference_only)
        self._artifacts.write_json(
            request.output_dir / "reconciliation_summary.json",
            {
                "candidate_only_count": len(candidate_only),
                "reference_only_count": len(reference_only),
                "matched_count": matched_count,
            },
        )
        return SourceReconcileResponse(
            output_dir=request.output_dir,
            candidate_only_count=len(candidate_only),
            reference_only_count=len(reference_only),
            matched_count=matched_count,
        )


def _row_fingerprint(row: dict[str, str]) -> str:
    payload = repr(sorted(row.items()))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
