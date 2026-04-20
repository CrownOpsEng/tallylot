from __future__ import annotations

import json
from pathlib import Path
from typing import cast, override

import pytest

from tallylot.application.normalization import NormalizeRequest
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.types import JsonValue
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.source_adapters import SourceAdapter
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch
from tallylot.ports.translation_inputs import (
    TranslationCoverageMode,
    TranslationCoverageWindow,
    TranslationFreshness,
    TranslationFreshnessKind,
    TranslationInputCandidate,
    TranslationInputPlan,
    TranslationSelectionMode,
    translation_input_content_fingerprint,
    translation_input_coverage_from_inventory_entry,
)
from repo_support.capture_roots import materialize_capture_root
from tests.support.services import (
    FakeSourceRegistry,
    MatchingSourceAdapter,
    build_registry_backed_normalization_service,
)


class TrackingArtifactStore(FilesystemArtifactStore):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self._events = events

    @override
    def write_json(self, path: Path, payload: JsonValue) -> None:
        super().write_json(path, payload)
        self._events.append(path.name)


class PlanningAdapter(MatchingSourceAdapter):
    def __init__(
        self,
        adapter_id: str,
        *,
        candidate_mode: str,
        events: list[str] | None = None,
    ) -> None:
        super().__init__(adapter_id)
        self._candidate_mode = candidate_mode
        self._events = events if events is not None else []
        self.translate_called = False
        self.translate_selected_called = False

    @override
    def translate(
        self, profile: SourceProfile, raw_dir: Path
    ) -> SourceTranslationBatch:
        del profile, raw_dir
        self.translate_called = True
        raise AssertionError(
            "planner-enabled adapters should use translate_selected_inputs"
        )

    def describe_translation_inputs(
        self,
        profile: SourceProfile,
        raw_dir: Path,
    ) -> tuple[TranslationInputCandidate, ...]:
        del raw_dir
        entries = tuple(
            entry for entry in profile.file_inventory if entry.suffix == ".csv"
        )
        if self._candidate_mode == "single":
            return (candidate_from_entry(entries[0], candidate_id="single"),)
        if self._candidate_mode == "blocked":
            return (
                candidate_from_entry(
                    entries[0],
                    candidate_id="first",
                    coverage=unknown_coverage(),
                    freshness=unknown_freshness(),
                ),
                candidate_from_entry(
                    entries[1],
                    candidate_id="second",
                    coverage=unknown_coverage(),
                    freshness=unknown_freshness(),
                ),
            )
        return (
            candidate_from_entry(
                entries[0],
                candidate_id="older",
                freshness=rank_freshness(1),
            ),
            candidate_from_entry(
                entries[1],
                candidate_id="newer",
                freshness=rank_freshness(2),
            ),
        )

    def translate_selected_inputs(
        self,
        profile: SourceProfile,
        raw_dir: Path,
        plan: TranslationInputPlan,
    ) -> SourceTranslationBatch:
        del profile, raw_dir, plan
        self.translate_selected_called = True
        self._events.append("translate_selected_inputs")

        return SourceTranslationBatch(
            drafts=(),
            balance_references=(),
            balance_reference_issues=(),
            issues=(),
            reviews=(),
            location_inventory=(),
        )


class LegacyAdapter(MatchingSourceAdapter):
    def __init__(self, adapter_id: str) -> None:
        super().__init__(adapter_id)
        self.translate_called = False

    @override
    def translate(
        self, profile: SourceProfile, raw_dir: Path
    ) -> SourceTranslationBatch:
        del profile, raw_dir
        self.translate_called = True

        return SourceTranslationBatch(
            drafts=(),
            balance_references=(),
            balance_reference_issues=(),
            issues=(),
            reviews=(),
            location_inventory=(),
        )


def test_normalization_writes_planner_artifacts_before_translation(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="planner_fixture")
    (raw_dir / "one.csv").write_text(
        "Timestamp,Amount\n2026-03-23 15:47:00 UTC,1\n",
        encoding="utf-8",
    )
    events: list[str] = []
    artifacts = TrackingArtifactStore(events)
    adapter = PlanningAdapter("planner_fixture", candidate_mode="single", events=events)
    service = build_registry_backed_normalization_service(
        registry=FakeSourceRegistry(source_adapters=(cast(SourceAdapter, adapter),)),
        artifacts=artifacts,
    )
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="planner_fixture",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    assert response.translation_planner_used is True
    assert (output_dir / "translation_input_candidates.json").exists()
    assert (output_dir / "translation_input_plan.json").exists()
    assert events.index("translation_input_plan.json") < events.index(
        "translate_selected_inputs"
    )


