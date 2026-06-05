"""Schema tests for the parechovirus symptom and triage issue models."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import SQLModel, Session, create_engine, select

from app.models import (
    ALL_MODELS,
    Child,
    ParechovirusSymptom,
    ParechovirusTriageIssue,
)


def test_parechovirus_models_registered() -> None:
    assert ParechovirusSymptom in ALL_MODELS
    assert ParechovirusTriageIssue in ALL_MODELS


def test_symptom_round_trip() -> None:
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(Child(id='thomas', name='Thomas Chen', dob='2026-05-17', sex='male'))
        session.add(
            ParechovirusSymptom(
                child_id='thomas',
                symptom_key='fever',
                severity=3,
                measurement_value=38.4,
                observed_at=now,
                actor='parent',
            )
        )
        session.commit()
        rows = session.exec(select(ParechovirusSymptom)).all()
    assert len(rows) == 1
    assert rows[0].symptom_key == 'fever'
    assert rows[0].measurement_value == 38.4
    assert rows[0].source == 'parent_log'


def test_triage_issue_round_trip() -> None:
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(Child(id='thomas', name='Thomas Chen', dob='2026-05-17', sex='male'))
        session.add(
            ParechovirusTriageIssue(
                child_id='thomas',
                rule_key='parecho_fever_neonate',
                label='Fever >=38.0 C in infant under 3 months',
                urgency='today',
                action='Call the pediatrician now',
                evidence='triage rule parecho_fever_neonate fired for symptoms: fever',
                source_id='SRC-003',
                source_title='ER AVS May 31 2026',
                page=2,
                snippet='call your pediatrician for fevers reaching 38.0 c or above',
                confidence=0.99,
                status='open',
                opened_at=now,
                related_symptom_ids='abc123',
            )
        )
        session.commit()
        rows = session.exec(select(ParechovirusTriageIssue)).all()
    assert len(rows) == 1
    assert rows[0].urgency == 'today'
    assert rows[0].status == 'open'
    assert rows[0].related_symptom_ids == 'abc123'
