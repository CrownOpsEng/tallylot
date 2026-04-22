from __future__ import annotations

from datetime import UTC, datetime

from tallylot.application.normalization.translation_inputs import (
    plan_translation_inputs,
)
from tallylot.domain.temporal import TemporalPrecision
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile
from tallylot.ports.translation_inputs import (
    TranslationCoverageMode,
    TranslationCoverageWindow,
    TranslationFreshness,
    TranslationFreshnessKind,
    TranslationInputCandidate,
    TranslationSelectionMode,
    translation_input_content_fingerprint,
)
from tests.support.services import build_source_profile


def test_plan_translation_inputs_selects_single_candidate() -> None:
    entry = inventory_entry("single.csv", "sha-single")
    result = plan_translation_inputs(
        profile=profile_for(entry),
        candidates=(
            candidate(
                candidate_id="single",
                entry=entry,
                coverage=unknown_coverage(),
                freshness=unknown_freshness(),
            ),
        ),
    )

    assert result.plan.selected_candidate_ids == ("single",)
    assert result.plan.blocked is False
    assert decision_statuses(result) == {"single": "selected"}


def test_plan_translation_inputs_selects_disjoint_appendable_ranges() -> None:
    first = inventory_entry("2021.csv", "sha-2021")
    second = inventory_entry("2022.csv", "sha-2022")
    result = plan_translation_inputs(
        profile=profile_for(first, second),
        candidates=(
            candidate(
                candidate_id="2022",
                entry=second,
                selection_mode=TranslationSelectionMode.APPENDABLE_RANGE,
                coverage=bounded("2022-01-01 00:00:00", "2022-12-31 23:59:59"),
                freshness=export_freshness("2023-01-02 00:00:00"),
            ),
            candidate(
                candidate_id="2021",
                entry=first,
                selection_mode=TranslationSelectionMode.APPENDABLE_RANGE,
                coverage=bounded("2021-01-01 00:00:00", "2021-12-31 23:59:59"),
                freshness=export_freshness("2022-01-02 00:00:00"),
            ),
        ),
    )

    assert result.plan.selected_candidate_ids == ("2021", "2022")
    assert result.plan.blocked is False
    assert decision_statuses(result) == {"2021": "selected", "2022": "selected"}


def test_plan_translation_inputs_supersedes_older_identical_duplicate() -> None:
    older = inventory_entry("older.csv", "shared-sha")
    newer = inventory_entry("newer.csv", "shared-sha")
    result = plan_translation_inputs(
        profile=profile_for(older, newer),
        candidates=(
            candidate(
                candidate_id="older",
                entry=older,
                coverage=bounded("2021-01-01 00:00:00", "2021-12-31 23:59:59"),
                freshness=export_freshness("2022-01-01 00:00:00"),
            ),
            candidate(
                candidate_id="newer",
                entry=newer,
                coverage=bounded("2021-01-01 00:00:00", "2021-12-31 23:59:59"),
                freshness=export_freshness("2023-01-01 00:00:00"),
            ),
        ),
    )

    assert result.plan.selected_candidate_ids == ("newer",)
    assert decision_statuses(result) == {
        "newer": "selected",
        "older": "superseded_identical",
    }


def test_plan_translation_inputs_supersedes_replaced_duplicate_for_replaceable_range() -> (
    None
):
    older = inventory_entry("older.csv", "sha-old")
    newer = inventory_entry("newer.csv", "sha-new")
    result = plan_translation_inputs(
        profile=profile_for(older, newer),
        candidates=(
            candidate(
                candidate_id="older",
                entry=older,
                coverage=bounded("2021-01-01 00:00:00", "2021-12-31 23:59:59"),
                freshness=export_freshness("2022-01-01 00:00:00"),
            ),
            candidate(
                candidate_id="newer",
                entry=newer,
                coverage=bounded("2021-01-01 00:00:00", "2021-12-31 23:59:59"),
                freshness=export_freshness("2023-01-01 00:00:00"),
            ),
        ),
    )

    assert result.plan.selected_candidate_ids == ("newer",)
    assert decision_statuses(result) == {
        "newer": "selected",
        "older": "superseded_replaced",
    }


