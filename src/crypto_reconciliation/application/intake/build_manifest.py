"""Build deterministic intake manifests."""

from __future__ import annotations

import hashlib
import json

from crypto_reconciliation.application.intake.archive import scanned_tree_files
from crypto_reconciliation.application.intake.contracts import ManifestRequest, ManifestResponse
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

ISSUE_HEADER = ("relative_path", "severity", "kind", "message")


class BuildManifestUseCase:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: ManifestRequest) -> ManifestResponse:
        rows: list[dict[str, str]] = []
        issue_rows: list[dict[str, str]] = []
        issues_path = request.output_path.with_name("manifest_issues.csv")
        with scanned_tree_files(
            request.source_dir,
            exclude_paths=(request.output_path, issues_path),
            inspect_archives=request.inspect_archives,
        ) as scanned_tree:
            for entry in scanned_tree.files:
                rows.append(
                    {
                        "filename": entry.relative_path,
                        "archive_source_path": entry.archive_source_path,
                        "archive_member_path": entry.archive_member_path,
                        "size_bytes": str(entry.size_bytes),
                        "sha256": entry.sha256,
                    }
                )
            issue_rows.extend(
                {
                    "relative_path": issue.relative_path,
                    "severity": issue.severity,
                    "kind": issue.kind,
                    "message": issue.message,
                }
                for issue in scanned_tree.issues
            )

        payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
        fingerprint = _sha256sum_from_text(payload)
        self._artifacts.write_rows(
            request.output_path,
            ("filename", "archive_source_path", "archive_member_path", "size_bytes", "sha256"),
            rows,
        )
        self._artifacts.write_rows(
            issues_path,
            ISSUE_HEADER,
            issue_rows,
        )
        return ManifestResponse(
            output_path=request.output_path,
            file_count=len(rows),
            manifest_fingerprint=fingerprint,
            issue_count=len(issue_rows),
        )


def _sha256sum_from_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
