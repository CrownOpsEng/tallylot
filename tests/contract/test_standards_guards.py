from __future__ import annotations

import ast
import json
import re
import tomllib
from collections import defaultdict
from pathlib import Path

from tallylot.adapters.support.drafts import economic_leg
from tallylot.domain.transactions import EconomicLeg, ProjectionType, TransactionFact

REPO_ROOT = Path(__file__).resolve().parents[2]
CLASSIFICATION_KEYWORDS = frozenset(
    {
        "economic_kind",
        "projection_type",
        "journal_intent",
        "tax_treatment_code",
    }
)


def _module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(root.rglob("*.py")))


def _is_named_call(node: ast.expr, name: str) -> bool:
    if isinstance(node, ast.Name):
        return node.id == name
    if isinstance(node, ast.Attribute):
        return node.attr == name
    return False


def test_repo_has_no_type_ignore_comments() -> None:
    python_files = (
        REPO_ROOT / "conftest.py",
        *_python_files(REPO_ROOT / "src"),
        *_python_files(REPO_ROOT / "tests"),
        *_python_files(REPO_ROOT / "tools"),
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

    for path in _python_files(application_root):
        module = _module(path)
        for node in ast.walk(module):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                assert not (
                    node.module == "tallylot.infrastructure" or node.module.startswith("tallylot.infrastructure.")
                ), f"{path} imports infrastructure from the application layer"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not (
                        alias.name == "tallylot.infrastructure" or alias.name.startswith("tallylot.infrastructure.")
                    ), f"{path} imports infrastructure from the application layer"


def test_transaction_fact_category_bridge_is_removed() -> None:
    assert not hasattr(TransactionFact, "category")


def test_transaction_fact_single_leg_compatibility_helpers_are_removed() -> None:
    for attribute in (
        "asset_in",
        "amount_in",
        "asset_out",
        "amount_out",
        "fee_asset",
        "fee_amount",
        "fee_legs",
    ):
        assert not hasattr(TransactionFact, attribute)


def test_economic_leg_fee_specific_helper_and_flag_are_removed() -> None:
    assert not hasattr(EconomicLeg, "is_fee")
    assert economic_leg.__name__ != "fee_leg"


def test_repo_does_not_reference_fact_category_attribute() -> None:
    guarded_roots = (
        REPO_ROOT / "src" / "tallylot" / "adapters",
        REPO_ROOT / "src" / "tallylot" / "application" / "outputs",
        REPO_ROOT / "src" / "tallylot" / "infrastructure" / "storage",
        REPO_ROOT / "src" / "tallylot" / "adapters" / "support",
        REPO_ROOT / "tests" / "unit" / "domain",
        REPO_ROOT / "tests" / "unit" / "application" / "outputs",
        REPO_ROOT / "tests" / "contract",
    )

    for root in guarded_roots:
        for path in _python_files(root):
            for node in ast.walk(_module(path)):
                if isinstance(node, ast.Attribute):
                    assert node.attr != "category", f"{path} references removed fact category attribute"


def test_repo_does_not_reference_removed_single_leg_fact_attributes() -> None:
    guarded_roots = (
        REPO_ROOT / "src" / "tallylot",
        REPO_ROOT / "tests",
    )
    forbidden_attributes = {
        "asset_in",
        "amount_in",
        "asset_out",
        "amount_out",
        "fee_asset",
        "fee_amount",
        "fee_legs",
        "is_fee",
    }

    for root in guarded_roots:
        for path in _python_files(root):
            for node in ast.walk(_module(path)):
                if isinstance(node, ast.Attribute):
                    assert node.attr not in forbidden_attributes, (
                        f"{path} references removed single-leg fact attribute {node.attr}"
                    )


def test_source_adapters_do_not_pass_string_classification_values() -> None:
    adapters_root = REPO_ROOT / "src" / "tallylot" / "adapters" / "sources"

    for path in _python_files(adapters_root):
        for node in ast.walk(_module(path)):
            if not isinstance(node, ast.Call):
                continue
            if not _is_named_call(node.func, "classification"):
                continue
            for keyword in node.keywords:
                if keyword.arg not in CLASSIFICATION_KEYWORDS:
                    continue
                if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    raise AssertionError(
                        f"{path} passes string classification value {keyword.arg}={keyword.value.value!r} "
                        "through shared draft helpers"
                    )


def test_projection_type_runtime_values_remain_machine_oriented() -> None:
    assert ProjectionType.TRADE.value == "trade"
    assert ProjectionType.DEPOSIT.value == "deposit"
    assert ProjectionType.WITHDRAWAL.value == "withdrawal"


def test_balance_evidence_has_single_production_owner() -> None:
    occurrences = 0
    for path in _python_files(REPO_ROOT / "src" / "tallylot"):
        text = path.read_text(encoding="utf-8")
        occurrences += text.count("class BalanceEvidence")
    assert occurrences == 1


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