def test_normalization_blocks_before_writing_facts_for_blocked_plan(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="planner_fixture")
    (raw_dir / "one.csv").write_text(
        "Timestamp,Amount\n2026-03-23 15:47:00 UTC,1\n",
        encoding="utf-8",
    )
    (raw_dir / "two.csv").write_text(
        "Timestamp,Amount\n2026-03-24 15:47:00 UTC,2\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    adapter = PlanningAdapter("planner_fixture", candidate_mode="blocked")
    service = build_registry_backed_normalization_service(
        registry=FakeSourceRegistry(source_adapters=(cast(SourceAdapter, adapter),)),
        artifacts=artifacts,
    )
    output_dir = tmp_path / "normalized"

    with pytest.raises(
        ValueError, match="translation input planning blocked normalization"
    ):
        service.execute(
            NormalizeRequest(
                source="planner_fixture",
                raw_capture_ref=to_resource_ref(raw_dir),
                normalized_output_ref=to_resource_ref(output_dir),
            )
        )

    issue_rows = artifacts.read_rows(output_dir / "translation_input_issues.csv")

    assert adapter.translate_selected_called is False
    assert (output_dir / "translation_input_candidates.json").exists()
    assert (output_dir / "translation_input_plan.json").exists()
    assert issue_rows[0]["kind"] == "blocked_unknown_coverage"
    assert not (output_dir / "facts.csv").exists()
    assert not (output_dir / "balance_snapshots.csv").exists()
    assert not (output_dir / "balance_references.csv").exists()


def test_normalization_uses_legacy_translate_fallback_when_planner_is_absent(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="legacy_fixture")
    (raw_dir / "one.csv").write_text(
        "Timestamp,Amount\n2026-03-23 15:47:00 UTC,1\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    adapter = LegacyAdapter("legacy_fixture")
    service = build_registry_backed_normalization_service(
        registry=FakeSourceRegistry(source_adapters=(cast(SourceAdapter, adapter),)),
        artifacts=artifacts,
    )
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="legacy_fixture",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    assert adapter.translate_called is True
    assert response.evidence_set_id == ""
    assert response.evidence_set_ref == ""
    assert response.translation_planner_used is False
    assert response.translation_candidate_count == 0
    assert not (output_dir / "translation_input_plan.json").exists()


def test_normalization_summary_includes_translation_metrics(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="planner_fixture")
    (raw_dir / "older.csv").write_text(
        "Timestamp,Amount\n2026-03-23 15:47:00 UTC,1\n",
        encoding="utf-8",
    )
    (raw_dir / "newer.csv").write_text(
        "Timestamp,Amount\n2026-03-23 15:47:00 UTC,2\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    adapter = PlanningAdapter("planner_fixture", candidate_mode="superseded")
    service = build_registry_backed_normalization_service(
        registry=FakeSourceRegistry(source_adapters=(cast(SourceAdapter, adapter),)),
        artifacts=artifacts,
    )
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="planner_fixture",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )
    summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )

    assert response.translation_candidate_count == 2
    assert response.translation_selected_count == 1
    assert response.translation_superseded_count == 1
    assert response.translation_blocked_count == 0
    assert response.translation_planner_used is True
    assert summary["translation_candidate_count"] == 2
    assert summary["translation_selected_count"] == 1
    assert summary["translation_superseded_count"] == 1
    assert summary["translation_blocked_count"] == 0
    assert summary["translation_planner_used"] is True


def candidate_from_entry(
    entry: FileInventoryEntry,
    *,
    candidate_id: str,
    coverage: TranslationCoverageWindow | None = None,
    freshness: TranslationFreshness | None = None,
) -> TranslationInputCandidate:
    selection_mode = TranslationSelectionMode.REPLACEABLE_RANGE
    return TranslationInputCandidate(
        candidate_id=candidate_id,
        selection_group="planner_fixture",
        family_id="fixture",
        member_relative_paths=(entry.relative_path,),
        selection_mode=selection_mode,
        coverage=coverage or translation_input_coverage_from_inventory_entry(entry),
        freshness=freshness or rank_freshness(1),
        content_fingerprint=translation_input_content_fingerprint(
            member_sha256s=(entry.sha256,),
            family_id="fixture",
            selection_group="planner_fixture",
            selection_mode=selection_mode,
        ),
        comparison_key="planner_fixture",
        description=f"Fixture candidate {candidate_id}",
        comparable=True,
    )


def unknown_coverage() -> TranslationCoverageWindow:
    return TranslationCoverageWindow(
        start_at=None,
        start_precision=None,
        end_at=None,
        end_precision=None,
        mode=TranslationCoverageMode.UNKNOWN,
    )


def rank_freshness(rank: int) -> TranslationFreshness:
    return TranslationFreshness(
        kind=TranslationFreshnessKind.ADAPTER_RANK,
        timestamp=None,
        rank=rank,
    )


def unknown_freshness() -> TranslationFreshness:
    return TranslationFreshness(
        kind=TranslationFreshnessKind.UNKNOWN,
        timestamp=None,
        rank=None,
    )
