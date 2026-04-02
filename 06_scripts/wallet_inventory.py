#!/usr/bin/env python3

"""Build a canonical wallet inventory from profiled source captures."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Sequence

from pipeline_common import build_source_profile
from script_common import require_directory, write_csv_rows, write_json
from source_adapters import get_adapter
from wallet_inventory_common import WALLET_EVIDENCE_HEADERS, WALLET_ISSUE_HEADERS, dedupe_rows, wallet_issue_row


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

SOURCE_INVENTORY_HEADERS = (
    "source",
    "activity_after_cutoff",
    "first_post_cutoff_tx",
    "export_window_start",
    "export_window_end",
    "import_order",
    "status",
    "capture_path",
    "profile_status",
    "adapter",
    "normalization_status",
    "exception_count",
    "candidate_path",
    "notes",
)


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


def profile_wallet_identifiers(
    source: str,
    raw_dir: Path,
    adapter_name: str = "",
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, object]]:
    raw_dir = require_directory(raw_dir.resolve(), "Raw source directory")
    profile = build_source_profile(
        source=source,
        raw_dir=raw_dir,
        adapter_name="generic",
        adapter_supported=False,
    )
    adapter = get_adapter(source, profile)
    if adapter.name == "generic" and adapter_name:
        adapter = get_adapter(adapter_name, profile)
    evidence, issues = adapter.extract_wallet_identifiers(source, raw_dir, profile)
    summary = {
        "status": "passed" if not issues else "needs_review",
        "adapter": adapter.name,
        "wallet_count": len({row["wallet_id"] for row in evidence}),
        "evidence_rows": len(evidence),
        "issue_count": len(issues),
    }
    return evidence, issues, summary


def summarize_wallet_inventory(
    evidence_rows: Sequence[dict[str, str]],
    issue_rows: Sequence[dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, object]]:
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
                    "capture_path": "",
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


def build_wallet_inventory(repo_root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict[str, object]]:
    repo_root = require_directory(repo_root.resolve(), "Repo root")
    source_inventory_rows = load_source_inventory(repo_root / "03_analysis" / "issues" / "source_inventory.csv")
    source_specs = [
        {"source": row["source"], "capture_path": row["capture_path"], "adapter": row["adapter"]}
        for row in source_inventory_rows
        if row.get("capture_path")
    ]

    evidence_rows: list[dict[str, str]] = []
    issue_rows: list[dict[str, str]] = []
    seen_sources: set[tuple[str, str]] = set()
    for spec in source_specs:
        key = (spec["source"], spec["capture_path"])
        if key in seen_sources:
            continue
        seen_sources.add(key)
        raw_dir = repo_root / spec["capture_path"]
        if not raw_dir.exists():
            issue_rows.append(
                wallet_issue_row(
                    source=spec["source"],
                    raw_dir=raw_dir,
                    wallet_id="",
                    issue_kind="missing_capture_path",
                    message="Wallet inventory source row points to a capture path that does not exist.",
                )
            )
            continue
        source_evidence, source_issues, _ = profile_wallet_identifiers(
            spec["source"],
            raw_dir,
            adapter_name=spec.get("adapter", ""),
        )
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
