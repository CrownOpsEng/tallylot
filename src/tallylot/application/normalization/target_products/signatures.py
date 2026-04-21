"""Canonical target-product execution signatures."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import cast

from tallylot.application.claim.contracts import DraftProjectionFieldRecord
from tallylot.application.compatibility.checkpoints import (
    observation_details_from_evidence_set,
    project_balance_references_from_checkpoint,
)
from tallylot.application.compatibility.economic_facts import (
    project_compatibility_artifacts_from_economic_facts,
)
from tallylot.application.compatibility.reconciliation_states import (
    project_balance_snapshots_from_reconciliation_state,
)
from tallylot.domain.checkpoint import Checkpoint
from tallylot.domain.claim import ClaimSet
from tallylot.domain.economics import EconomicFacts
from tallylot.domain.evidence import EvidenceSet
from tallylot.domain.reconciliation import ReconciliationState

from .models import TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION

_CLAIM_SET_SIGNATURE_VERSION = "claim-set-execution-v1"
_ECONOMIC_FACTS_COMPATIBILITY_SIGNATURE_VERSION = "economic-facts-compatibility-v1"
_RECONCILIATION_STATE_SNAPSHOT_SIGNATURE_VERSION = "reconciliation-state-snapshot-v1"
_CHECKPOINT_REFERENCE_SIGNATURE_VERSION = "checkpoint-reference-v1"


def claim_set_execution_fingerprint(claim_set: ClaimSet) -> str:
    payload = {
        "signature_version": _CLAIM_SET_SIGNATURE_VERSION,
        "claim_set": claim_set.to_payload(),
        "target_product_signature_version": TARGET_PRODUCT_EXECUTION_SIGNATURE_VERSION,
    }
    return _hash_payload(payload)


def economic_facts_compatibility_signature(
    *,
    economic_facts: EconomicFacts,
    claim_set: ClaimSet,
    evidence_set: EvidenceSet,
    draft_projection_field_records: tuple[DraftProjectionFieldRecord, ...],
) -> str:
    projection = project_compatibility_artifacts_from_economic_facts(
        economic_facts=economic_facts,
        claim_set=claim_set,
        evidence_set=evidence_set,
        draft_projection_field_records=draft_projection_field_records,
    )
    payload = {
        "signature_version": _ECONOMIC_FACTS_COMPATIBILITY_SIGNATURE_VERSION,
        "facts": [fact.to_row() for fact in projection.facts],
        "fact_annotations": [
            cast(dict[str, object], record.to_json())
            for record in projection.fact_annotations
        ],
    }
    return _hash_payload(payload)


def reconciliation_state_snapshot_signature(state: ReconciliationState) -> str:
    payload = {
        "signature_version": _RECONCILIATION_STATE_SNAPSHOT_SIGNATURE_VERSION,
        "balance_snapshots": [
            snapshot.to_row()
            for snapshot in project_balance_snapshots_from_reconciliation_state(state)
        ],
    }
    return _hash_payload(payload)


def checkpoint_reference_signature(
    *,
    checkpoint: Checkpoint,
    reconciliation_states: tuple[ReconciliationState, ...],
    evidence_set: EvidenceSet,
) -> str:
    payload = {
        "signature_version": _CHECKPOINT_REFERENCE_SIGNATURE_VERSION,
        "balance_references": [
            reference.to_row()
            for reference in project_balance_references_from_checkpoint(
                checkpoint=checkpoint,
                reconciliation_states=reconciliation_states,
                observation_details=observation_details_from_evidence_set(evidence_set),
            )
        ],
    }
    return _hash_payload(payload)


def _hash_payload(payload: object) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
