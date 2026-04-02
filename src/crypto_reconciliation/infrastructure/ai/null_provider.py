"""Provider-agnostic AI stubs."""

from __future__ import annotations

from typing import override

from crypto_reconciliation.ports.ai import ModelGateway, ReviewRequest, ReviewResponse


class NullModelGateway(ModelGateway):
    @override
    def review(self, request: ReviewRequest) -> ReviewResponse:
        return ReviewResponse(
            provider="null",
            summary=f"No provider configured for task {request.task!r}.",
            findings=(),
        )


class LocalStubModelGateway(ModelGateway):
    @override
    def review(self, request: ReviewRequest) -> ReviewResponse:
        return ReviewResponse(
            provider="local_stub",
            summary=f"Stub review for {request.subject}",
            findings=tuple(sorted(str(key) for key in request.context)),
        )
