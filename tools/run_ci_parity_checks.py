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


QUALITY_STEP_CHOICES = ("quality", "lint-format", "types", "pylint", "tests")
PARITY_STEP_CHOICES = (
    "commit-messages",
    "pr-metadata",
    *QUALITY_STEP_CHOICES,
    "build",
    "verify-wheel",
)
_QUALITY_SUBSTEP_NAMES = frozenset({"lint-format", "types", "pylint", "tests"})


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
    parser = argparse.ArgumentParser(
        description="Run local checks that mirror the GitHub Actions CI workflow."
    )
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
    parser.add_argument(
        "--step",
        action="append",
        choices=PARITY_STEP_CHOICES,
        help="Run only the named parity step. May be passed multiple times.",
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
            return (
                install_result.returncode,
                install_result.stdout,
                install_result.stderr,
            )

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


def _quality_command(*gate_names: str, full_tests: bool = False) -> tuple[str, ...]:
    command = ["uv", "run", "python", "-m", "tools.run_quality_gates"]
    if full_tests:
        command.append("--full-tests")
    for gate_name in gate_names:
        command.extend(("--gate", gate_name))
    return tuple(command)


def _selected_steps(args: argparse.Namespace) -> tuple[str, ...] | None:
    if args.step is None:
        return None
    selected_steps = tuple(args.step)
    if "quality" in selected_steps and any(
        step_name in _QUALITY_SUBSTEP_NAMES for step_name in selected_steps
    ):
        raise ValueError(
            "do not combine `quality` with `lint-format`, `types`, `pylint`, or `tests`"
        )
    return selected_steps


def _commit_message_step() -> _ParityStep:
    return _ParityStep(
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


def _pr_metadata_step(pr_title: str, pr_body_file: str) -> _ParityStep:
    base_sha, head_sha = _pr_validation_shas()
    pr_body = Path(pr_body_file).read_text(encoding="utf-8")
    return _ParityStep(
        name="pr-metadata",
        command=(
            "uv",
            "run",
            "python",
            "-m",
            "tools.validate_pr_metadata",
            "--title",
            pr_title,
            "--body",
            pr_body,
            "--base-sha",
            base_sha,
            "--head-sha",
            head_sha,
        ),
    )


def _quality_parity_step(step_name: str) -> _ParityStep | None:
    command_by_step_name = {
        "quality": _quality_command(full_tests=True),
        "lint-format": _quality_command("markdownlint", "actionlint", "ruff"),
        "types": _quality_command("mypy", "pyright"),
        "pylint": _quality_command("pylint"),
        "tests": _quality_command("pytest", full_tests=True),
        "build": ("uv", "build"),
        "verify-wheel": (),
    }
    if step_name not in command_by_step_name:
        raise ValueError(f"unsupported parity step: {step_name}")
    command = command_by_step_name[step_name]
    if not command:
        return None
    return _ParityStep(name=step_name, command=command)


def _parity_steps(
    *,
    include_commit_messages: bool,
    pr_title: str | None,
    pr_body_file: str | None,
    selected_steps: tuple[str, ...] | None,
) -> tuple[_ParityStep, ...]:
    base_steps = (
        ("quality", "build", "verify-wheel")
        if selected_steps is None
        else selected_steps
    )

    steps: list[_ParityStep] = []
    if include_commit_messages:
        steps.append(_commit_message_step())
    if pr_title is not None and pr_body_file is not None:
        steps.append(_pr_metadata_step(pr_title, pr_body_file))

    for step_name in base_steps:
        if step_name == "commit-messages":
            if include_commit_messages:
                continue
            steps.append(_commit_message_step())
            continue
        if step_name == "pr-metadata":
            if pr_title is None or pr_body_file is None:
                raise ValueError(
                    "provide both --pr-title and --pr-body-file when running the `pr-metadata` step"
                )
            continue
        parity_step = _quality_parity_step(step_name)
        if parity_step is None:
            continue
        steps.append(parity_step)
    if "verify-wheel" in base_steps:
        steps.append(_ParityStep(name="verify-wheel", command=()))
    return tuple(steps)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if (args.pr_title is None) != (args.pr_body_file is None):
        print(
            "provide both --pr-title and --pr-body-file when validating PR metadata",
            flush=True,
        )
        return 2
    try:
        selected_steps = _selected_steps(args)
        steps = _parity_steps(
            include_commit_messages=args.include_commit_messages,
            pr_title=args.pr_title,
            pr_body_file=args.pr_body_file,
            selected_steps=selected_steps,
        )
    except ValueError as error:
        print(str(error), flush=True)
        return 2

    dist_dir = Path("dist")
    for step in steps:
        if step.name == "build":
            shutil.rmtree(dist_dir, ignore_errors=True)
        if step.name == "verify-wheel":
            started = time.perf_counter()
            verify_code, stdout, stderr = _verify_built_wheel(dist_dir)
            elapsed = time.perf_counter() - started
            print(f"[verify-wheel] exit={verify_code} elapsed={elapsed:.2f}s")
            if stdout:
                print(stdout.rstrip())
            if stderr:
                print(stderr.rstrip())
            if verify_code != 0:
                return verify_code
            continue
        if _run_step(step) != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