def test_plan_translation_inputs_blocks_replaced_duplicate_for_appendable_range() -> (
    None
):
    older = inventory_entry("older.csv", "sha-old")
    newer = inventory_entry("newer.csv", "sha-new")
    result = plan_translation_inputs(
        profile=profile_for(older, newer),
        candidates=(
            candidate(
                candidate_id="older",
                entry=older,
                selection_mode=TranslationSelectionMode.APPENDABLE_RANGE,
                coverage=bounded("2021-01-01 00:00:00", "2021-12-31 23:59:59"),
                freshness=export_freshness("2022-01-01 00:00:00"),
            ),
            candidate(
                candidate_id="newer",
                entry=newer,
                selection_mode=TranslationSelectionMode.APPENDABLE_RANGE,
                coverage=bounded("2021-01-01 00:00:00", "2021-12-31 23:59:59"),
                freshness=export_freshness("2023-01-01 00:00:00"),
            ),
        ),
    )

    assert result.plan.blocked is True
    assert decision_statuses(result) == {
        "newer": "blocked_partial_overlap",
        "older": "blocked_partial_overlap",
    }


def test_plan_translation_inputs_supersedes_subset_with_newer_superset() -> None:
    subset = inventory_entry("subset.csv", "sha-subset")
    superset = inventory_entry("superset.csv", "sha-superset")
    result = plan_translation_inputs(
        profile=profile_for(subset, superset),
        candidates=(
            candidate(
                candidate_id="subset",
                entry=subset,
                coverage=bounded("2021-01-01 00:00:00", "2021-12-31 23:59:59"),
                freshness=export_freshness("2022-01-01 00:00:00"),
            ),
            candidate(
                candidate_id="superset",
                entry=superset,
                coverage=bounded("2021-01-01 00:00:00", "2026-03-23 00:00:00"),
                freshness=export_freshness("2026-03-23 00:00:00"),
            ),
        ),
    )

    assert result.plan.selected_candidate_ids == ("superset",)
    assert decision_statuses(result) == {
        "subset": "superseded_replaced",
        "superset": "selected",
    }


def test_plan_translation_inputs_blocks_partial_overlap() -> None:
    first = inventory_entry("first.csv", "sha-first")
    second = inventory_entry("second.csv", "sha-second")
    result = plan_translation_inputs(
        profile=profile_for(first, second),
        candidates=(
            candidate(
                candidate_id="first",
                entry=first,
                coverage=bounded("2021-01-01 00:00:00", "2021-12-31 23:59:59"),
                freshness=export_freshness("2022-01-01 00:00:00"),
            ),
            candidate(
                candidate_id="second",
                entry=second,
                coverage=bounded("2021-06-01 00:00:00", "2022-05-31 23:59:59"),
                freshness=export_freshness("2023-01-01 00:00:00"),
            ),
        ),
    )

    assert result.plan.blocked is True
    assert decision_statuses(result) == {
        "first": "blocked_partial_overlap",
        "second": "blocked_partial_overlap",
    }


def test_plan_translation_inputs_blocks_unknown_coverage_with_multiple_candidates() -> (
    None
):
    unknown = inventory_entry("unknown.csv", "sha-unknown")
    bounded_entry = inventory_entry("bounded.csv", "sha-bounded")
    result = plan_translation_inputs(
        profile=profile_for(unknown, bounded_entry),
        candidates=(
            candidate(
                candidate_id="unknown",
                entry=unknown,
                coverage=unknown_coverage(),
                freshness=unknown_freshness(),
            ),
            candidate(
                candidate_id="bounded",
                entry=bounded_entry,
                coverage=bounded("2021-01-01 00:00:00", "2021-12-31 23:59:59"),
                freshness=export_freshness("2022-01-01 00:00:00"),
            ),
        ),
    )

    assert result.plan.blocked is True
    assert decision_statuses(result) == {
        "bounded": "blocked_unknown_coverage",
        "unknown": "blocked_unknown_coverage",
    }


