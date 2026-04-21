from __future__ import annotations

from repo_support.docs_audit.rules import forward_contracts_support as support
from repo_support.docs_audit.rules._common import build_rule


FORWARD_CONTRACTS_FOUNDATION_RULES = (
    build_rule(
        "forward_contracts.do_not_reference_undefined_record_families_or_refs",
        "docs/concepts/pipeline-stage-contracts.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("forward contracts reference undefined record families")
            )
            for condition in (
                support.used_record_families()
                - support.DEFINED_TARGET_RECORD_FAMILIES
                - support.ALLOWED_CURRENT_STATE_RECORD_NAMES
            )
            if condition
        ]
        + [
            (_ for _ in ()).throw(
                AssertionError("forward contracts reference undefined ref types")
            )
            for condition in (
                support.used_ref_types() - support.DEFINED_TARGET_REF_TYPES
            )
            if condition
        ],
    ),
)
