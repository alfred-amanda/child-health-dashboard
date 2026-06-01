
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlmodel import Field, SQLModel


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid4().hex


class FactType(StrEnum):
    RECORD_FACT = 'record_fact'
    PARENT_OBSERVATION = 'parent_observation'
    DERIVED_METRIC = 'derived_metric'
    AI_SUMMARY = 'ai_summary'
    NEEDS_CONFIRMATION = 'needs_confirmation'
    DOCTOR_CONFIRMED = 'doctor_confirmed'


class ReviewStatus(StrEnum):
    NEW = 'new'
    EXTRACTED = 'extracted'
    NEEDS_CONFIRMATION = 'needs_confirmation'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    DOCTOR_CONFIRMED = 'doctor_confirmed'
    DUPLICATE = 'duplicate'


class TaskStatus(StrEnum):
    OPEN = 'open'
    RESOLVED = 'resolved'


class Child(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    name: str
    dob: str
    sex: str
    pcp: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class SourceDocument(SQLModel, table=True):
    id: str = Field(primary_key=True)
    child_id: str = Field(index=True)
    relative_path: str
    file_name: str
    sha256: str = Field(index=True)
    bytes: int = 0
    pages: int = 0
    text_chars: int = 0
    extraction_method: str = 'pymupdf_text'
    extraction_quality: str = 'text_ok'
    categories: str = ''
    output_text_path: str = ''
    status: ReviewStatus = ReviewStatus.NEW
    duplicate_of: str | None = None
    duplicate_reason: str | None = None
    created_at: datetime = Field(default_factory=now_utc)


class ExtractedFact(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    child_id: str = Field(index=True)
    source_document_id: str = Field(index=True)
    fact_type: FactType
    status: ReviewStatus = ReviewStatus.NEEDS_CONFIRMATION
    field_path: str
    raw_value: str
    normalized_value: str | None = None
    unit: str | None = None
    page: int | None = None
    snippet: str
    confidence: float = Field(ge=0, le=1)
    actor: str = 'system'
    reviewer_actor: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)

    def ensure_provenance(self) -> None:
        if not self.source_document_id or not self.snippet.strip() or self.confidence <= 0:
            raise ValueError('fact requires source_document_id, snippet, and confidence')
        if self.status in {ReviewStatus.ACCEPTED, ReviewStatus.DOCTOR_CONFIRMED}:
            if self.page is None:
                raise ValueError('accepted facts require page provenance')
            if not self.reviewer_actor or self.reviewed_at is None:
                raise ValueError('accepted facts require reviewer actor and timestamp')


class Encounter(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    child_id: str = Field(index=True)
    date: str
    category: str
    summary: str
    source_document_id: str
    page: int | None = None
    snippet: str
    confidence: float = Field(ge=0, le=1)


class Measurement(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    child_id: str = Field(index=True)
    measured_at: str
    kind: str
    value: float
    unit: str
    raw_value: str
    age_days: float | None = None
    source_document_id: str
    page: int | None = None
    snippet: str
    confidence: float = Field(ge=0, le=1)


class LabResult(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    child_id: str = Field(index=True)
    collected_at: str
    lab_name: str
    value: float | None = None
    unit: str | None = None
    raw_value: str
    age_days: float | None = None
    reference_range: str | None = None
    interpretation: str | None = None
    source_document_id: str
    page: int | None = None
    snippet: str
    confidence: float = Field(ge=0, le=1)


class Condition(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    child_id: str = Field(index=True)
    name: str
    status: str
    severity: str
    evidence: str
    watch_items: str = ''
    next_action: str = ''
    source_document_id: str
    page: int | None = None
    snippet: str
    confidence: float = Field(ge=0, le=1)


class RiskSignal(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    child_id: str = Field(index=True)
    key: str
    urgency: str
    evidence: str
    source_document_id: str
    page: int | None = None
    snippet: str
    confidence: float = Field(ge=0, le=1)


class Task(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    child_id: str = Field(index=True)
    title: str
    status: TaskStatus = TaskStatus.OPEN
    urgency: str = 'routine'
    source_document_id: str
    page: int | None = None
    snippet: str
    actor: str = 'system'
    created_at: datetime = Field(default_factory=now_utc)
    resolved_at: datetime | None = None
    resolved_by: str | None = None


class ParentObservation(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    child_id: str = Field(index=True)
    kind: str
    value: str
    observed_at: datetime = Field(default_factory=now_utc)
    actor: str
    created_at: datetime = Field(default_factory=now_utc)


class VaccineEvent(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    child_id: str = Field(index=True)
    vaccine: str
    status: str
    due_date: str | None = None
    given_date: str | None = None
    reason: str | None = None
    source_document_id: str
    page: int | None = None
    snippet: str
    confidence: float = Field(ge=0, le=1)


class DevelopmentMilestone(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    child_id: str = Field(index=True)
    domain: str
    milestone: str
    expected_age_window: str
    status: str
    enhanced_watch: bool = True
    source_document_id: str
    page: int | None = None
    snippet: str
    confidence: float = Field(ge=0, le=1)


class Question(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    child_id: str = Field(index=True)
    question: str
    status: str = 'open'
    source_document_id: str
    page: int | None = None
    snippet: str
    actor: str = 'system'
    created_at: datetime = Field(default_factory=now_utc)
    asked_at: datetime | None = None
    answered_at: datetime | None = None
    answer: str | None = None
    resolved_at: datetime | None = None


class WhatChangedEntry(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    child_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=now_utc)
    summary: str
    source_document_id: str
    page: int | None = None
    snippet: str


ALL_MODELS: tuple[type[SQLModel], ...] = (
    Child,
    SourceDocument,
    ExtractedFact,
    Encounter,
    Measurement,
    LabResult,
    Condition,
    RiskSignal,
    Task,
    ParentObservation,
    VaccineEvent,
    DevelopmentMilestone,
    Question,
    WhatChangedEntry,
)
