from __future__ import annotations

import argparse

from pytest import CaptureFixture, MonkeyPatch

import tools.report_coverage_hotspots as coverage_hotspots


def _sample_coverage_payload() -> dict[str, object]:
    return {
        "files": {
            "src/tallylot/interfaces/cli/source.py": {
                "summary": {
                    "percent_covered": 40.0,
                    "missing_lines": 12,
                    "missing_branches": 6,
                    "num_branches": 8,
                }
            },
            "src/tallylot/application/normalization/normalize_source.py": {
                "summary": {
                    "percent_covered": 55.0,
                    "missing_lines": 18,
                    "missing_branches": 9,
                    "num_branches": 12,
                }
            },
            "src/tallylot/domain/transactions/models.py": {
                "summary": {
                    "percent_covered": 72.0,
                    "missing_lines": 7,
                    "missing_branches": 2,
                    "num_branches": 10,
                }
            },
            "src/tallylot/adapters/sources/platforms/binance/tests/test_adapter.py": {
                "summary": {
                    "percent_covered": 0.0,
                    "missing_lines": 100,
                    "missing_branches": 0,
                    "num_branches": 0,
                }
            },
            "tests/unit/test_quality_gates.py": {
                "summary": {
                    "percent_covered": 0.0,
                    "missing_lines": 40,
                    "missing_branches": 0,
                    "num_branches": 0,
                }
            },
        },
        "totals": {"percent_covered": 68.0},
    }


def test_hotspot_report_sorts_sections_stably() -> None:
    report = coverage_hotspots._hotspot_report(
        _sample_coverage_payload(),
        changed_files=(),
        top=2,
    )

    assert [module.path for module in report.lowest_covered_modules] == [
        "src/tallylot/interfaces/cli/source.py",
        "src/tallylot/application/normalization/normalize_source.py",
    ]
    assert [module.path for module in report.highest_uncovered_branch_modules] == [
        "src/tallylot/application/normalization/normalize_source.py",
        "src/tallylot/interfaces/cli/source.py",
    ]


def test_hotspot_report_filters_changed_production_modules() -> None:
    report = coverage_hotspots._hotspot_report(
        _sample_coverage_payload(),
        changed_files=(
            "src/tallylot/domain/transactions/models.py",
            "tests/unit/test_quality_gates.py",
            "src/tallylot/interfaces/cli/source.py",
        ),
        top=5,
    )

    assert [module.path for module in report.changed_modules_below_average] == [
        "src/tallylot/interfaces/cli/source.py"
    ]


def test_hotspot_report_omits_non_production_files() -> None:
    modules = coverage_hotspots._module_coverages(_sample_coverage_payload())

    assert [module.path for module in modules] == [
        "src/tallylot/interfaces/cli/source.py",
        "src/tallylot/application/normalization/normalize_source.py",
        "src/tallylot/domain/transactions/models.py",
    ]


def test_hotspot_report_prints_readable_empty_sections(
    capsys: CaptureFixture[str],
) -> None:
    report = coverage_hotspots.CoverageHotspots(
        repo_average_coverage=90.0,
        lowest_covered_modules=(),
        highest_uncovered_branch_modules=(),
        changed_modules_below_average=(),
    )

    coverage_hotspots._print_report(report)

    output = capsys.readouterr().out
    assert "lowest-covered production modules:" in output
    assert "  - none" in output


def test_hotspot_report_requires_full_diff_override_pair(
    capsys: CaptureFixture[str],
) -> None:
    assert coverage_hotspots.main(["--base-sha", "abc123"]) == 2
    assert "provide both --base-sha and --head-sha" in capsys.readouterr().out


def test_hotspot_report_handles_missing_coverage_data(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    def fake_resolved_changed_files(args: argparse.Namespace) -> tuple[str, ...]:
        del args
        return ()

    monkeypatch.setattr(coverage_hotspots, "_load_coverage_payload", lambda: None)
    monkeypatch.setattr(
        coverage_hotspots,
        "_resolved_changed_files",
        fake_resolved_changed_files,
    )

    assert coverage_hotspots.main([]) == 0
    assert "no coverage data found" in capsys.readouterr().out
