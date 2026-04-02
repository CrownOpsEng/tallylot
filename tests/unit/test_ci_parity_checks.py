from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

import tools.run_ci_parity_checks as ci_parity


def test_ci_parity_stops_when_quality_step_fails(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    def fake_run_step(step: ci_parity.ParityStep) -> int:
        assert step.name == "quality"
        return 1

    monkeypatch.setattr(ci_parity, "_run_step", fake_run_step)

    assert ci_parity.main([]) == 1


def test_ci_parity_runs_quality_build_and_verify(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    wheel_path = dist_dir / "tallylot-0.1.0-py3-none-any.whl"
    wheel_path.write_text("stub", encoding="utf-8")

    steps_seen: list[str] = []

    def fake_run_step(step: ci_parity.ParityStep) -> int:
        steps_seen.append(step.name)
        if step.name == "build":
            dist_dir.mkdir(exist_ok=True)
            wheel_path.write_text("rebuilt", encoding="utf-8")
        return 0

    def fake_verify_built_wheel(dist_path: Path) -> tuple[int, str, str]:
        assert dist_path.resolve() == dist_dir.resolve()
        return 0, "", ""

    monkeypatch.setattr(ci_parity, "_run_step", fake_run_step)
    monkeypatch.setattr(ci_parity, "_verify_built_wheel", fake_verify_built_wheel)

    assert ci_parity.main([]) == 0
    assert steps_seen == ["quality", "build"]
