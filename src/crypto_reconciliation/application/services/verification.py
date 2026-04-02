"""Verification comparison service."""

from __future__ import annotations

import hashlib
from typing import cast

from crypto_reconciliation.application.dtos import (
    VerificationCompareRequest,
    VerificationCompareResponse,
)
from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

DEFAULT_REPORTS = (
    "Validate Transactions.csv",
    "Missing Transactions.csv",
    "Duplicate Transactions.csv",
    "Current Balance.csv",
    "Balance by Exchange.csv",
)


class VerificationCompareService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: VerificationCompareRequest) -> VerificationCompareResponse:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        changed_reports = 0
        summary: list[dict[str, str]] = []
        for report_name in DEFAULT_REPORTS:
            previous_path = request.previous_dir / report_name
            current_path = request.current_dir / report_name
            previous_rows = self._artifacts.read_rows(previous_path)
            current_rows = self._artifacts.read_rows(current_path)
            previous_hash = _fingerprint(previous_rows)
            current_hash = _fingerprint(current_rows)
            changed = previous_hash != current_hash
            changed_reports += int(changed)
            summary.append(
                {
                    "report_name": report_name,
                    "previous_rows": str(len(previous_rows)),
                    "current_rows": str(len(current_rows)),
                    "changed": "yes" if changed else "no",
                }
            )
        self._artifacts.write_rows(
            request.output_dir / "verification_summary.csv",
            ("report_name", "previous_rows", "current_rows", "changed"),
            summary,
        )
        self._artifacts.write_json(
            request.output_dir / "verification_summary.json",
            cast(JsonValue, {"changed_reports": changed_reports, "reports": summary}),
        )
        return VerificationCompareResponse(
            output_dir=request.output_dir,
            changed_reports=changed_reports,
        )


def _fingerprint(rows: list[dict[str, str]]) -> str:
    payload = repr(sorted(rows, key=repr))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
