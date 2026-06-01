
from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Urgency = Literal['routine', 'soon', 'today', 'urgent', '911']
Confidence = Literal['low', 'moderate', 'high']


class MedicalBoundary(StrEnum):
    ORGANIZE_ONLY = 'organize_only_pediatrician_decides'


class SourceRef(BaseModel):
    source_id: str
    title: str
    page: int | None = None
    snippet: str
    confidence: float = Field(ge=0, le=1)

    @field_validator('source_id', 'title', 'snippet')
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('source fields may not be blank')
        return value


class RecommendationPayload(BaseModel):
    evidence: str
    action: str
    urgency: Urgency
    confidence: Confidence
    source: SourceRef
    boundary: MedicalBoundary = MedicalBoundary.ORGANIZE_ONLY

    @field_validator('evidence', 'action')
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('recommendations require evidence and action')
        return value

    def display_text(self) -> str:
        return (
            f"Because {self.evidence}, {self.action}. "
            f"Urgency: {self.urgency}. Confidence: {self.confidence}. "
            f"Source: {self.source.source_id} p.{self.source.page or '?'} — {self.source.snippet}"
        )


def validate_recommendations(payloads: list[RecommendationPayload]) -> None:
    for payload in payloads:
        RecommendationPayload.model_validate(payload.model_dump())
