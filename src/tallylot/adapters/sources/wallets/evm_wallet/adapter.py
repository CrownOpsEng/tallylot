"""EVM wallet-state adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from tallylot.adapters.support import (
    canonical_location_id_from_identifier,
    location_identifier_kind,
    location_issue,
    location_record,
    match_intake_by_path_or_header,
    matching_file_paths,
    no_intake_route,
)
from tallylot.adapters.support.drafts import translation_batch_from_drafts
from tallylot.adapters.support.locations import LocationIssueSpec, LocationRecordSpec
from tallylot.domain.issues import IssueRecord
from tallylot.domain.locations import LocationKind
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from tallylot.ports.source_profiles import FileFamilyClaim, FileInventoryEntry, SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch


class EvmWalletAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("evm_wallet"),
        display_name="EVM Wallet",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.LOCATION_INVENTORY, AdapterCapability.INTAKE_ROUTE}),
        description="Extracts wallet identifiers from EVM wallet state exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        if self.classify_profile_families(source, raw_dir, inventory):
            return 100
        lower_source = source.lower()
        if "evm wallet" in lower_source or "wallet state" in lower_source:
            return 100
        if any(
            item.relative_path.lower().endswith(".json") and "state" in item.relative_path.lower() for item in inventory
        ):
            return 80
        return 0

    def classify_profile_families(
        self,
        source: str,
        raw_dir: Path,
        inventory: tuple[FileInventoryEntry, ...],
    ) -> tuple[FileFamilyClaim, ...]:
        del source, inventory
        claims: list[FileFamilyClaim] = []
        for path in matching_file_paths(raw_dir, pattern="*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if _wallet_state_root(payload) is None:
                continue
            claims.append(
                FileFamilyClaim(
                    relative_path=path.relative_to(raw_dir).as_posix(),
                    adapter_id=self.manifest.adapter_id,
                    family_id="wallet_state",
                )
            )
        return tuple(claims)

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("state logs", "wallet state"),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        del profile
        return {"status": "passed", "issue_count": 0, "rows_with_dates": 0, "mode_counts": {}}, ()

    def extract_location_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del profile
        evidence: list[LocationInventoryRecord] = []
        issues: list[IssueRecord] = []
        for path in matching_file_paths(raw_dir, pattern="*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            account_records, account_issues = _account_records(source, path.name, payload)
            evidence.extend(account_records)
            issues.extend(account_issues)
        if evidence:
            return tuple(evidence), tuple(issues)
        return (), (
            *issues,
            location_issue(
                LocationIssueSpec(
                    source=source,
                    adapter_id=str(self.manifest.adapter_id),
                    issue_kind="missing_identifier",
                    message="No authoritative wallet identifiers could be extracted from the wallet-state export.",
                )
            ),
        )

    def translate(self, profile: SourceProfile, raw_dir: Path) -> SourceTranslationBatch:
        location_inventory, issues = self.extract_location_inventory(str(profile.source), raw_dir, profile)
        return translation_batch_from_drafts(
            issues=issues,
            location_inventory=location_inventory,
        )


def _account_records(
    source: str,
    evidence_path: str,
    payload: object,
) -> tuple[list[LocationInventoryRecord], list[IssueRecord]]:
    state_root = _wallet_state_root(payload)
    if state_root is None:
        return [], []
    internal_accounts = state_root.get("internalAccounts")
    if not isinstance(internal_accounts, dict):
        return [], []
    internal_accounts_dict = cast(dict[str, object], internal_accounts)
    accounts_container = internal_accounts_dict.get("accounts")
    if not isinstance(accounts_container, dict):
        return [], []
    records: list[LocationInventoryRecord] = []
    issues: list[IssueRecord] = []
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
        account_type = str(account_payload_dict.get("type", "")).strip()
        scopes = tuple(
            str(scope).strip()
            for scope in cast(list[object], account_payload_dict.get("scopes", []))
            if isinstance(scope, str) and str(scope).strip()
        )
        identifier_kind, network_scope, issue_kind, issue_message = _account_identifier_context(
            address=address,
            account_type=account_type,
            scopes=scopes,
        )
        if issue_kind:
            issues.append(
                location_issue(
                    LocationIssueSpec(
                        source=source,
                        adapter_id="evm_wallet",
                        issue_kind=issue_kind,
                        message=issue_message,
                        raw_file=evidence_path,
                    )
                )
            )
            continue
        records.append(
            location_record(
                LocationRecordSpec(
                    source=source,
                    location_id=canonical_location_id_from_identifier(
                        identifier_kind,
                        address,
                        network_scope=network_scope,
                    ),
                    location_kind=LocationKind.ADDRESS,
                    location_label=_account_label(metadata_map, address),
                    identifier_kind=identifier_kind,
                    identifier_value=address,
                    network_scope=network_scope,
                    controller=f"EVM wallet {keyring_type}".strip(),
                    evidence_kind="wallet_state",
                    evidence_path=evidence_path,
                    confidence="high",
                )
            )
        )
    return records, issues


def _network_scope(identifier_kind: str) -> str:
    return {
        "tron_address": "tron",
        "btc_address": "bitcoin",
        "solana_address": "solana",
        "near_account": "near",
    }.get(identifier_kind, "")


def _account_identifier_context(
    *,
    address: str,
    account_type: str,
    scopes: tuple[str, ...],
) -> tuple[str, str, str, str]:
    # pylint: disable=too-many-return-statements
    identifier_kind = location_identifier_kind(address)
    if identifier_kind == "unknown":
        return (
            identifier_kind,
            "",
            "unsupported_wallet_identifier",
            f"Wallet-state account {address} is not a supported canonical identifier.",
        )
    namespace = account_type.split(":", 1)[0].strip().lower()
    if namespace == "eip155":
        if identifier_kind != "evm_address":
            return (
                identifier_kind,
                "",
                "unsupported_wallet_identifier",
                f"Wallet-state account {address} declares EVM ownership but is not an EVM address.",
            )
        network_scope = _evm_network_scope(scopes)
        if not network_scope:
            return (
                identifier_kind,
                "",
                "ambiguous_wallet_identifier",
                (
                    f"Wallet-state account {address} is an EVM address without a single chain-scoped ownership "
                    "claim; use chain-specific exports for canonical routing."
                ),
            )
        return identifier_kind, network_scope, "", ""
    expected_kind = {
        "tron": "tron_address",
        "bip122": "btc_address",
        "solana": "solana_address",
    }.get(namespace, "")
    if expected_kind:
        if identifier_kind != expected_kind:
            return (
                identifier_kind,
                "",
                "unsupported_wallet_identifier",
                f"Wallet-state account {address} does not match declared wallet namespace {namespace}.",
            )
        return identifier_kind, _network_scope(identifier_kind), "", ""
    if identifier_kind == "evm_address":
        return (
            identifier_kind,
            "",
            "ambiguous_wallet_identifier",
            (
                f"Wallet-state account {address} is an EVM address without chain-scoped ownership evidence; "
                "use chain-specific exports for canonical routing."
            ),
        )
    return identifier_kind, _network_scope(identifier_kind), "", ""


def _evm_network_scope(scopes: tuple[str, ...]) -> str:
    chain_ids = {
        scope.split(":", 1)[1]
        for scope in scopes
        if scope.lower().startswith("eip155:") and ":" in scope and scope.split(":", 1)[1] != "0"
    }
    if len(chain_ids) != 1:
        return ""
    return {
        "1": "ethereum",
        "10": "optimism",
        "56": "bsc",
        "137": "polygon",
        "8453": "base",
        "42161": "arbitrum",
    }.get(next(iter(chain_ids)), "")


def _account_label(metadata_map: dict[str, object], address: str) -> str:
    name = str(metadata_map.get("name", "")).strip()
    if name:
        return name
    snap_map = _object_map(metadata_map.get("snap"))
    snap_name = str(snap_map.get("name", "")).strip()
    return snap_name or address


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
