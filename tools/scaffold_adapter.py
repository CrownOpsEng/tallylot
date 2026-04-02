from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

from repo_support.paths import repo_root as active_repo_root


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scaffold a package-style adapter with colocated tests and fixtures.",
    )
    parser.add_argument("kind", choices=("source", "output"))
    parser.add_argument(
        "module_name",
        help=(
            "Adapter package name. Source adapters must include a category namespace, "
            "for example 'platforms/example_exchange' or 'wallets/example_wallet'."
        ),
    )
    parser.add_argument("display_name")
    parser.add_argument("--description", default="")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing scaffold files under the adapter package.",
    )
    return parser


def _camel_case(value: str) -> str:
    parts = [part for part in value.replace("-", "_").split("_") if part]
    return "".join(part[:1].upper() + part[1:] for part in parts)


@dataclass(frozen=True)
class _AdapterScaffoldSpec:
    repo_root: Path
    kind: str
    module_name: str
    display_name: str
    description: str
    version: str


def _module_parts(kind: str, module_name: str) -> tuple[str, ...]:
    parts = tuple(part for part in re.split(r"[/.]", module_name.replace("-", "_")) if part)
    if not parts or any(not part.isidentifier() for part in parts):
        raise ValueError(f"invalid adapter module path: {module_name!r}")
    if kind == "source" and len(parts) < 2:
        raise ValueError(
            "source adapters must include a category namespace such as "
            "'platforms/example_exchange' or 'wallets/example_wallet'"
        )
    return parts


def _scaffold_adapter(
    *,
    spec: _AdapterScaffoldSpec,
    force: bool,
) -> tuple[Path, ...]:
    module_parts = _module_parts(spec.kind, spec.module_name)
    adapter_root = _adapter_root(spec.repo_root, spec.kind, module_parts)
    adapter_root.mkdir(parents=True, exist_ok=True)
    (adapter_root / "fixtures").mkdir(exist_ok=True)
    (adapter_root / "tests").mkdir(exist_ok=True)

    adapter_name = module_parts[-1]
    adapter_class_name = f"{_camel_case(adapter_name)}{spec.kind.title()}Adapter"
    return (
        _write_file(
            adapter_root / "__init__.py",
            'from .adapter import ADAPTER\n\n__all__ = ["ADAPTER"]\n',
            force=force,
        ),
        _write_file(
            adapter_root / "adapter.py",
            _adapter_template(
                spec=spec,
                adapter_name=adapter_name,
                adapter_class_name=adapter_class_name,
            ),
            force=force,
        ),
        *(
            (
                _write_file(
                    adapter_root / "translation.py",
                    _source_translation_template(adapter_name=adapter_name),
                    force=force,
                ),
            )
            if spec.kind == "source"
            else ()
        ),
        _write_file(
            adapter_root / "tests" / "__init__.py",
            "",
            force=force,
        ),
        _write_file(
            adapter_root / "tests" / "test_contract.py",
            _contract_test_template(kind=spec.kind, module_parts=module_parts),
            force=force,
        ),
        _write_file(
            adapter_root / "fixtures" / ".gitkeep",
            "",
            force=force,
        ),
    )


def _adapter_root(repo_root: Path, kind: str, module_parts: tuple[str, ...]) -> Path:
    namespace = "sources" if kind == "source" else "outputs"
    return repo_root / "src" / "tallylot" / "adapters" / namespace / Path(*module_parts)


