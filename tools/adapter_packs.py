from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from repo_support.paths import adapter_packs_root


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


def _load_adapter_packs(
    *,
    pack_root: Path | None = None,
    capability: str | None = None,
) -> tuple[AdapterPack, ...]:
    resolved_pack_root = (
        adapter_packs_root() if pack_root is None else pack_root.resolve()
    )
    packs: list[AdapterPack] = []
    for manifest in sorted(resolved_pack_root.glob("*/*/pack.json")):
        pack = _load_adapter_pack(manifest)
        if capability is not None and not pack.supports(capability):
            continue
        packs.append(pack)
    return tuple(packs)


def select_adapter_packs(
    *,
    pack_root: Path | None = None,
    selected_ids: tuple[str, ...] = (),
    capability: str | None = None,
) -> tuple[AdapterPack, ...]:
    packs = _load_adapter_packs(pack_root=pack_root, capability=capability)
    if not selected_ids:
        return packs
    selected = {pack_id.strip() for pack_id in selected_ids if pack_id.strip()}
    matched = tuple(pack for pack in packs if pack.id in selected)
    missing = sorted(selected.difference(pack.id for pack in matched))
    if missing:
        raise ValueError(f"unknown adapter pack ids: {', '.join(missing)}")
    return matched


def _load_adapter_pack(manifest_path: Path) -> AdapterPack:
    payload = _manifest_payload(manifest_path)
    root = manifest_path.parent
    raw_dir = root / "raw"
    expected_dir = root / "expected"
    if not raw_dir.is_dir():
        raise ValueError(
            f"adapter pack is missing required raw/ directory: {manifest_path}"
        )
    if not expected_dir.is_dir():
        raise ValueError(
            f"adapter pack is missing required expected/ directory: {manifest_path}"
        )
    adapter = payload.get("adapter", root.parent.name)
    source = payload.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError(
            f"adapter pack manifest is missing a valid source: {manifest_path}"
        )
    expected_adapter = payload.get("expected_adapter", adapter)
    if not isinstance(expected_adapter, str) or not str(expected_adapter).strip():
        raise ValueError(
            f"adapter pack manifest is missing a valid expected_adapter: {manifest_path}"
        )
    return AdapterPack(
        adapter=str(adapter),
        name=root.name,
        root=root,
        source=source.strip(),
        capabilities=_capabilities_for_payload(payload),
        expected_adapter=str(expected_adapter),
        expected_timezone_status=_payload_str(
            payload, "expected_timezone_status", "passed"
        ),
        expected_normalization_status=_payload_str(
            payload,
            "expected_normalization_status",
            "ready",
        ),
        adapter_name_override=_optional_payload_str(payload, "adapter_name_override"),
        capture_dir_name=_optional_payload_str(payload, "capture_dir_name"),
    )


def _capabilities_for_payload(payload: dict[str, object]) -> frozenset[str]:
    capabilities = payload.get("capabilities")
    if isinstance(capabilities, list):
        capability_items = cast(list[object], capabilities)
        normalized_capabilities: set[str] = set()
        for item in capability_items:
            if isinstance(item, str):
                normalized = item.strip()
                if normalized:
                    normalized_capabilities.add(normalized)
        return frozenset(normalized_capabilities)
    mode = _optional_payload_str(payload, "mode")
    return frozenset({mode} if mode else ())


def _payload_str(payload: dict[str, object], key: str, default: str) -> str:
    value = payload.get(key, default)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _optional_payload_str(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _manifest_payload(manifest_path: Path) -> dict[str, object]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            f"adapter pack manifest must be a JSON object: {manifest_path}"
        )
    return cast(dict[str, object], payload)
