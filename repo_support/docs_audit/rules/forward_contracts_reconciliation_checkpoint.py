from __future__ import annotations

from repo_support.docs_audit.rules import forward_contracts_support as support
from repo_support.docs_audit.rules._common import build_rule


FORWARD_CONTRACTS_RECONCILIATION_CHECKPOINT_RULES = (
    build_rule(
        "forward_contracts.evidence_assertion_and_ref_contracts_are_defined",
        "docs/concepts/domain-ontology.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("AssertionValue or canonical ref seams drifted")
            )
            for needle in (
                "## `AssertionValue`",
                "## Identity And Ref Seams",
                "### Canonical Ref Shapes",
                "### `ContractRef` Versus `PositionRef`",
                "`ContractRef`",
                "`PositionRef`",
                "assertion ids and fingerprints must treat the value variant and its canonical",
            )
            if needle
            not in (
                support.text(support.docs_path("concepts/domain-ontology.md"))
                + "\n"
                + support.text(
                    support.docs_path(
                        "reference/economics-reconciliation-checkpoint-contract.md"
                    )
                )
            )
        ],
    ),
    build_rule(
        "forward_contracts.reconciliation_and_checkpoint_hot_path_fields_use_direct_values",
        "docs/reference/economics-reconciliation-checkpoint-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("reconciliation/checkpoint hot-path value rules drifted")
            )
            for needle in (
                "`expected_value`",
                "`observed_value`",
                "`accepted_value`",
                "use value refs that point to undefined sidecar values outside the kernel",
                "`expected_value_ref`",
                "`observed_value_ref`",
                "Not allowed in this slice:",
            )
            if needle
            not in (
                support.text(support.docs_path("concepts/pipeline-stage-contracts.md"))
                + "\n"
                + support.text(
                    support.docs_path(
                        "reference/economics-reconciliation-checkpoint-contract.md"
                    )
                )
            )
        ],
    ),
)
