#!/usr/bin/env python3

"""Build a canonical wallet inventory from raw captures and profile-time evidence."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

from script_common import read_csv_rows, require_directory, write_csv_rows, write_json


WALLET_INVENTORY_HEADERS = (
    "wallet_id",
    "identifier_kind",
    "normalized_identifier",
    "display_identifier",
    "network_scopes",
    "source_labels",
    "controller_labels",
    "account_labels",
    "evidence_count",
    "primary_evidence_path",
    "status",
    "notes",
)

WALLET_EVIDENCE_HEADERS = (
    "source",
    "raw_dir",
    "wallet_id",
    "identifier_kind",
    "normalized_identifier",
    "display_identifier",
    "network_scope",
    "controller",
    "account_label",
    "evidence_kind",
    "evidence_path",
    "confidence",
    "note",
)

WALLET_ISSUE_HEADERS = (
    "source",
    "raw_dir",
    "wallet_id",
    "issue_kind",
    "message",
    "evidence_path",
)

SOURCE_INVENTORY_HEADERS = (
    "source",
    "activity_after_cutoff",
    "first_post_cutoff_tx",
    "export_window_start",
    "export_window_end",
    "import_order",
    "status",
    "raw_folder",
    "profile_status",
    "adapter",
    "normalization_status",
    "exception_count",
    "candidate_path",
    "notes",
)

EVM_ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")
NEAR_HEX_ACCOUNT_PATTERN = re.compile(r"(?<![a-f0-9])[a-f0-9]{64}(?![a-f0-9])")
BTC_XPUB_PATTERN = re.compile(r"^(?:xpub|ypub|zpub|tpub|upub|vpub)[1-9A-HJ-NP-Za-km-z]+$")
BTC_ADDRESS_PATTERN = re.compile(r"^(?:bc1[ac-hj-np-z02-9]{11,87}|[13][1-9A-HJ-NP-Za-km-z]{25,34})$")
TRON_ADDRESS_PATTERN = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")
SOLANA_ADDRESS_PATTERN = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args(argv)


def detect_repo_root(start: Path) -> Path | None:
    candidate = start.resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for path in (candidate, *candidate.parents):
        if (path / "03_analysis" / "issues" / "source_inventory.csv").exists():
            return path
    return None


def load_source_inventory(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    return [
        {header: (row.get(header, "") or "").strip() for header in SOURCE_INVENTORY_HEADERS}
        for row in rows
    ]


def infer_identifier_kind(value: str) -> str:
    text = value.strip()
    lower = text.lower()
    if EVM_ADDRESS_PATTERN.fullmatch(text):
        return "evm_address"
    if BTC_XPUB_PATTERN.fullmatch(text):
        return "btc_xpub"
    if BTC_ADDRESS_PATTERN.fullmatch(text.lower()):
        return "btc_address"
    if TRON_ADDRESS_PATTERN.fullmatch(text):
        return "tron_address"
    if SOLANA_ADDRESS_PATTERN.fullmatch(text):
        return "solana_address"
    if NEAR_HEX_ACCOUNT_PATTERN.fullmatch(lower):
        return "near_account"
    if lower.startswith("addr1") or len(text) >= 80 and all(char in "0123456789abcdef" for char in lower):
        return "cardano_account_key"
    return "address_alias"


def normalize_identifier(identifier_kind: str, value: str) -> str:
    text = value.strip()
    if identifier_kind in {"evm_address", "near_account", "address_alias"}:
        return text.lower()
    if identifier_kind == "btc_address":
        return text.lower()
    return text


def infer_network_scope(identifier_kind: str, source: str, raw_dir: Path, account_label: str = "") -> str:
    source_lower = source.strip().lower()
    path_lower = str(raw_dir).lower()
    account_lower = account_label.strip().lower()
    if identifier_kind == "address_alias":
        if "gtrade" in source_lower or "/gtrade/" in path_lower:
            return "polygon"
        return ""
    if identifier_kind == "evm_address":
        if "polygon" in source_lower or "polygon" in path_lower:
            return "polygon"
        if "bsc" in source_lower or "bsc" in path_lower or "bnb" in path_lower:
            return "bsc"
        if "ronin" in source_lower or "ronin" in path_lower:
            return "ronin"
        return "ethereum"
    if identifier_kind in {"btc_xpub", "btc_address"} or "btc" in account_lower or "bitcoin" in account_lower:
        return "bitcoin"
    if identifier_kind == "tron_address":
        return "tron"
    if identifier_kind == "solana_address":
        return "solana"
    if identifier_kind == "near_account":
        return "near"
    if identifier_kind == "cardano_account_key" or "cardano" in account_lower or "ada" in account_lower:
        return "cardano"
    return ""


def wallet_id_for(identifier_kind: str, normalized_identifier: str) -> str:
    return f"{identifier_kind}:{normalized_identifier}"


def wallet_evidence_row(
    *,
    source: str,
    raw_dir: Path,
    identifier_value: str,
    controller: str,
    account_label: str,
    evidence_kind: str,
    evidence_path: Path,
    confidence: str,
    note: str = "",
    identifier_kind: str | None = None,
) -> dict[str, str]:
    kind = identifier_kind or infer_identifier_kind(identifier_value)
    normalized_identifier = normalize_identifier(kind, identifier_value)
    network_scope = infer_network_scope(kind, source, raw_dir, account_label)
    return {
        "source": source,
        "raw_dir": str(raw_dir),
        "wallet_id": wallet_id_for(kind, normalized_identifier),
        "identifier_kind": kind,
        "normalized_identifier": normalized_identifier,
        "display_identifier": identifier_value.strip(),
        "network_scope": network_scope,
        "controller": controller,
        "account_label": account_label.strip(),
        "evidence_kind": evidence_kind,
        "evidence_path": str(evidence_path),
        "confidence": confidence,
        "note": note.strip(),
    }


def wallet_issue_row(
    *,
    source: str,
    raw_dir: Path,
    wallet_id: str,
    issue_kind: str,
    message: str,
    evidence_path: Path | None = None,
) -> dict[str, str]:
    return {
        "source": source,
        "raw_dir": str(raw_dir),
        "wallet_id": wallet_id,
        "issue_kind": issue_kind,
        "message": message,
        "evidence_path": str(evidence_path) if evidence_path is not None else "",
    }


def dedupe_rows(rows: Iterable[dict[str, str]], *, key_fields: Sequence[str]) -> list[dict[str, str]]:
    seen: set[tuple[str, ...]] = set()
    deduped: list[dict[str, str]] = []
    for row in rows:
        key = tuple(row.get(field, "") for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def extract_evm_wallets(source: str, raw_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    evidence: list[dict[str, str]] = []
    issues: list[dict[str, str]] = []
    addresses = {
        match.group(0)
        for path in raw_dir.glob("*.csv")
        for match in EVM_ADDRESS_PATTERN.finditer(path.name)
    }
    for address in sorted(addresses, key=str.lower):
        path = next(path for path in raw_dir.glob("*.csv") if address.lower() in path.name.lower())
        evidence.append(
            wallet_evidence_row(
                source=source,
                raw_dir=raw_dir,
                identifier_value=address,
                controller="Explorer export",
                account_label="",
                evidence_kind="filename",
                evidence_path=path,
                confidence="high",
            )
        )

    if not evidence:
        issues.append(
            wallet_issue_row(
                source=source,
                raw_dir=raw_dir,
                wallet_id="",
                issue_kind="missing_identifier",
                message="No EVM address could be extracted from the chain-scoped explorer capture.",
            )
        )
    elif len({row["normalized_identifier"] for row in evidence}) > 1:
        issues.append(
            wallet_issue_row(
                source=source,
                raw_dir=raw_dir,
                wallet_id="",
                issue_kind="multiple_primary_identifiers",
                message="A chain-scoped explorer capture exposed more than one owned EVM address.",
            )
        )

    return dedupe_rows(evidence, key_fields=WALLET_EVIDENCE_HEADERS), issues


def extract_ledger_live_wallets(source: str, raw_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    evidence: list[dict[str, str]] = []
    issues: list[dict[str, str]] = []
    account_identifiers: dict[str, set[str]] = defaultdict(set)
    for path in sorted(raw_dir.glob("ledgerlive-operations-*.csv")):
        for row in read_csv_rows(path):
            account_label = (row.get("Account Name") or "").strip()
            identifier_value = (row.get("Account xpub") or "").strip()
            if not identifier_value:
                continue
            account_identifiers[account_label].add(identifier_value)
            evidence.append(
                wallet_evidence_row(
                    source=source,
                    raw_dir=raw_dir,
                    identifier_value=identifier_value,
                    controller="Ledger Live",
                    account_label=account_label,
                    evidence_kind="csv_row",
                    evidence_path=path,
                    confidence="high",
                )
            )

    for account_label, identifiers in sorted(account_identifiers.items()):
        if len(identifiers) > 1:
            issues.append(
                wallet_issue_row(
                    source=source,
                    raw_dir=raw_dir,
                    wallet_id="",
                    issue_kind="account_identifier_conflict",
                    message=f"Ledger Live account {account_label or 'blank'} maps to multiple identifiers.",
                )
            )

    if not evidence:
        issues.append(
            wallet_issue_row(
                source=source,
                raw_dir=raw_dir,
                wallet_id="",
                issue_kind="missing_identifier",
                message="No account identifier was found in the Ledger Live operations exports.",
            )
        )

    return dedupe_rows(evidence, key_fields=WALLET_EVIDENCE_HEADERS), issues


def extract_near_wallets(source: str, raw_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    evidence: list[dict[str, str]] = []
    identifiers = {
        match.group(0)
        for path in raw_dir.glob("*.csv")
        for match in NEAR_HEX_ACCOUNT_PATTERN.finditer(path.name)
    }
    for identifier_value in sorted(identifiers):
        path = next(path for path in raw_dir.glob("*.csv") if identifier_value in path.name)
        evidence.append(
            wallet_evidence_row(
                source=source,
                raw_dir=raw_dir,
                identifier_value=identifier_value,
                controller="NearBlocks export",
                account_label="",
                evidence_kind="filename",
                evidence_path=path,
                confidence="high",
            )
        )

    issues: list[dict[str, str]] = []
    if not evidence:
        issues.append(
            wallet_issue_row(
                source=source,
                raw_dir=raw_dir,
                wallet_id="",
                issue_kind="missing_identifier",
                message="No NEAR account identifier was found in the raw filenames.",
            )
        )
    return dedupe_rows(evidence, key_fields=WALLET_EVIDENCE_HEADERS), issues


def extract_ronin_wallets(source: str, raw_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    evidence: list[dict[str, str]] = []
    identifiers = {
        match.group(0)
        for path in raw_dir.glob("*.csv")
        for match in EVM_ADDRESS_PATTERN.finditer(path.name)
    }
    for identifier_value in sorted(identifiers, key=str.lower):
        path = next(path for path in raw_dir.glob("*.csv") if identifier_value.lower() in path.name.lower())
        evidence.append(
            wallet_evidence_row(
                source=source,
                raw_dir=raw_dir,
                identifier_value=identifier_value,
                controller="Ronin explorer export",
                account_label="",
                evidence_kind="filename",
                evidence_path=path,
                confidence="high",
                note="Ronin addresses are recorded in 0x form in the raw export package.",
            )
        )

    issues: list[dict[str, str]] = []
    if not evidence:
        issues.append(
            wallet_issue_row(
                source=source,
                raw_dir=raw_dir,
                wallet_id="",
                issue_kind="missing_identifier",
                message="No Ronin address could be extracted from the raw filenames.",
            )
        )
    return dedupe_rows(evidence, key_fields=WALLET_EVIDENCE_HEADERS), issues


def extract_gtrade_identifiers(source: str, raw_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    evidence: list[dict[str, str]] = []
    aliases: set[str] = set()
    for path in raw_dir.glob("*.csv"):
        for row in read_csv_rows(path):
            alias = (row.get("ADDR") or "").strip()
            if alias:
                aliases.add(alias)
                evidence.append(
                    wallet_evidence_row(
                        source=source,
                        raw_dir=raw_dir,
                        identifier_value=alias,
                        identifier_kind="address_alias",
                        controller="GTrade report",
                        account_label="",
                        evidence_kind="csv_row",
                        evidence_path=path,
                        confidence="medium",
                        note="The report exposes a truncated trader alias instead of a full on-chain address.",
                    )
                )

    issues: list[dict[str, str]] = []
    if aliases:
        issues.append(
            wallet_issue_row(
                source=source,
                raw_dir=raw_dir,
                wallet_id="address_alias:" + min(alias.lower() for alias in aliases),
                issue_kind="partial_identifier_only",
                message="GTrade evidence exposes only a truncated address alias; keep companion explorer evidence linked in the canonical wallet inventory.",
                evidence_path=next(iter(raw_dir.glob("*.csv"))),
            )
        )
    else:
        issues.append(
            wallet_issue_row(
                source=source,
                raw_dir=raw_dir,
                wallet_id="",
                issue_kind="missing_identifier",
                message="No address alias was found in the GTrade report.",
            )
        )
    return dedupe_rows(evidence, key_fields=WALLET_EVIDENCE_HEADERS), issues


def extract_metamask_app_wallets(source: str, raw_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    evidence: list[dict[str, str]] = []
    issues: list[dict[str, str]] = []
    state_path = raw_dir / "MetaMask state logs.json"
    if not state_path.exists():
        issues.append(
            wallet_issue_row(
                source=source,
                raw_dir=raw_dir,
                wallet_id="",
                issue_kind="missing_identifier",
                message="MetaMask state logs were not found.",
            )
        )
        return evidence, issues

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    metamask = payload.get("metamask", {})
    internal_accounts = (((metamask.get("internalAccounts") or {}).get("accounts")) or {})
    for account in internal_accounts.values():
        identifier_value = (account.get("address") or "").strip()
        if not identifier_value:
            continue
        metadata = account.get("metadata") or {}
        keyring = metadata.get("keyring") or {}
        evidence.append(
            wallet_evidence_row(
                source=source,
                raw_dir=raw_dir,
                identifier_value=identifier_value,
                controller=f"MetaMask {keyring.get('type', '').strip()}".strip(),
                account_label=(metadata.get("name") or "").strip(),
                evidence_kind="app_state",
                evidence_path=state_path,
                confidence="high",
            )
        )

    identities = metamask.get("identities") or {}
    for identifier_value, identity in identities.items():
        if any(
            row["normalized_identifier"] == normalize_identifier(infer_identifier_kind(identifier_value), identifier_value)
            for row in evidence
        ):
            continue
        evidence.append(
            wallet_evidence_row(
                source=source,
                raw_dir=raw_dir,
                identifier_value=identifier_value,
                controller="MetaMask app",
                account_label=(identity.get("name") or "").strip(),
                evidence_kind="app_state",
                evidence_path=state_path,
                confidence="medium",
                note="Discovered from the MetaMask identity map rather than a chain-scoped export.",
            )
        )

    if not evidence:
        issues.append(
            wallet_issue_row(
                source=source,
                raw_dir=raw_dir,
                wallet_id="",
                issue_kind="missing_identifier",
                message="No wallet identifiers could be extracted from the MetaMask app state.",
                evidence_path=state_path,
            )
        )
    return dedupe_rows(evidence, key_fields=WALLET_EVIDENCE_HEADERS), issues


def profile_wallet_identifiers(source: str, raw_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, object]]:
    raw_dir = require_directory(raw_dir.resolve(), "Raw source directory")
    source_lower = source.strip().lower()
    path_lower = str(raw_dir).lower()
    if "app-metamask" in path_lower:
        evidence, issues = extract_metamask_app_wallets(source, raw_dir)
    elif "ledger live" in source_lower or "ledger live" in path_lower:
        evidence, issues = extract_ledger_live_wallets(source, raw_dir)
    elif "near" in source_lower or "/near/" in path_lower:
        evidence, issues = extract_near_wallets(source, raw_dir)
    elif "ronin" in source_lower or "/ronin/" in path_lower:
        evidence, issues = extract_ronin_wallets(source, raw_dir)
    elif "gtrade" in source_lower or "/gtrade/" in path_lower:
        evidence, issues = extract_gtrade_identifiers(source, raw_dir)
    elif any(token in source_lower or token in path_lower for token in ("metamask", "eth-", "bsc-", "polygon-", "eth-gala", "eth-ledger")):
        evidence, issues = extract_evm_wallets(source, raw_dir)
    else:
        evidence, issues = [], []

    summary = {
        "status": "passed" if not issues else "needs_review",
        "wallet_count": len({row["wallet_id"] for row in evidence}),
        "evidence_rows": len(evidence),
        "issue_count": len(issues),
    }
    return evidence, issues, summary


def summarize_wallet_inventory(evidence_rows: Sequence[dict[str, str]], issue_rows: Sequence[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in evidence_rows:
        grouped[row["wallet_id"]].append(row)

    inventory_rows: list[dict[str, str]] = []
    for wallet_id, rows in sorted(grouped.items()):
        identifier_kind = rows[0]["identifier_kind"]
        status = "ready"
        notes: list[str] = []
        if identifier_kind == "address_alias":
            status = "needs_linked_evidence"
            notes.append("Truncated alias only")
        inventory_rows.append(
            {
                "wallet_id": wallet_id,
                "identifier_kind": identifier_kind,
                "normalized_identifier": rows[0]["normalized_identifier"],
                "display_identifier": rows[0]["display_identifier"],
                "network_scopes": "; ".join(sorted({row["network_scope"] for row in rows if row["network_scope"]})),
                "source_labels": "; ".join(sorted({row["source"] for row in rows if row["source"]})),
                "controller_labels": "; ".join(sorted({row["controller"] for row in rows if row["controller"]})),
                "account_labels": "; ".join(sorted({row["account_label"] for row in rows if row["account_label"]})),
                "evidence_count": str(len(rows)),
                "primary_evidence_path": rows[0]["evidence_path"],
                "status": status,
                "notes": "; ".join(filter(None, [*notes, *sorted({row["note"] for row in rows if row["note"]})])),
            }
        )

    normalized_to_kinds: dict[str, set[str]] = defaultdict(set)
    for row in evidence_rows:
        normalized_to_kinds[row["normalized_identifier"]].add(row["identifier_kind"])

    generated_issues = list(issue_rows)
    for normalized_identifier, kinds in sorted(normalized_to_kinds.items()):
        if len(kinds) > 1:
            generated_issues.append(
                {
                    "source": "",
                    "raw_dir": "",
                    "wallet_id": "",
                    "issue_kind": "identifier_kind_conflict",
                    "message": f"Identifier {normalized_identifier} was classified under multiple kinds: {', '.join(sorted(kinds))}",
                    "evidence_path": "",
                }
            )

    summary = {
        "status": "passed" if not generated_issues else "needs_review",
        "wallet_count": len(inventory_rows),
        "evidence_rows": len(evidence_rows),
        "issue_count": len(generated_issues),
        "identifier_kind_counts": {
            kind: sum(1 for row in inventory_rows if row["identifier_kind"] == kind)
            for kind in sorted({row["identifier_kind"] for row in inventory_rows})
        },
    }
    return inventory_rows, summary


def supplemental_wallet_sources(repo_root: Path) -> list[dict[str, str]]:
    extra: list[dict[str, str]] = []
    for source, raw_folder in (
        ("MetaMask app", "01_raw_exports/external/app-metamask/2026-03"),
        ("ETH Ledger 1 capture", "01_raw_exports/external/eth-ledger1/2026-03"),
        ("Ronin", "01_raw_exports/external/ronin/raw"),
    ):
        raw_dir = repo_root / raw_folder
        if raw_dir.exists():
            extra.append(
                {
                    "source": source,
                    "raw_folder": raw_folder,
                }
            )
    return extra


def build_wallet_inventory(repo_root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict[str, object]]:
    repo_root = require_directory(repo_root.resolve(), "Repo root")
    source_inventory_rows = load_source_inventory(repo_root / "03_analysis" / "issues" / "source_inventory.csv")
    source_specs = [
        {"source": row["source"], "raw_folder": row["raw_folder"]}
        for row in source_inventory_rows
        if row.get("raw_folder")
    ]
    source_specs.extend(supplemental_wallet_sources(repo_root))

    evidence_rows: list[dict[str, str]] = []
    issue_rows: list[dict[str, str]] = []
    seen_sources: set[tuple[str, str]] = set()
    for spec in source_specs:
        key = (spec["source"], spec["raw_folder"])
        if key in seen_sources:
            continue
        seen_sources.add(key)
        raw_dir = repo_root / spec["raw_folder"]
        if not raw_dir.exists():
            issue_rows.append(
                wallet_issue_row(
                    source=spec["source"],
                    raw_dir=raw_dir,
                    wallet_id="",
                    issue_kind="missing_raw_folder",
                    message="Wallet inventory source row points to a raw folder that does not exist.",
                )
            )
            continue
        source_evidence, source_issues, _ = profile_wallet_identifiers(spec["source"], raw_dir)
        evidence_rows.extend(source_evidence)
        issue_rows.extend(source_issues)

    evidence_rows = dedupe_rows(evidence_rows, key_fields=WALLET_EVIDENCE_HEADERS)
    issue_rows = dedupe_rows(issue_rows, key_fields=WALLET_ISSUE_HEADERS)
    inventory_rows, summary = summarize_wallet_inventory(evidence_rows, issue_rows)
    return inventory_rows, evidence_rows, issue_rows, summary


def write_wallet_inventory_artifacts(
    out_dir: Path,
    *,
    inventory_rows: Sequence[dict[str, str]],
    evidence_rows: Sequence[dict[str, str]],
    issue_rows: Sequence[dict[str, str]],
    summary: dict[str, object],
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = out_dir / "wallet_inventory.csv"
    evidence_path = out_dir / "wallet_inventory_evidence.csv"
    issues_path = out_dir / "wallet_inventory_issues.csv"
    summary_path = out_dir / "wallet_inventory_summary.json"
    write_csv_rows(inventory_path, list(WALLET_INVENTORY_HEADERS), inventory_rows)
    write_csv_rows(evidence_path, list(WALLET_EVIDENCE_HEADERS), evidence_rows)
    write_csv_rows(issues_path, list(WALLET_ISSUE_HEADERS), issue_rows)
    write_json(
        summary_path,
        {
            **summary,
            "inventory_path": str(inventory_path),
            "evidence_path": str(evidence_path),
            "issues_path": str(issues_path),
        },
    )
    return {
        "inventory_path": str(inventory_path),
        "evidence_path": str(evidence_path),
        "issues_path": str(issues_path),
        "summary_path": str(summary_path),
    }


def refresh_wallet_inventory(repo_root: Path, *, out_dir: Path | None = None) -> dict[str, object]:
    repo_root = require_directory(repo_root.resolve(), "Repo root")
    inventory_rows, evidence_rows, issue_rows, summary = build_wallet_inventory(repo_root)
    paths = write_wallet_inventory_artifacts(
        out_dir or repo_root / "03_analysis" / "inventory",
        inventory_rows=inventory_rows,
        evidence_rows=evidence_rows,
        issue_rows=issue_rows,
        summary=summary,
    )
    return {
        **summary,
        **paths,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = detect_repo_root(args.repo_root) or args.repo_root.resolve()
    summary = refresh_wallet_inventory(repo_root, out_dir=args.out_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
