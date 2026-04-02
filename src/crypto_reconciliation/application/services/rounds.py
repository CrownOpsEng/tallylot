"""Round scaffolding service."""

from __future__ import annotations

from crypto_reconciliation.application.dtos import RoundScaffoldRequest, RoundScaffoldResponse
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

ROUND_LOG_HEADER = ("round_id", "phase", "source", "status", "verification_dir", "notes")


class RoundScaffoldingService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: RoundScaffoldRequest) -> RoundScaffoldResponse:
        round_dir = request.workspace_root / "working" / "verification" / request.round_id
        round_dir.mkdir(parents=True, exist_ok=True)
        round_log_path = request.workspace_root / "outputs" / "logs" / "round_log.csv"
        existing_rows = self._artifacts.read_rows(round_log_path) if round_log_path.exists() else []
        seeded = not any(row["round_id"] == request.round_id for row in existing_rows)
        rows = [row for row in existing_rows if row.get("round_id") != request.round_id]
        rows.append(
            {
                "round_id": request.round_id,
                "phase": request.phase,
                "source": request.source,
                "status": "seeded",
                "verification_dir": str(round_dir.relative_to(request.workspace_root)),
                "notes": "",
            }
        )
        self._artifacts.write_rows(round_log_path, ROUND_LOG_HEADER, rows)
        return RoundScaffoldResponse(
            workspace_root=request.workspace_root,
            round_dir=round_dir,
            round_log_path=round_log_path,
            seeded=seeded,
        )
