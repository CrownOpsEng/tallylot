from __future__ import annotations

from dataclasses import dataclass
import json
import shutil
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "source_packs"


@dataclass(frozen=True)
class SourcePack:
    name: str
    root: Path
    source: str
    mode: str
    expected_adapter: str
    expected_timezone_status: str = "passed"
    adapter_name_override: str | None = None

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def expected_dir(self) -> Path:
        return self.root / "expected"

    def expected_json(self, name: str) -> object:
        path = self.expected_dir / f"{name}.json"
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)


def load_source_packs(mode: str) -> list[SourcePack]:
    packs: list[SourcePack] = []
    for root in sorted(PACK_ROOT.iterdir()):
        if not root.is_dir():
            continue
        manifest = root / "pack.json"
        if not manifest.exists():
            continue
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        if payload.get("mode") != mode:
            continue
        packs.append(
            SourcePack(
                name=root.name,
                root=root,
                source=payload["source"],
                mode=payload["mode"],
                expected_adapter=payload["expected_adapter"],
                expected_timezone_status=payload.get("expected_timezone_status", "passed"),
                adapter_name_override=payload.get("adapter_name_override"),
            )
        )
    return packs


def stage_source_pack(pack: SourcePack, destination_root: Path) -> Path:
    target = destination_root / pack.name / "raw"
    shutil.copytree(pack.raw_dir, target)
    return target


def strip_dynamic_wallet_paths(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            key: value
            for key, value in row.items()
            if key not in {"capture_path", "evidence_path"}
        }
        for row in rows
    ]
