"""EVM wallet-state adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from crypto_reconciliation.adapters.sources.wallet_record_support import (
    AdapterIssueSpec,
    WalletRecordSpec,
    adapter_issue,
    wallet_identifier_kind,
    wallet_record,
)
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    FileInventoryEntry,
    IssueRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, JsonValue
from crypto_reconciliation.ports.adapters import NormalizationResult


class EvmWalletAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("evm_wallet"),
        display_name="EVM Wallet",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.WALLET_INVENTORY}),
        description="Extracts wallet identifiers from EVM wallet state exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        lower_source = source.lower()
        if "evm wallet" in lower_source or "wallet state" in lower_source:
            return 100
        if any(
            item.relative_path.lower().endswith(".json") and "state" in item.relative_path.lower() for item in inventory
        ):
            return 80
        return 0

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        del profile
        return {"status": "passed", "issue_count": 0, "rows_with_dates": 0, "mode_counts": {}}, ()

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del profile
        evidence: list[WalletInventoryRecord] = []
        for path in sorted(raw_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            evidence.extend(_account_records(source, path.name, payload))
            evidence.extend(_identity_records(source, path.name, payload))
        if evidence:
            return tuple(evidence), ()
        return (), (
            adapter_issue(
                AdapterIssueSpec(
                    source=source,
                    adapter_id=str(self.manifest.adapter_id),
                    issue_kind="missing_identifier",
                    message="No wallet identifiers could be extracted from the EVM wallet state export.",
                )
            ),
        )

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        wallet_inventory, issues = self.extract_wallet_inventory(str(profile.source), raw_dir, profile)
        return NormalizationResult(
            canonical_events=(),
            canonical_balances=(),
            issues=issues,
            reviews=(),
            wallet_inventory=wallet_inventory,
        )


def _account_records(source: str, evidence_path: str, payload: object) -> list[WalletInventoryRecord]:
    state_root = _wallet_state_root(payload)
    if state_root is None:
        return []
    internal_accounts = state_root.get("internalAccounts")
    if not isinstance(internal_accounts, dict):
        return []
    internal_accounts_dict = cast(dict[str, object], internal_accounts)
    accounts_container = internal_accounts_dict.get("accounts")
    if not isinstance(accounts_container, dict):
        return []
    records: list[WalletInventoryRecord] = []
    accounts_dict = cast(dict[str, object], accounts_container)
    for account_payload in accounts_dict.values():
        if not isinstance(account_payload, dict):
            continue
        account_payload_dict = cast(dict[str, object], account_payload)
        address = str(account_payload_dict.get("address", "")).strip()
        if not address:
            continue
        metadata_map = _object_map(account_payload_dict.get("metadata"))
        keyring_map = _object_map(metadata_map.get("keyring"))
        keyring_type = str(keyring_map.get("type", "")).strip()
        records.append(
            wallet_record(
                WalletRecordSpec(
                    source=source,
                    identifier_kind="evm_address",
                    identifier_value=address,
                    network_scope="ethereum",
                    controller=f"EVM wallet {keyring_type}".strip(),
                    account_label=str(metadata_map.get("name", "")).strip(),
                    evidence_kind="wallet_state",
                    evidence_path=evidence_path,
                    confidence="high",
                )
            )
        )
    return records


def _identity_records(source: str, evidence_path: str, payload: object) -> list[WalletInventoryRecord]:
    state_root = _wallet_state_root(payload)
    if state_root is None:
        return []
    identities = state_root.get("identities")
    if not isinstance(identities, dict):
        return []
    records: list[WalletInventoryRecord] = []
    identities_dict = cast(dict[str, object], identities)
    for identifier, metadata in identities_dict.items():
        identifier_value = str(identifier).strip()
        if not identifier_value:
            continue
        identifier_kind = wallet_identifier_kind(identifier_value)
        if identifier_kind == "unknown":
            continue
        metadata_map = _object_map(metadata)
        records.append(
            wallet_record(
                WalletRecordSpec(
                    source=source,
                    identifier_kind=identifier_kind,
                    identifier_value=identifier_value,
                    network_scope=_network_scope(identifier_kind),
                    controller="EVM wallet state",
                    account_label=str(metadata_map.get("name", "")).strip(),
                    evidence_kind="wallet_state",
                    evidence_path=evidence_path,
                    confidence="medium",
                    note="Discovered from the wallet identity map rather than a chain-scoped export.",
                )
            )
        )
    return records


def _network_scope(identifier_kind: str) -> str:
    return {
        "evm_address": "ethereum",
        "tron_address": "tron",
        "btc_address": "bitcoin",
        "solana_address": "solana",
    }.get(identifier_kind, "")


def _object_map(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _wallet_state_root(payload: object) -> dict[str, object] | None:
    if not isinstance(payload, dict):
        return None
    payload_dict = cast(dict[str, object], payload)
    for key in ("wallet_state", "metamask"):
        candidate = payload_dict.get(key)
        if isinstance(candidate, dict):
            return cast(dict[str, object], candidate)
    return None


ADAPTER = EvmWalletAdapter()
