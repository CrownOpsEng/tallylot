"""AI ports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ReviewRequest:
    task: str
    subject: str
    context: dict[str, object]


@dataclass(frozen=True)
class ReviewResponse:
    provider: str
    summary: str
    findings: tuple[str, ...]


class ModelGateway(Protocol):
    def review(self, request: ReviewRequest) -> ReviewResponse:
        ...
