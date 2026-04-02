"""Application service exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = [
    "BaselineValidationService",
    "BatchScreeningService",
    "BatchStagingService",
    "ManifestService",
    "NormalizationService",
    "OutputProjectionService",
    "PdfBalanceExtractionService",
    "ProfileService",
    "RoundScaffoldingService",
    "SourceDiffService",
    "SourceIntakeService",
    "VerificationCompareService",
    "WalletInventoryService",
    "WorkspaceInitializationService",
]

_SERVICE_MODULES = {
    "BaselineValidationService": "crypto_reconciliation.application.services.baseline",
    "BatchScreeningService": "crypto_reconciliation.application.services.staging",
    "BatchStagingService": "crypto_reconciliation.application.services.staging",
    "ManifestService": "crypto_reconciliation.application.services.manifest",
    "NormalizationService": "crypto_reconciliation.application.services.normalize",
    "OutputProjectionService": "crypto_reconciliation.application.services.projections",
    "PdfBalanceExtractionService": "crypto_reconciliation.application.services.pdf_extract",
    "ProfileService": "crypto_reconciliation.application.services.profile",
    "RoundScaffoldingService": "crypto_reconciliation.application.services.rounds",
    "SourceDiffService": "crypto_reconciliation.application.services.source_diff",
    "SourceIntakeService": "crypto_reconciliation.application.services.intake",
    "VerificationCompareService": "crypto_reconciliation.application.services.verification",
    "WalletInventoryService": "crypto_reconciliation.application.services.wallet_inventory",
    "WorkspaceInitializationService": "crypto_reconciliation.application.services.workspace",
}

if TYPE_CHECKING:
    from .baseline import BaselineValidationService
    from .intake import SourceIntakeService
    from .manifest import ManifestService
    from .normalize import NormalizationService
    from .pdf_extract import PdfBalanceExtractionService
    from .profile import ProfileService
    from .projections import OutputProjectionService
    from .rounds import RoundScaffoldingService
    from .source_diff import SourceDiffService
    from .staging import BatchScreeningService, BatchStagingService
    from .verification import VerificationCompareService
    from .wallet_inventory import WalletInventoryService
    from .workspace import WorkspaceInitializationService


def __getattr__(name: str) -> object:
    module_name = _SERVICE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(name)
    module = import_module(module_name)
    return getattr(module, name)
