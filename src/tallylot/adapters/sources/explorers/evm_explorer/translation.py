"""EVM explorer translation rules."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.explorers.evm_explorer.families import (
    classified_csv_paths,
)
from tallylot.adapters.sources.explorers.evm_explorer.issues import (
    blocked_nft_tx_hashes,
    nft_transfer_issues,
    unsupported_internal_transfer_issues,
)
from tallylot.adapters.sources.explorers.evm_explorer.models import (
    EvmTranslationContext,
)
from tallylot.adapters.sources.explorers.evm_explorer.native_transfers import (
    translate_native_transfers,
    unsupported_native_methods,
)
from tallylot.adapters.sources.explorers.evm_explorer.token_transfers import (
    translate_token_transfers,
)
from tallylot.adapters.support.drafts import EconomicActivityDraft
from tallylot.domain.issues import IssueRecord
from tallylot.ports.source_profiles import SourceProfile


def translate_transactions(
    profile: SourceProfile,
    raw_dir: Path,
    *,
    owned_addresses: set[str],
    network_scope: str,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    context = EvmTranslationContext(
        owned_addresses=owned_addresses,
        network_scope=network_scope,
        blocked_tx_hashes=blocked_nft_tx_hashes(raw_dir),
        unsupported_methods=unsupported_native_methods(raw_dir),
    )
    for path, family_id in classified_csv_paths(raw_dir):
        if family_id == "native_transfers":
            path_drafts, path_issues = translate_native_transfers(
                profile,
                path,
                context,
            )
        elif family_id == "token_transfers":
            path_drafts, path_issues = translate_token_transfers(
                profile,
                path,
                context,
            )
        elif family_id == "internal_transfers":
            path_drafts, path_issues = (
                (),
                unsupported_internal_transfer_issues(profile, path),
            )
        elif family_id == "nft_transfers":
            path_drafts, path_issues = (
                (),
                nft_transfer_issues(profile, path, owned_addresses=owned_addresses),
            )
        else:
            path_drafts, path_issues = (), ()
        drafts.extend(path_drafts)
        issues.extend(path_issues)
    return tuple(drafts), tuple(issues)
