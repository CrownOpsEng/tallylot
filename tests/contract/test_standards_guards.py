from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_repo_has_no_type_ignore_comments() -> None:
    python_files = (
        REPO_ROOT / "conftest.py",
        *sorted((REPO_ROOT / "src").rglob("*.py")),
        *sorted((REPO_ROOT / "tests").rglob("*.py")),
        *sorted((REPO_ROOT / "tools").rglob("*.py")),
    )
    forbidden = ("type:" + " ignore", "pyright:" + " ignore")

    for path in python_files:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} contains forbidden typing bypass {needle!r}"


def test_markdownlint_only_disables_md013() -> None:
    config = json.loads((REPO_ROOT / ".markdownlint.json").read_text(encoding="utf-8"))
    assert config == {"default": True, "MD013": False}


def test_module_size_policy_remains_aligned() -> None:
    pylint_text = (REPO_ROOT / ".pylintrc").read_text(encoding="utf-8")
    standards_text = (REPO_ROOT / "docs/architecture/engineering-standards.md").read_text(encoding="utf-8")

    assert "max-module-lines = 450" in pylint_text
    assert re.search(r"Refactor before extending beyond 300 lines", standards_text) is not None
    assert re.search(r"Treat `300` lines as the official repo refactor limit", standards_text) is not None
    assert re.search(r"Treat `450` lines as the hard-stop lint ceiling", standards_text) is not None


def test_src_does_not_accumulate_flat_same_prefix_clusters() -> None:
    source_root = REPO_ROOT / "src" / "crypto_reconciliation"

    for directory in sorted({path.parent for path in source_root.rglob("*.py")}):
        prefix_groups: dict[str, list[str]] = defaultdict(list)
        for path in sorted(directory.glob("*.py")):
            if path.name == "__init__.py":
                continue
            parts = path.stem.split("_")
            if len(parts) < 2:
                continue
            prefix_groups["_".join(parts[:2])].append(path.name)
        offenders = {prefix: names for prefix, names in prefix_groups.items() if len(names) > 3}
        assert not offenders, f"{directory} has flat same-prefix clusters that should be packaged: {offenders}"


def test_retired_bucket_directories_do_not_exist() -> None:
    src_root = REPO_ROOT / "src" / "crypto_reconciliation"

    assert not (src_root / "application" / "services").exists()
    assert not (src_root / "application" / "models").exists()
    assert not (src_root / "domain" / "models").exists()
    assert not (src_root / "ports" / "adapters.py").exists()
    assert not (src_root / "ports" / "storage.py").exists()
    assert not (src_root / "ports" / "output_workflows.py").exists()


def test_oracle_code_is_not_in_production_package() -> None:
    src_root = REPO_ROOT / "src" / "crypto_reconciliation"
    forbidden = (
        src_root / "application" / "oracle_review",
        src_root / "adapters" / "oracles",
    )
    for path in forbidden:
        assert not path.exists()

    for path in sorted(src_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8").lower()
        assert "oracle review" not in text
        assert "baseline validation" not in text
        assert "verification compare" not in text


def test_typecheck_configs_remain_strict() -> None:
    mypy_text = (REPO_ROOT / "mypy.ini").read_text(encoding="utf-8")
    pyright_config = json.loads((REPO_ROOT / "pyrightconfig.json").read_text(encoding="utf-8"))

    assert "strict = true" in mypy_text
    assert "warn_unused_ignores = true" in mypy_text
    assert pyright_config["typeCheckingMode"] == "strict"
    assert pyright_config["reportUnnecessaryTypeIgnoreComment"] is True
