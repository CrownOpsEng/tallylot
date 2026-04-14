from __future__ import annotations

import argparse
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the latest built wheel.")
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=Path("dist"),
        help="Directory containing built wheels.",
    )
    return parser.parse_args(argv)


def _verify_built_wheel(dist_dir: Path) -> tuple[int, str, str]:
    wheel_paths = sorted(dist_dir.glob("*.whl"))
    if not wheel_paths:
        return 1, "", "no wheel found under dist/"

    with tempfile.TemporaryDirectory(prefix="tallylot-wheel-test-") as tempdir:
        venv_dir = Path(tempdir) / "venv"
        subprocess.run(("python3.12", "-m", "venv", str(venv_dir)), check=True)
        pip_path = venv_dir / "bin" / "pip"
        cli_path = venv_dir / "bin" / "tallylot"
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


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    returncode, stdout, stderr = _verify_built_wheel(args.dist_dir)
    if stdout:
        print(stdout.rstrip())
    if stderr:
        print(stderr.rstrip())
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
