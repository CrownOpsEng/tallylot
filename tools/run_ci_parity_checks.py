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
class _ParityStep:
    name: str
    command: tuple[str, ...]


def _git_stdout(*args: str) -> str:
    result = subprocess.run(
        ("git", *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _default_branch_ref() -> str:
    try:
        return _git_stdout("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    except subprocess.CalledProcessError:
        return "origin/main"


def _commit_message_range() -> str:
    default_branch = _default_branch_ref()
    try:
        merge_base = _git_stdout("merge-base", "HEAD", default_branch)
    except subprocess.CalledProcessError:
        return "HEAD^!"

    head_sha = _git_stdout("rev-parse", "HEAD")
    if merge_base == head_sha:
        return "HEAD^!"
    return f"{merge_base}..{head_sha}"


def _pr_validation_shas() -> tuple[str, str]:
    default_branch = _default_branch_ref()
    try:
        base_sha = _git_stdout("merge-base", "HEAD", default_branch)
    except subprocess.CalledProcessError:
        return _git_stdout("rev-parse", "HEAD^"), _git_stdout("rev-parse", "HEAD")
    return base_sha, _git_stdout("rev-parse", "HEAD")


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local checks that mirror the GitHub Actions CI workflow.")
    parser.add_argument(
        "--include-commit-messages",
        action="store_true",
        help="Also validate the current branch commit-message range before running quality and build checks.",
    )
    parser.add_argument(
        "--pr-title",
        help="Validate pull request metadata for the current branch using this PR title.",
    )
    parser.add_argument(
        "--pr-body-file",
        help="Path to a file containing the pull request body to validate for the current branch.",
    )
    return parser


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


def _run_step(step: _ParityStep) -> int:
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
    args = _parse_args(argv)
    if (args.pr_title is None) != (args.pr_body_file is None):
        print("provide both --pr-title and --pr-body-file when validating PR metadata", flush=True)
        return 2

    steps: list[_ParityStep] = []
    if args.include_commit_messages:
        steps.append(
            _ParityStep(
                name="commit-messages",
                command=(
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "tools.validate_commit_message",
                    "--rev-range",
                    _commit_message_range(),
                ),
            )
        )
    if args.pr_title is not None and args.pr_body_file is not None:
        base_sha, head_sha = _pr_validation_shas()
        pr_body = Path(args.pr_body_file).read_text(encoding="utf-8")
        steps.append(
            _ParityStep(
                name="pr-metadata",
                command=(
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "tools.validate_pr_metadata",
                    "--title",
                    args.pr_title,
                    "--body",
                    pr_body,
                    "--base-sha",
                    base_sha,
                    "--head-sha",
                    head_sha,
                ),
            )
        )
    steps.append(
        _ParityStep(
            name="quality",
            command=("uv", "run", "python", "-m", "tools.run_quality_gates", "--full-tests"),
        )
    )

    for step in steps:
        if _run_step(step) != 0:
            return 1

    dist_dir = Path("dist")
    shutil.rmtree(dist_dir, ignore_errors=True)
    build_status = _run_step(_ParityStep(name="build", command=("uv", "build")))
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
