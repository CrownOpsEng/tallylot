from __future__ import annotations

DISALLOWED_SUMMARY_PHRASES = (
    "human-facing entrypoint",
    "owning concept page",
    "owning contract",
    "helper reference",
    "single authority",
    "design anchor",
    "implementation anchor",
    "forward design",
    "owner pages",
    "primary owners",
    "authoritative owners",
)

LOCAL_PROVIDER_SUMMARY_ALLOWLIST = frozenset(
    {
        "docs/status/current-state.md",
        "docs/concepts/current-bridge-contracts.md",
        "docs/concepts/transaction-classification.md",
        "docs/concepts/oracle-boundaries.md",
        "docs/reference/cointracking-oracle-artifacts.md",
    }
)

FORWARD_LOOKING_PROVIDER_OR_CUSTODY_NOUNS = (
    "coinbase",
    "binance",
    "wealthsimple",
    "crypto.com",
    "shakepay",
    "ledger live",
    "ronin",
    "gtrade",
    "cointracking",
    "custodial",
)


def validate_summary_style(path: str, summary: str) -> str | None:
    lowered_summary = summary.lower()
    for phrase in DISALLOWED_SUMMARY_PHRASES:
        if phrase not in lowered_summary:
            continue
        return (
            f"{path} must use a content-first summary and avoid banned summary "
            f"phrase {phrase!r}"
        )

    if path in LOCAL_PROVIDER_SUMMARY_ALLOWLIST or path.startswith("docs/workspace/"):
        return None

    for noun in FORWARD_LOOKING_PROVIDER_OR_CUSTODY_NOUNS:
        if noun not in lowered_summary:
            continue
        return (
            f"{path} must keep provider and custody nouns out of forward-looking "
            f"summaries; found {noun!r}"
        )
    return None


__all__ = ["validate_summary_style"]
