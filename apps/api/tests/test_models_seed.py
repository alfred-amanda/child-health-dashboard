
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlmodel import SQLModel, create_engine

from app.models import ExtractedFact, FactType, ReviewStatus
from app.seed import import_thomas_seed


def test_schema_migrates_on_sqlite() -> None:
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    assert engine is not None


def test_model_rejects_accepted_fact_without_provenance() -> None:
    fact = ExtractedFact(child_id='thomas', source_document_id='', fact_type=FactType.RECORD_FACT, status=ReviewStatus.ACCEPTED, field_path='labs.fake', raw_value='x', page=None, snippet='', confidence=0)
    with pytest.raises(ValueError):
        fact.ensure_provenance()


def test_model_accepts_reviewed_provenanced_fact() -> None:
    fact = ExtractedFact(child_id='thomas', source_document_id='SRC-003', fact_type=FactType.RECORD_FACT, status=ReviewStatus.ACCEPTED, field_path='red_flags.wet_diapers', raw_value='<4', page=2, snippet='Less than 4 wet diapers in 24 hours', confidence=0.99, reviewer_actor='john', reviewed_at=datetime.now(UTC))
    fact.ensure_provenance()


def test_thomas_seed_import_idempotent_and_counts_reconcile() -> None:
    first = import_thomas_seed()
    second = import_thomas_seed()
    assert first['sources'] == second['sources'] == 35
    assert second['conditions'] >= 6
    assert second['tasks'] >= 4
    assert second['questions'] == 10
