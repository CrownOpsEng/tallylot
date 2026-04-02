"""Round scaffolding service."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from tallylot.ports.artifacts import ArtifactStorePort
from tools.oracles.contracts import RoundScaffoldRequest, RoundScaffoldResponse

_ROUND_LOG_HEADER = (
    "round_id",
    "phase",
    "source",
    "date",
    "goal",
    "output_change",
    "exports_captured",
    "issues_opened_or_closed",
    "gate_result",
    "next_action",
)
_DEFAULT_VERIFICATION_EXPORTS = (
    "Validate Transactions",
    "Missing Transactions",
    "Duplicate Transactions",
    "Current Balance",
    "Balance by Exchange",
)
_PHASE_GOALS = {
    "baseline_repair": "Capture fresh verification exports after baseline repair",
    "post_import": "Capture fresh verification exports after source import",
}


class RoundScaffoldingService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: RoundScaffoldRequest) -> RoundScaffoldResponse:
        round_id = _validate_round_id(request.round_id)
        today = request.today or datetime.now(UTC).date()
        round_dir = request.workspace_root / "working" / "verification" / round_id
        round_dir.mkdir(parents=True, exist_ok=True)
        readme_path = round_dir / "README.md"
        if not readme_path.exists():
            readme_path.write_text(
                _build_verification_readme(round_id, request.phase, request.source),
                encoding="utf-8",
            )
        round_log_path = request.workspace_root / "outputs" / "logs" / "round_log.csv"
        existing_rows = self._artifacts.read_rows(round_log_path) if round_log_path.exists() else []
        seeded = not any(row["round_id"] == round_id for row in existing_rows)
        rows = [row for row in existing_rows if row.get("round_id") != round_id]
        rows.append(_create_round_log_entry(request, round_dir, today))
        self._artifacts.write_rows(round_log_path, _ROUND_LOG_HEADER, rows)
        return RoundScaffoldResponse(
            workspace_root=request.workspace_root,
            round_dir=round_dir,
            round_log_path=round_log_path,
            readme_path=readme_path,
            seeded=seeded,
        )


def _validate_round_id(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("round_id must not be empty")
    path = Path(normalized)
    if normalized in {".", ".."} or len(path.parts) != 1:
        raise ValueError("round_id must be a single path segment")
    if "/" in normalized or "\\" in normalized:
        raise ValueError("round_id must be a single path segment")
    return normalized


def _build_verification_readme(round_id: str, phase: str, source: str) -> str:
    goal = _PHASE_GOALS.get(phase, "Capture fresh verification exports for review")
    lines = [
        f"# Verification Round {round_id}",
        "",
        f"- Phase: {phase}",
        f"- Source: {source}",
        f"- Goal: {goal}",
        "",
        "Expected exports:",
    ]
    lines.extend(f"- {export_name}" for export_name in _DEFAULT_VERIFICATION_EXPORTS)
    lines.extend(
        (
            "",
            "Notes:",
            "- Capture the comparison export set for this round before review closes.",
        )
    )
    return "\n".join(lines) + "\n"


def _create_round_log_entry(
    request: RoundScaffoldRequest,
    verification_dir: Path,
    today: date,
) -> dict[str, str]:
    goal = _PHASE_GOALS.get(request.phase, "Capture fresh verification exports for review")
    return {
        "round_id": request.round_id,
        "phase": request.phase,
        "source": request.source,
        "date": today.isoformat(),
        "goal": goal,
        "output_change": "",
        "exports_captured": str(verification_dir.relative_to(request.workspace_root)),
        "issues_opened_or_closed": "",
        "gate_result": "pending",
        "next_action": "",
    }
