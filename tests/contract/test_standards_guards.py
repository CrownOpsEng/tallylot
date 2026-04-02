from __future__ import annotations

import json
import re
import tomllib
from collections import defaultdict
from pathlib import Path

from tallylot.domain.transactions import ProjectionType, TransactionFact

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
    source_root = REPO_ROOT / "src" / "tallylot"

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
    src_root = REPO_ROOT / "src" / "tallylot"

    assert not (src_root / "application" / "services").exists()
    assert not (src_root / "application" / "models").exists()
    assert not (src_root / "domain" / "models").exists()
    assert not (src_root / "ports" / "adapters.py").exists()
    assert not (src_root / "ports" / "storage.py").exists()
    assert not (src_root / "ports" / "output_workflows.py").exists()


def test_oracle_code_is_not_in_production_package() -> None:
    src_root = REPO_ROOT / "src" / "tallylot"
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


def test_future_capability_roots_remain_available_for_next_phase() -> None:
    src_root = REPO_ROOT / "src" / "tallylot"

    required_packages = (
        src_root / "application" / "reconciliation",
        src_root / "application" / "checkpoints",
        src_root / "application" / "accounting",
        src_root / "application" / "tax",
        src_root / "domain" / "transactions",
        src_root / "domain" / "checkpoints",
        src_root / "domain" / "reconciliation",
        src_root / "infrastructure" / "composition",
    )
    required_modules = (
        src_root / "ports" / "facts.py",
        src_root / "ports" / "evidence.py",
        src_root / "ports" / "source_translation.py",
        src_root / "ports" / "source_adapters.py",
        src_root / "ports" / "output_adapters.py",
    )

    for package in required_packages:
        assert package.is_dir(), f"missing future capability package root: {package}"
        assert (package / "__init__.py").exists(), f"missing package marker for {package}"
    for module in required_modules:
        assert module.exists(), f"missing capability boundary module: {module}"


def test_production_packaging_excludes_dev_only_oracle_tooling() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    scripts = pyproject["project"]["scripts"]
    wheel_packages = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]

    assert scripts == {"tallylot": "tallylot.interfaces.cli:app"}
    assert wheel_packages == ["src/tallylot"]
    assert all("tools.oracles" not in target for target in scripts.values())


def test_typecheck_configs_remain_strict() -> None:
    mypy_text = (REPO_ROOT / "mypy.ini").read_text(encoding="utf-8")
    pyright_config = json.loads((REPO_ROOT / "pyrightconfig.json").read_text(encoding="utf-8"))

    assert "strict = true" in mypy_text
    assert "warn_unused_ignores = true" in mypy_text
    assert pyright_config["typeCheckingMode"] == "strict"
    assert pyright_config["reportUnnecessaryTypeIgnoreComment"] is True


def test_application_modules_do_not_import_infrastructure() -> None:
    application_root = REPO_ROOT / "src" / "tallylot" / "application"

    for path in sorted(application_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert re.search(r"(^|\n)(from|import)\s+tallylot\.infrastructure\b", text) is None, (
            f"{path} imports infrastructure from the application layer"
        )


def test_transaction_fact_category_bridge_is_removed() -> None:
    assert not hasattr(TransactionFact, "category")


def test_repo_does_not_reference_fact_category_attribute() -> None:
    guarded_roots = (
        REPO_ROOT / "src" / "tallylot" / "adapters" / "sources",
        REPO_ROOT / "src" / "tallylot" / "adapters" / "support",
        REPO_ROOT / "tests" / "unit" / "domain",
    )

    for root in guarded_roots:
        for path in sorted(root.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            assert re.search(r"\.category\b", text) is None, f"{path} references removed fact category attribute"


def test_source_adapters_do_not_emit_cointracking_projection_labels() -> None:
    adapters_root = REPO_ROOT / "src" / "tallylot" / "adapters" / "sources"
    forbidden_pattern = re.compile(
        r'projection_type\s*=\s*"(Deposit|Trade|Withdrawal|Interest Income|Reward / Bonus|'
        r"Expense \(non taxable\)|Swap \(non taxable\)|Staking|"
        r'Derivatives / Futures Profit|Derivatives / Futures Loss)"'
    )

    for path in sorted(adapters_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert forbidden_pattern.search(text) is None, f"{path} embeds CoinTracking projection labels"


def test_source_adapters_do_not_pass_string_classification_values() -> None:
    adapters_root = REPO_ROOT / "src" / "tallylot" / "adapters" / "sources"
    forbidden_literals = (
        'economic_kind="',
        'projection_type="',
        'journal_intent="',
        'tax_treatment_code="',
    )

    for path in sorted(adapters_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for literal in forbidden_literals:
            assert literal not in text, f"{path} passes string classification values through shared draft helpers"


def test_projection_type_runtime_values_remain_machine_oriented() -> None:
    assert ProjectionType.TRADE.value == "trade"
    assert ProjectionType.DEPOSIT.value == "deposit"
    assert ProjectionType.WITHDRAWAL.value == "withdrawal"


def test_transaction_classification_matrix_describes_runtime_projection_values() -> None:
    matrix_text = (REPO_ROOT / "docs" / "architecture" / "transaction-classification-matrix.md").read_text(
        encoding="utf-8"
    )

    assert "| `trade` | `trade` | `spot_trade` | `capital_exchange` | `asset_exchange` |" in matrix_text
    assert "| `deposit` | `deposit` | `asset_deposit` | `non_taxable_transfer_in` | `funding_inflow` |" in matrix_text
    assert (
        "| `withdrawal` | `withdrawal` | `asset_withdrawal` | `non_taxable_transfer_out` | `funding_outflow` |"
        in matrix_text
    )
    assert "enum members such as `ProjectionType.TRADE`" in matrix_text
    assert "stored/runtime values such as `trade`" in matrix_text
    assert "renderer labels such as `Trade`" in matrix_text
