"""Port definitions."""

from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    AccountingIntentHint,
    FactLegPolicy,
    LegKind,
    LegShapeLimit,
)

from .adapter_contracts import AdapterCapability, AdapterManifest
from .ai import ModelGateway, ReviewRequest, ReviewResponse
from .annotations import AdapterMetadata
from .artifacts import ArtifactStorePort
from .evidence import EvidenceRepositoryPort, LocationInventoryRecord
from .evidence_sets import EvidenceSetRepositoryPort
from .facts import FactRepositoryPort
from .intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from .output_adapters import (
    OutputAdapter,
    OutputAdapterRegistryPort,
    OutputRenderPolicy,
    RenderedArtifact,
)
from .source_adapters import SourceAdapter, SourceAdapterRegistryPort
from .source_profiles import FileInventoryEntry, SourceProfile
from .source_translation import (
    ActivityClassification,
    ActivityDraftSeed,
    EconomicActivityDraft,
    EconomicLegDraft,
    LocationDraft,
    SourceTranslationBatch,
    symbol_claim,
)
from .workspace import WorkspaceLocator, WorkspaceRepository

__all__ = [
    "SINGLE_PRIMARY_ACTIVITY_POLICY",
    "TWO_SIDED_PRIMARY_EXCHANGE_POLICY",
    "TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY",
    "AccountingIntentHint",
    "ActivityClassification",
    "ActivityDraftSeed",
    "AdapterCapability",
    "AdapterManifest",
    "AdapterMetadata",
    "ArtifactStorePort",
    "EconomicActivityDraft",
    "EconomicLegDraft",
    "EvidenceRepositoryPort",
    "EvidenceSetRepositoryPort",
    "FactLegPolicy",
    "FactRepositoryPort",
    "FileInventoryEntry",
    "IntakeFileFacts",
    "IntakeRoute",
    "IntakeRoutingRequest",
    "LegKind",
    "LegShapeLimit",
    "LocationDraft",
    "LocationInventoryRecord",
    "ModelGateway",
    "OutputAdapter",
    "OutputAdapterRegistryPort",
    "OutputRenderPolicy",
    "RenderedArtifact",
    "ReviewRequest",
    "ReviewResponse",
    "SourceAdapter",
    "SourceAdapterRegistryPort",
    "SourceProfile",
    "SourceTranslationBatch",
    "WorkspaceLocator",
    "WorkspaceRepository",
    "symbol_claim",
]
