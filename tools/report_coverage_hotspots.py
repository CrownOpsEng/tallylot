from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

from repo_support.paths import repo_root
from repo_support.review_verification import changed_paths
from repo_support.uv_environment import repo_uv_environment


@dataclass(frozen=True)
class ModuleCoverage:
    path: str
    percent_covered: float
    missing_lines: int
    missing_branches: int
    num_branches: int


@dataclass(frozen=True)
class CoverageHotspots:
    repo_average_coverage: float
    lowest_covered_modules: tuple[ModuleCoverage, ...]
    highest_uncovered_branch_modules: tuple[ModuleCoverage, ...]
    changed_modules_below_average: tuple[ModuleCoverage, ...]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report coverage hotspots from the latest full-suite coverage data."
    )
    parser.add_argument(
        "--changed-file",
        action="append",
        help="Repo-relative changed production file to highlight. May be passed multiple times.",
    )
    parser.add_argument(
        "--base-sha", help="Base commit SHA for inferring changed files."
    )
    parser.add_argument(
        "--head-sha", help="Head commit SHA for inferring changed files."
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Maximum number of modules to show in each hotspot section.",
    )
    return parser.parse_args(argv)


def _is_production_module(path: str) -> bool:
    pure_path = PurePosixPath(path)
    return pure_path.parts[:2] == ("src", "tallylot") and "tests" not in pure_path.parts


def _normalize_changed_files(paths: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for path in paths:
        normalized_path = PurePosixPath(path).as_posix()
        if _is_production_module(normalized_path):
            normalized.append(normalized_path)
    return tuple(dict.fromkeys(normalized))


def _resolved_changed_files(args: argparse.Namespace) -> tuple[str, ...]:
    if (args.base_sha is None) != (args.head_sha is None):
        raise ValueError(
            "provide both --base-sha and --head-sha when overriding the diff range"
        )
    if args.changed_file:
        return _normalize_changed_files(args.changed_file)
    if args.base_sha is not None and args.head_sha is not None:
        return _normalize_changed_files(
            changed_paths(base_sha=args.base_sha, head_sha=args.head_sha)
        )
    return _normalize_changed_files(changed_paths())


def _load_coverage_payload() -> dict[str, object] | None:
    coverage_data_path = repo_root() / ".coverage"
    if not coverage_data_path.exists():
        return None

    with tempfile.TemporaryDirectory(prefix="tallylot-coverage-hotspots-") as temp_dir:
        output_path = Path(temp_dir) / "coverage.json"
        result = subprocess.run(
            ("uv", "run", "coverage", "json", "-o", str(output_path)),
            capture_output=True,
            text=True,
            check=False,
            env=repo_uv_environment(),
        )
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip())
        if not output_path.exists():
            return None
        return cast(
            dict[str, object],
            json.loads(output_path.read_text(encoding="utf-8")),
        )


def _float_value(value: object) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return 0.0


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    return 0


def _module_coverages(
    coverage_payload: dict[str, object],
) -> tuple[ModuleCoverage, ...]:
    files_object = coverage_payload.get("files")
    if not isinstance(files_object, Mapping):
        return ()
    files = cast(Mapping[object, object], files_object)

    modules: list[ModuleCoverage] = []
    for path_object, file_payload_object in files.items():
        if not isinstance(path_object, str) or not _is_production_module(path_object):
            continue
        if not isinstance(file_payload_object, Mapping):
            continue
        file_payload = cast(Mapping[str, object], file_payload_object)
        summary_object = file_payload.get("summary")
        if not isinstance(summary_object, Mapping):
            continue
        summary = cast(Mapping[str, object], summary_object)
        modules.append(
            ModuleCoverage(
                path=path_object,
                percent_covered=_float_value(summary.get("percent_covered", 0.0)),
                missing_lines=_int_value(summary.get("missing_lines", 0)),
                missing_branches=_int_value(summary.get("missing_branches", 0)),
                num_branches=_int_value(summary.get("num_branches", 0)),
            )
        )
    return tuple(modules)


def _hotspot_report(
    coverage_payload: dict[str, object],
    *,
    changed_files: Iterable[str],
    top: int,
) -> CoverageHotspots:
    modules = _module_coverages(coverage_payload)
    totals_object = coverage_payload.get("totals")
    repo_average_coverage = (
        _float_value(
            cast(Mapping[str, object], totals_object).get("percent_covered", 0.0)
        )
        if isinstance(totals_object, Mapping)
        else 0.0
    )
    normalized_changed_files = set(_normalize_changed_files(changed_files))

    lowest_covered_modules = tuple(
        sorted(
            modules,
            key=lambda module: (
                module.percent_covered,
                -module.missing_lines,
                module.path,
            ),
        )[:top]
    )
    highest_uncovered_branch_modules = tuple(
        sorted(
            (module for module in modules if module.num_branches > 0),
            key=lambda module: (
                -module.missing_branches,
                module.percent_covered,
                module.path,
            ),
        )[:top]
    )
    changed_modules_below_average = tuple(
        sorted(
            (
                module
                for module in modules
                if module.path in normalized_changed_files
                and module.percent_covered < repo_average_coverage
            ),
            key=lambda module: (
                module.percent_covered,
                -module.missing_lines,
                module.path,
            ),
        )[:top]
    )
    return CoverageHotspots(
        repo_average_coverage=repo_average_coverage,
        lowest_covered_modules=lowest_covered_modules,
        highest_uncovered_branch_modules=highest_uncovered_branch_modules,
        changed_modules_below_average=changed_modules_below_average,
    )


def _print_section(
    title: str, modules: Sequence[ModuleCoverage], *, branch_view: bool
) -> None:
    print(title)
    if not modules:
        print("  - none")
        return
    for module in modules:
        branch_summary = (
            f", missing_branches={module.missing_branches}/{module.num_branches}"
            if branch_view
            else ""
        )
        print(
            f"  - {module.path}: coverage={module.percent_covered:.1f}% "
            f"missing_lines={module.missing_lines}{branch_summary}"
        )


def _print_report(report: CoverageHotspots) -> None:
    print(
        f"repo average coverage={report.repo_average_coverage:.1f}%",
        flush=True,
    )
    _print_section(
        "lowest-covered production modules:",
        report.lowest_covered_modules,
        branch_view=False,
    )
    _print_section(
        "highest uncovered-branch production modules:",
        report.highest_uncovered_branch_modules,
        branch_view=True,
    )
    _print_section(
        "changed production modules below repo average:",
        report.changed_modules_below_average,
        branch_view=False,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.top < 1:
        print("--top must be at least 1", flush=True)
        return 2
    try:
        changed_files = _resolved_changed_files(args)
    except ValueError as error:
        print(str(error), flush=True)
        return 2

    coverage_payload = _load_coverage_payload()
    if coverage_payload is None:
        print(
            "no coverage data found; run the full test suite before reporting hotspots"
        )
        return 0

    report = _hotspot_report(
        coverage_payload, changed_files=changed_files, top=args.top
    )
    _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
