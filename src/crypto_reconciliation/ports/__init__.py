"""Port definitions."""

from .adapter_contracts import AdapterCapability, AdapterManifest
from .ai import ModelGateway, ReviewRequest, ReviewResponse
from .artifacts import ArtifactStorePort
from .evidence import EvidenceRepositoryPort, WalletInventoryRecord
from .facts import FactRepositoryPort
from .intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from .output_adapters import OutputAdapter, OutputAdapterRegistryPort, RenderedArtifact
from .source_adapters import SourceAdapter, SourceAdapterRegistryPort
from .source_profiles import FileInventoryEntry, SourceProfile, VerificationExportSet
from .source_translation import (
    ActivityClassification,
    ActivityDraftSeed,
    EconomicActivityDraft,
    EconomicLegDraft,
    SourceTranslationBatch,
)
from .workspace import WorkspaceLocator, WorkspaceRepository

__all__ = [
    "ActivityClassification",
    "ActivityDraftSeed",
    "AdapterCapability",
    "AdapterManifest",
    "ArtifactStorePort",
    "EconomicActivityDraft",
    "EconomicLegDraft",
    "EvidenceRepositoryPort",
    "FactRepositoryPort",
    "FileInventoryEntry",
    "IntakeFileFacts",
    "IntakeRoute",
    "IntakeRoutingRequest",
    "ModelGateway",
    "OutputAdapter",
    "OutputAdapterRegistryPort",
    "RenderedArtifact",
    "ReviewRequest",
    "ReviewResponse",
    "SourceAdapter",
    "SourceAdapterRegistryPort",
    "SourceProfile",
    "SourceTranslationBatch",
    "VerificationExportSet",
    "WalletInventoryRecord",
    "WorkspaceLocator",
    "WorkspaceRepository",
]
