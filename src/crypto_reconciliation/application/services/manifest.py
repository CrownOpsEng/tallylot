"""Source manifest service."""

from __future__ import annotations

import hashlib
import json

from crypto_reconciliation.application.dtos import ManifestRequest, ManifestResponse
from crypto_reconciliation.application.services.common import sha256sum
from crypto_reconciliation.application.services.scan import iter_tree_files
from crypto_reconciliation.ports.artifacts import ArtifactStorePort


class ManifestService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: ManifestRequest) -> ManifestResponse:
        rows: list[dict[str, str]] = []
        for path in iter_tree_files(request.source_dir, exclude_paths=(request.output_path,)):
            rows.append(
                {
                    "filename": str(path.relative_to(request.source_dir)),
                    "size_bytes": str(path.stat().st_size),
                    "sha256": sha256sum(path),
                }
            )

        payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
        fingerprint = _sha256sum_from_text(payload)
        self._artifacts.write_rows(request.output_path, ("filename", "size_bytes", "sha256"), rows)
        return ManifestResponse(
            output_path=request.output_path,
            file_count=len(rows),
            manifest_fingerprint=fingerprint,
        )


def _sha256sum_from_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
