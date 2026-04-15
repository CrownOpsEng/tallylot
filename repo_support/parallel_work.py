from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar
from collections.abc import Callable, Sequence

ItemT = TypeVar("ItemT")
ResultT = TypeVar("ResultT")


def run_parallel_batch(
    items: Sequence[ItemT],
    *,
    runner: Callable[[ItemT], ResultT],
) -> tuple[ResultT, ...]:
    if len(items) <= 1:
        return tuple(runner(item) for item in items)

    with ThreadPoolExecutor(max_workers=len(items)) as executor:
        futures = [executor.submit(runner, item) for item in items]
        return tuple(future.result() for future in futures)
