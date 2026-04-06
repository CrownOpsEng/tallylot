from __future__ import annotations

from pathlib import Path

from tallylot.infrastructure.workspace import FilesystemWorkspaceRepository


def test_workspace_repository_initializes_seed_files(tmp_path: Path) -> None:
    repository = FilesystemWorkspaceRepository()

    created_paths = repository.initialize(tmp_path)

    issue_log = tmp_path / "analysis/issues/issue_log.csv"
    source_inventory = tmp_path / "analysis/issues/source_inventory.csv"
    source_label_map = tmp_path / "analysis/issues/source_label_map.csv"

    assert created_paths
    assert issue_log.exists()
    assert source_inventory.exists()
    assert source_label_map.exists()
    assert (tmp_path / "outputs/logs/round_log.csv").exists()
    assert (tmp_path / "config/workspace.json").exists()
    assert issue_log.read_text(encoding="utf-8").splitlines()[0] == (
        "issue_id,source_file,issue_class,priority,asset,exchange,date,direction,amount,"
        "cad_value,status,disposition,likely_meaning,proof_needed,proof_path,"
        "proof_summary,planned_action,external_action,verification_path,gate_result,"
        "closed_at,notes"
    )
    assert source_inventory.read_text(encoding="utf-8").splitlines()[0] == (
        "source,activity_after_cutoff,first_post_cutoff_tx,export_window_start,"
        "export_window_end,import_order,status,capture_path,profile_status,adapter,"
        "normalization_status,exception_count,candidate_path,notes"
    )
    assert source_label_map.read_text(encoding="utf-8").splitlines()[0] == (
        "incoming_path_prefix,source,notes"
    )
