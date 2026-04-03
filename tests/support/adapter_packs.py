from __future__ import annotations

from dataclasses import dataclass
import json
import shutil
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "adapter_packs"


@dataclass(frozen=True)
class AdapterPack:
    adapter: str
    name: str
    root: Path
    source: str
    capabilities: frozenset[str]
    expected_adapter: str
    expected_timezone_status: str = "passed"
    expected_normalization_status: str = "ready"
    adapter_name_override: str | None = None
    capture_dir_name: str | None = None

    @property
    def id(self) -> str:
        return f"{self.adapter}/{self.name}"

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def expected_dir(self) -> Path:
        return self.root / "expected"

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities

    def expected_json(self, name: str) -> object:
        path = self.expected_dir / f"{name}.json"
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)


def _capabilities_for_payload(payload: dict[str, object]) -> frozenset[str]:
    capabilities = payload.get("capabilities")
    if isinstance(capabilities, list):
        return frozenset(str(item).strip() for item in capabilities if str(item).strip())
    mode = str(payload.get("mode", "")).strip()
    return frozenset({mode} if mode else ())


def load_adapter_packs(capability: str | None = None) -> list[AdapterPack]:
    packs: list[AdapterPack] = []
    for manifest in sorted(PACK_ROOT.glob("*/*/pack.json")):
        root = manifest.parent
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        adapter = payload.get("adapter", root.parent.name)
        capabilities = _capabilities_for_payload(payload)
        if capability is not None and capability not in capabilities:
            continue
        packs.append(
            AdapterPack(
                adapter=str(adapter),
                name=root.name,
                root=root,
                source=str(payload["source"]),
                capabilities=capabilities,
                expected_adapter=str(payload.get("expected_adapter", adapter)),
                expected_timezone_status=str(payload.get("expected_timezone_status", "passed")),
                expected_normalization_status=str(payload.get("expected_normalization_status", "ready")),
                adapter_name_override=payload.get("adapter_name_override"),
                capture_dir_name=payload.get("capture_dir_name"),
            )
        )
    return packs


def stage_adapter_pack(pack: AdapterPack, destination_root: Path) -> Path:
    capture_dir_name = pack.capture_dir_name or f"{pack.adapter}_{pack.name}"
    target = destination_root / capture_dir_name / "raw"
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


def strip_dynamic_issue_paths(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            key: value
            for key, value in row.items()
            if key not in {"capture_path", "evidence_path"}
        }
        for row in rows
    ]