def test_plan_translation_inputs_blocks_incomparable_overlapping_candidates() -> None:
    first = inventory_entry("first.csv", "sha-first")
    second = inventory_entry("second.csv", "sha-second")
    result = plan_translation_inputs(
        profile=profile_for(first, second),
        candidates=(
            candidate(
                candidate_id="first",
                entry=first,
                comparable=False,
                coverage=bounded("2021-01-01 00:00:00", "2021-12-31 23:59:59"),
                freshness=export_freshness("2022-01-01 00:00:00"),
            ),
            candidate(
                candidate_id="second",
                entry=second,
                coverage=bounded("2021-01-01 00:00:00", "2026-03-23 00:00:00"),
                freshness=export_freshness("2023-01-01 00:00:00"),
            ),
        ),
    )

    assert result.plan.blocked is True
    assert decision_statuses(result) == {
        "first": "blocked_incomparable_candidates",
        "second": "blocked_incomparable_candidates",
    }


def test_plan_translation_inputs_blocks_exclusive_snapshot_tie() -> None:
    first = inventory_entry("first.csv", "sha-first")
    second = inventory_entry("second.csv", "sha-second")
    result = plan_translation_inputs(
        profile=profile_for(first, second),
        candidates=(
            candidate(
                candidate_id="first",
                entry=first,
                selection_mode=TranslationSelectionMode.EXCLUSIVE_SNAPSHOT,
                coverage=bounded("2026-03-23 00:00:00", "2026-03-23 00:00:00"),
                freshness=export_freshness("2026-03-23 00:00:00"),
            ),
            candidate(
                candidate_id="second",
                entry=second,
                selection_mode=TranslationSelectionMode.EXCLUSIVE_SNAPSHOT,
                coverage=bounded("2026-03-23 00:00:00", "2026-03-23 00:00:00"),
                freshness=export_freshness("2026-03-23 00:00:00"),
            ),
        ),
    )

    assert result.plan.blocked is True
    assert decision_statuses(result) == {
        "first": "blocked_ambiguous_freshness",
        "second": "blocked_ambiguous_freshness",
    }


def test_plan_translation_inputs_keeps_selected_order_stable_across_repeated_runs() -> (
    None
):
    first = inventory_entry("second.csv", "sha-second")
    second = inventory_entry("first.csv", "sha-first")
    third = inventory_entry("third.csv", "sha-third")
    candidates = (
        candidate(
            candidate_id="third",
            entry=third,
            selection_mode=TranslationSelectionMode.APPENDABLE_RANGE,
            coverage=bounded("2023-01-01 00:00:00", "2023-12-31 23:59:59"),
            freshness=export_freshness("2024-01-01 00:00:00"),
        ),
        candidate(
            candidate_id="first",
            entry=second,
            selection_mode=TranslationSelectionMode.APPENDABLE_RANGE,
            coverage=bounded("2021-01-01 00:00:00", "2021-12-31 23:59:59"),
            freshness=export_freshness("2022-01-01 00:00:00"),
        ),
        candidate(
            candidate_id="second",
            entry=first,
            selection_mode=TranslationSelectionMode.APPENDABLE_RANGE,
            coverage=bounded("2022-01-01 00:00:00", "2022-12-31 23:59:59"),
            freshness=export_freshness("2023-01-01 00:00:00"),
        ),
    )
    profile = profile_for(first, second, third)

    first_result = plan_translation_inputs(profile=profile, candidates=candidates)
    second_result = plan_translation_inputs(
        profile=profile, candidates=tuple(reversed(candidates))
    )

    assert first_result.plan.selected_candidate_ids == ("first", "second", "third")
    assert second_result.plan.selected_candidate_ids == ("first", "second", "third")
    assert first_result.plan.decisions == second_result.plan.decisions


