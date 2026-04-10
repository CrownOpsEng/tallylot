from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from .models import ExpectedDifferenceSet, ExpectedMetricDifference

_TOP_LEVEL_FIELDS = frozenset({"sources", "packs"})
_SOURCE_ENTRY_FIELDS = frozenset({"issue_count_delta", "review_count_delta", "reason"})
_PACK_ENTRY_FIELDS = _SOURCE_ENTRY_FIELDS | {"source"}


def load_expected_differences(path: Path | None) -> ExpectedDifferenceSet:
    if path is None:
        return ExpectedDifferenceSet.empty()
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("expected-difference fixture must be a JSON object")
    payload_mapping = cast(Mapping[object, object], payload)
    unknown_fields = set(payload_mapping) - _TOP_LEVEL_FIELDS
    if unknown_fields:
        raise ValueError(
            "expected-difference fixture has unsupported top-level fields: "
            + ", ".join(sorted(str(field) for field in unknown_fields))
        )
    differences: list[ExpectedMetricDifference] = []
    differences.extend(
        _source_differences(
            _optional_mapping(payload_mapping, "sources"),
        )
    )
    differences.extend(
        _pack_differences(
            _optional_mapping(payload_mapping, "packs"),
        )
    )
    return ExpectedDifferenceSet(
        differences_by_source=_merge_differences_by_source(differences)
    )


def _optional_mapping(
    payload: Mapping[object, object],
    key: str,
) -> Mapping[object, object]:
    value = payload.get(key, {})
    if not isinstance(value, Mapping):
        raise ValueError(f"expected-difference fixture field {key!r} must be an object")
    return cast(Mapping[object, object], value)


def _source_differences(
    payload: Mapping[object, object],
) -> tuple[ExpectedMetricDifference, ...]:
    differences: list[ExpectedMetricDifference] = []
    for source, raw_entry in payload.items():
        if not isinstance(source, str) or not source.strip():
            raise ValueError(
                "source expected-difference keys must be non-empty strings"
            )
        entry = _entry_mapping(raw_entry, scope="source", scope_id=source)
        differences.append(
            _difference_from_entry(
                source=source.strip(),
                scope="source",
                scope_id=source.strip(),
                entry=entry,
                allowed_fields=_SOURCE_ENTRY_FIELDS,
            )
        )
    return tuple(differences)


def _pack_differences(
    payload: Mapping[object, object],
) -> tuple[ExpectedMetricDifference, ...]:
    differences: list[ExpectedMetricDifference] = []
    for pack_id, raw_entry in payload.items():
        if not isinstance(pack_id, str) or not pack_id.strip():
            raise ValueError("pack expected-difference keys must be non-empty strings")
        entry = _entry_mapping(raw_entry, scope="pack", scope_id=pack_id)
        source = entry.get("source")
        if not isinstance(source, str) or not source.strip():
            raise ValueError(
                f"pack expected difference {pack_id!r} must declare a source"
            )
        differences.append(
            _difference_from_entry(
                source=source.strip(),
                scope="pack",
                scope_id=pack_id.strip(),
                entry=entry,
                allowed_fields=_PACK_ENTRY_FIELDS,
            )
        )
    return tuple(differences)


def _entry_mapping(
    value: object,
    *,
    scope: str,
    scope_id: str,
) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise ValueError(
            f"{scope} expected difference {scope_id!r} must be a JSON object"
        )
    return cast(Mapping[object, object], value)


def _difference_from_entry(
    *,
    source: str,
    scope: str,
    scope_id: str,
    entry: Mapping[object, object],
    allowed_fields: frozenset[str],
) -> ExpectedMetricDifference:
    unknown_fields = set(entry) - allowed_fields
    if unknown_fields:
        raise ValueError(
            f"{scope} expected difference {scope_id!r} has unsupported fields: "
            + ", ".join(sorted(str(field) for field in unknown_fields))
        )
    issue_count_delta = _int_delta(entry, "issue_count_delta")
    review_count_delta = _int_delta(entry, "review_count_delta")
    if issue_count_delta == 0 and review_count_delta == 0:
        raise ValueError(
            f"{scope} expected difference {scope_id!r} must declare non-zero "
            "issue_count_delta or review_count_delta"
        )
    reason = _reason(entry, scope=scope, scope_id=scope_id)
    return ExpectedMetricDifference(
        source=source,
        issue_count_delta=issue_count_delta,
        review_count_delta=review_count_delta,
        reason=f"{scope} {scope_id}: {reason}",
    )


def _int_delta(entry: Mapping[object, object], field_name: str) -> int:
    value = entry.get(field_name, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"expected-difference field {field_name!r} must be an integer")
    return value


def _reason(
    entry: Mapping[object, object],
    *,
    scope: str,
    scope_id: str,
) -> str:
    value = entry.get("reason")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{scope} expected difference {scope_id!r} must declare a reason"
        )
    return value.strip()


def _merge_differences_by_source(
    differences: list[ExpectedMetricDifference],
) -> dict[str, ExpectedMetricDifference]:
    merged: dict[str, ExpectedMetricDifference] = {}
    for difference in differences:
        existing = merged.get(difference.source)
        if existing is None:
            merged[difference.source] = difference
            continue
        merged[difference.source] = ExpectedMetricDifference(
            source=difference.source,
            issue_count_delta=(
                existing.issue_count_delta + difference.issue_count_delta
            ),
            review_count_delta=(
                existing.review_count_delta + difference.review_count_delta
            ),
            reason=f"{existing.reason}; {difference.reason}",
        )
    return merged
