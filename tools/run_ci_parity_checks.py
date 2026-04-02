from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.uv_environment import repo_uv_environment


@dataclass(frozen=True)
class ParityStep:
    name: str
    command: tuple[str, ...]


def _build_argument_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description="Run local checks that mirror the GitHub Actions CI workflow.")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _build_argument_parser().parse_args(argv)


def _verify_built_wheel(dist_dir: Path) -> tuple[int, str, str]:
    wheel_paths = sorted(dist_dir.glob("*.whl"))
    if not wheel_paths:
        return 1, "", "no wheel found under dist/"

    with tempfile.TemporaryDirectory(prefix="tallylot-wheel-test-") as tempdir:
        venv_dir = Path(tempdir) / "venv"
        subprocess.run(("python3.12", "-m", "venv", str(venv_dir)), check=True)
        pip_path = venv_dir / "bin/pip"
        cli_path = venv_dir / "bin/tallylot"
        install_result = subprocess.run(
            (str(pip_path), "install", str(wheel_paths[-1])),
            capture_output=True,
            text=True,
            check=False,
        )
        if install_result.returncode != 0:
            return install_result.returncode, install_result.stdout, install_result.stderr

        verify_result = subprocess.run(
            (str(cli_path), "--help"),
            capture_output=True,
            text=True,
            check=False,
        )
        return verify_result.returncode, verify_result.stdout, verify_result.stderr


def _run_step(step: ParityStep) -> int:
    started = time.perf_counter()
    result = subprocess.run(
        step.command,
        capture_output=True,
        text=True,
        check=False,
        env=repo_uv_environment(),
    )
    elapsed = time.perf_counter() - started
    print(f"[{step.name}] exit={result.returncode} elapsed={elapsed:.2f}s")
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    _parse_args(argv)

    steps = (
        ParityStep(
            name="quality",
            command=("uv", "run", "python", "-m", "tools.run_quality_gates", "--full-tests"),
        ),
    )

    for step in steps:
        if _run_step(step) != 0:
            return 1

    dist_dir = Path("dist")
    shutil.rmtree(dist_dir, ignore_errors=True)
    build_status = _run_step(ParityStep(name="build", command=("uv", "build")))
    if build_status != 0:
        return build_status

    started = time.perf_counter()
    verify_code, stdout, stderr = _verify_built_wheel(dist_dir)
    elapsed = time.perf_counter() - started
    print(f"[verify-wheel] exit={verify_code} elapsed={elapsed:.2f}s")
    if stdout:
        print(stdout.rstrip())
    if stderr:
        print(stderr.rstrip())
    return verify_code


if __name__ == "__main__":
    raise SystemExit(main())