def test_material_input_change_changes_translation_candidate_content_fingerprint() -> (
    None
):
    first = translation_input_content_fingerprint(
        member_sha256s=("sha-one", "sha-two"),
        family_id="family",
        selection_group="group",
        selection_mode=TranslationSelectionMode.REPLACEABLE_RANGE,
    )
    second = translation_input_content_fingerprint(
        member_sha256s=("sha-one", "sha-three"),
        family_id="family",
        selection_group="group",
        selection_mode=TranslationSelectionMode.REPLACEABLE_RANGE,
    )

    assert first != second


def test_member_order_change_does_not_change_translation_candidate_content_fingerprint() -> (
    None
):
    first = translation_input_content_fingerprint(
        member_sha256s=("sha-one", "sha-two"),
        family_id="family",
        selection_group="group",
        selection_mode=TranslationSelectionMode.REPLACEABLE_RANGE,
    )
    second = translation_input_content_fingerprint(
        member_sha256s=("sha-two", "sha-one"),
        family_id="family",
        selection_group="group",
        selection_mode=TranslationSelectionMode.REPLACEABLE_RANGE,
    )

    assert first == second


def inventory_entry(relative_path: str, sha256: str) -> FileInventoryEntry:
    return FileInventoryEntry(
        relative_path=relative_path,
        suffix=".csv",
        size_bytes=1,
        sha256=sha256,
        row_count=1,
    )


def profile_for(*entries: FileInventoryEntry) -> SourceProfile:
    return build_source_profile(
        adapter_id="planner_fixture",
        source="planner_fixture",
        file_inventory=entries,
    )


def candidate(
    *,
    candidate_id: str,
    entry: FileInventoryEntry,
    coverage: TranslationCoverageWindow,
    freshness: TranslationFreshness,
    selection_mode: TranslationSelectionMode = TranslationSelectionMode.REPLACEABLE_RANGE,
    selection_group: str = "group",
    comparable: bool = True,
) -> TranslationInputCandidate:
    return TranslationInputCandidate(
        candidate_id=candidate_id,
        selection_group=selection_group,
        family_id="family",
        member_relative_paths=(entry.relative_path,),
        selection_mode=selection_mode,
        coverage=coverage,
        freshness=freshness,
        content_fingerprint=translation_input_content_fingerprint(
            member_sha256s=(entry.sha256,),
            family_id="family",
            selection_group=selection_group,
            selection_mode=selection_mode,
        ),
        comparison_key="comparison",
        description=f"Candidate {candidate_id}",
        comparable=comparable,
    )


def bounded(start_at: str, end_at: str) -> TranslationCoverageWindow:
    return TranslationCoverageWindow(
        start_at=timestamp(start_at),
        start_precision=TemporalPrecision.TIMESTAMP,
        end_at=timestamp(end_at),
        end_precision=TemporalPrecision.TIMESTAMP,
        mode=TranslationCoverageMode.BOUNDED,
    )


def unknown_coverage() -> TranslationCoverageWindow:
    return TranslationCoverageWindow(
        start_at=None,
        start_precision=None,
        end_at=None,
        end_precision=None,
        mode=TranslationCoverageMode.UNKNOWN,
    )


def export_freshness(value: str) -> TranslationFreshness:
    return TranslationFreshness(
        kind=TranslationFreshnessKind.EXPORT_TIMESTAMP,
        timestamp=timestamp(value),
        rank=None,
    )


def unknown_freshness() -> TranslationFreshness:
    return TranslationFreshness(
        kind=TranslationFreshnessKind.UNKNOWN,
        timestamp=None,
        rank=None,
    )


def timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def decision_statuses(result: object) -> dict[str, str]:
    return {
        decision.candidate_id: decision.status
        for decision in getattr(result, "plan").decisions
    }