def _adapter_template(
    *,
    spec: _AdapterScaffoldSpec,
    adapter_name: str,
    adapter_class_name: str,
) -> str:
    capability_block = (
        "        capabilities=frozenset(\n"
        "            {\n"
        "                AdapterCapability.SOURCE_TRANSLATE,\n"
        "                AdapterCapability.LOCATION_INVENTORY,\n"
        "            }\n"
        "        ),\n"
        if spec.kind == "source"
        else "        capabilities=frozenset({AdapterCapability.OUTPUT_RENDER}),\n"
    )
    body = (
        dedent(
            f"""
            \"\"\"{spec.display_name} {spec.kind} adapter.\"\"\"

            from __future__ import annotations

            from pathlib import Path

            from tallylot.domain.issues import IssueRecord
            from tallylot.domain.transactions import TransactionFact
            from tallylot.domain.types import AdapterId, JsonValue
            from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
            from tallylot.ports.evidence import LocationInventoryRecord
            from tallylot.ports.intake_routing import (
                IntakeFileFacts,
                IntakeRoute,
                IntakeRoutingRequest,
            )
            from tallylot.ports.output_adapters import RenderedArtifact
            from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile
            from tallylot.ports.source_translation import SourceTranslationBatch
            """
        )
        + ("from .translation import translate_source_batches\n\n" if spec.kind == "source" else "\n")
        + dedent(
            f"""


            class {adapter_class_name}:
                manifest = AdapterManifest(
                    adapter_id=AdapterId("{adapter_name}"),
                    display_name="{spec.display_name}",
                    version="{spec.version}",
            """
        )
        + capability_block
        + dedent(
            f"""
                    supported=False,
                    description="{spec.description}",
                )

            """
        )
    )
    if spec.kind == "source":
        body += dedent(
            """
                def match(
                    self,
                    source: str,
                    raw_dir: Path,
                    inventory: tuple[FileInventoryEntry, ...],
                ) -> int:
                    del source, raw_dir, inventory
                    return 0

                def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
                    del relative_path, facts
                    return 0

                def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
                    del request
                    return None

                def validate_profile_timezones(
                    self,
                    profile: SourceProfile,
                ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
                    del profile
                    return {{"status": "passed", "issue_count": 0, "rows_with_dates": 0, "mode_counts": {{}}}}, ()

                def extract_location_inventory(
                    self,
                    source: str,
                    raw_dir: Path,
                    profile: SourceProfile,
                ) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
                    del source, raw_dir, profile
                    return (), ()

                def translate(
                    self,
                    profile: SourceProfile,
                    raw_dir: Path,
                ) -> SourceTranslationBatch:
                    return translate_source_batches(profile, raw_dir)
            """
        )
    else:
        body += dedent(
            """
                def render(
                    self,
                    facts: tuple[TransactionFact, ...],
                    output_path: Path,
                ) -> RenderedArtifact:
                    del facts, output_path
                    raise NotImplementedError(
                        "Implement output rendering before enabling this adapter."
                    )
            """
        )
    body += dedent(
        """


            ADAPTER = """
        + adapter_class_name
        + "()\n"
    )
    return body


def _source_translation_template(*, adapter_name: str) -> str:
    return dedent(
        f"""
        \"\"\"Provider-local translation rules for the {adapter_name} source adapter.\"\"\"

        from __future__ import annotations

        from pathlib import Path

        from tallylot.adapters.support import (
            FileTranslationContext,
            FileTranslationRule,
            translate_file_families,
        )
        from tallylot.adapters.support.drafts import (
            EconomicActivityDraft,
            translation_batch_from_drafts,
        )
        from tallylot.domain.issues import IssueRecord
        from tallylot.ports.source_profiles import SourceProfile
        from tallylot.ports.source_translation import SourceTranslationBatch

        FILE_TRANSLATION_RULES = (
            FileTranslationRule(
                family="example_export",
                matches_path=lambda path: path.name == "example.csv",
                translate=_translate_example_export,
            ),
        )


        def translate_source_batches(
            profile: SourceProfile,
            raw_dir: Path,
        ) -> SourceTranslationBatch:
            translation = translate_file_families(
                raw_dir,
                profile=profile,
                rules=FILE_TRANSLATION_RULES,
            )
            return translation_batch_from_drafts(
                translation.drafts,
                issues=translation.issues,
            )


        def _translate_example_export(
            context: FileTranslationContext,
        ) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
            del context
            raise NotImplementedError(
                "Implement provider-local parsing and translation rules before enabling this adapter."
            )
        """
    )


def _contract_test_template(*, kind: str, module_parts: tuple[str, ...]) -> str:
    namespace = "sources" if kind == "source" else "outputs"
    module_name = ".".join(module_parts)
    adapter_id = module_parts[-1]
    return dedent(
        f"""
        from __future__ import annotations

        from tallylot.adapters.{namespace}.{module_name} import ADAPTER


        def test_manifest_adapter_id_matches_package_name() -> None:
            assert str(ADAPTER.manifest.adapter_id) == "{adapter_id}"
        """
    )


def _write_file(path: Path, content: str, *, force: bool) -> Path:
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite existing scaffold file without --force: {path}")
    path.write_text(content, encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    args = _build_argument_parser().parse_args(argv)
    resolved_repo_root = active_repo_root() if args.repo_root is None else args.repo_root.resolve()
    created = _scaffold_adapter(
        spec=_AdapterScaffoldSpec(
            repo_root=resolved_repo_root,
            kind=args.kind,
            module_name=args.module_name,
            display_name=args.display_name,
            description=args.description,
            version=args.version,
        ),
        force=args.force,
    )
    for path in created:
        print(path.relative_to(resolved_repo_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
