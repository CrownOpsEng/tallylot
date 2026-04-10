from __future__ import annotations

import os

DEFAULT_FAST_PYTEST_WORKERS = 4
FAST_PYTEST_WORKERS_ENV = "TALLYLOT_FAST_PYTEST_WORKERS"
FAST_PYTEST_MARKER_EXPRESSION = "unit and not slow"


def resolve_fast_pytest_workers(workers: int | None = None) -> int:
    if workers is not None:
        resolved_workers = workers
    else:
        raw_workers = os.environ.get(FAST_PYTEST_WORKERS_ENV)
        resolved_workers = (
            DEFAULT_FAST_PYTEST_WORKERS if raw_workers is None else int(raw_workers)
        )
    if resolved_workers < 0:
        raise ValueError("fast pytest worker count must be zero or greater")
    return resolved_workers


def build_fast_pytest_command(*, workers: int | None = None) -> tuple[str, ...]:
    resolved_workers = resolve_fast_pytest_workers(workers)
    command = ["uv", "run", "pytest"]
    if resolved_workers > 0:
        command.extend(("-n", str(resolved_workers)))
    command.extend(("-m", FAST_PYTEST_MARKER_EXPRESSION, "--no-cov", "-q"))
    return tuple(command)
