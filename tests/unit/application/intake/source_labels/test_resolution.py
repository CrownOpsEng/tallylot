from __future__ import annotations

from pathlib import Path

from tallylot.application.intake.file_facts import IntakeFileFacts
from tallylot.application.intake.path_rules import override_target_source
from tallylot.application.intake.source_labels import (
    load_source_label_context,
    resolve_source_label,
    SourceLabelResolutionRequest,
)
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_load_source_label_context_reads_rules_and_reports_conflicts(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    issues_dir = workspace_root / "analysis" / "issues"
    issues_dir.mkdir(parents=True)
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        issues_dir / "source_inventory.csv",
        ("source",),
        ({"source": "binance-main"}, {"source": "binance-alt"}),
    )
    artifacts.write_rows(
        issues_dir / "source_label_map.csv",
        ("incoming_path_prefix", "source", "notes"),
        (
            {"incoming_path_prefix": ".", "source": "binance-main", "notes": ""},
            {"incoming_path_prefix": "capture", "source": "binance-main", "notes": ""},
            {"incoming_path_prefix": "capture", "source": "binance-alt", "notes": ""},
            {"incoming_path_prefix": "../bad", "source": "binance-main", "notes": ""},
        ),
    )

    context = load_source_label_context(artifacts, workspace_root)

    assert tuple(rule.prefix for rule in context.rules) == (".",)
    assert {issue.kind for issue in context.issues} == {
        "source_label_map_conflict",
        "source_label_map_invalid_prefix",
    }


def test_resolve_source_label_prefers_explicit_map_for_source_scoped_working_paths(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    issues_dir = workspace_root / "analysis" / "issues"
    issues_dir.mkdir(parents=True)
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        issues_dir / "source_inventory.csv",
        ("source",),
        ({"source": "binance-main"},),
    )
    artifacts.write_rows(
        issues_dir / "source_label_map.csv",
        ("incoming_path_prefix", "source", "notes"),
        (
            {
                "incoming_path_prefix": "2021/Binance",
                "source": "binance-main",
                "notes": "",
            },
        ),
    )

    decision = resolve_source_label(
        artifacts=artifacts,
        context=load_source_label_context(artifacts, workspace_root),
        request=SourceLabelResolutionRequest(
            workspace_root=workspace_root,
            route_key="2021/Binance/trade Analysis - ADA-USDT - Binance.png",
            facts=IntakeFileFacts(),
            source_folder="binance",
            target_path=workspace_root
            / "working"
            / "supporting_artifacts"
            / "binance"
            / "incoming"
            / "trade Analysis - ADA-USDT - Binance.png",
        ),
    )

    assert decision.source_folder == "binance-main"
    assert decision.source_resolution_status == "explicit_map"
    assert decision.inventory_match_status == "not_evaluated_explicit_map"


def test_resolve_source_label_blocks_matching_unknown_source_mapping(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    issues_dir = workspace_root / "analysis" / "issues"
    issues_dir.mkdir(parents=True)
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        issues_dir / "source_inventory.csv",
        ("source",),
        ({"source": "binance-main"},),
    )
    artifacts.write_rows(
        issues_dir / "source_label_map.csv",
        ("incoming_path_prefix", "source", "notes"),
        ({"incoming_path_prefix": ".", "source": "missing-source", "notes": ""},),
    )

    decision = resolve_source_label(
        artifacts=artifacts,
        context=load_source_label_context(artifacts, workspace_root),
        request=SourceLabelResolutionRequest(
            workspace_root=workspace_root,
            route_key="transactions.csv",
            facts=IntakeFileFacts(),
            source_folder="unclassified",
            target_path=workspace_root
            / "evidence"
            / "raw"
            / "source"
            / "unclassified"
            / "incoming"
            / "transactions.csv",
        ),
    )

    assert decision.source_resolution_status == "explicit_map_blocked"
    assert decision.review_codes == "source_map_unknown_source"
    assert decision.blocked is True


def test_override_target_source_updates_any_source_scoped_working_surface() -> None:
    original = Path("/tmp/workspace/working/normalized/binance/incoming/facts.csv")

    updated = override_target_source(original, "binance", "binance-main")

    assert updated == Path(
        "/tmp/workspace/working/normalized/binance-main/incoming/facts.csv"
    )


def test_override_target_source_handles_ancestor_named_working() -> None:
    original = Path(
        "/tmp/working/sandboxes/workspace/working/supporting_artifacts/binance/incoming/facts.csv"
    )

    updated = override_target_source(original, "binance", "binance-main")

    assert updated == Path(
        "/tmp/working/sandboxes/workspace/working/supporting_artifacts/binance-main/incoming/facts.csv"
    )


def test_resolve_source_label_skips_non_source_scoped_working_paths(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    issues_dir = workspace_root / "analysis" / "issues"
    issues_dir.mkdir(parents=True)
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        issues_dir / "source_inventory.csv",
        ("source",),
        ({"source": "binance-main"},),
    )
    artifacts.write_rows(
        issues_dir / "source_label_map.csv",
        ("incoming_path_prefix", "source", "notes"),
        ({"incoming_path_prefix": ".", "source": "binance-main", "notes": ""},),
    )

    decision = resolve_source_label(
        artifacts=artifacts,
        context=load_source_label_context(artifacts, workspace_root),
        request=SourceLabelResolutionRequest(
            workspace_root=workspace_root,
            route_key="batch-001/manifest.csv",
            facts=IntakeFileFacts(),
            source_folder="binance",
            target_path=workspace_root
            / "working"
            / "import_batches"
            / "batch-001"
            / "manifest.csv",
        ),
    )

    assert decision.source_folder == "binance"
    assert decision.source_resolution_status == "routed_source"
    assert (
        decision.source_resolution_reason
        == "Non-source-scoped destination keeps routed source binance."
    )
    assert decision.inventory_match_status == "unmatched"
