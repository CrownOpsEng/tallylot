"""Row-diff helpers for verification export comparison."""

from __future__ import annotations

from collections import Counter


def row_counter(rows: list[dict[str, str]]) -> Counter[tuple[tuple[str, str], ...]]:
    return Counter(
        tuple(sorted((key, value or "") for key, value in row.items())) for row in rows
    )


def expand_counter_delta(
    counter: Counter[tuple[tuple[str, str], ...]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for signature, count in sorted(counter.items()):
        row = dict(signature)
        for _ in range(count):
            rows.append(row)
    return rows


def subtract_counters(
    current: Counter[tuple[tuple[str, str], ...]],
    previous: Counter[tuple[tuple[str, str], ...]],
) -> Counter[tuple[tuple[str, str], ...]]:
    delta = current.copy()
    delta.subtract(previous)
    return Counter({key: count for key, count in delta.items() if count > 0})
