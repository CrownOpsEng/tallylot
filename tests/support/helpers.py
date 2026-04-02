from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "06_scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def read_dict_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def run_script(
    script_name: str,
    *args: str,
    cwd: Path | None = None,
    scripts_dir: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    script = (scripts_dir or SCRIPTS_DIR) / script_name
    return subprocess.run(
        [sys.executable, str(script), *args],
        check=check,
        capture_output=True,
        text=True,
        cwd=cwd or REPO_ROOT,
    )


def copy_script_to_repo(script_name: str, repo_root: Path) -> Path:
    destination = repo_root / "06_scripts" / script_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCRIPTS_DIR / script_name, destination)
    return destination
