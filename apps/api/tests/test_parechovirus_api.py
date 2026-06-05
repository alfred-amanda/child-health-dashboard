"""End-to-end tests for the parechovirus API endpoints.

These hit the FastAPI app via ``TestClient`` against a throwaway
SQLite file, so we exercise routing, validation, persistence, and the
triage engine wiring in one shot.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine

from app import db as db_module
from app import main as main_module
from app.config import get_settings
from app.db import get_session


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, 'parecho_test.db')
        env = {
            'CHD_DB_URL': f'sqlite:///{db_path}',
            'CHD_EXTERNAL_SERVICES__ENABLED': 'false',
        }
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        # get_settings has no lru_cache wrapper; subsequent calls re-read env.
        # rebuild the engine bound to the temp DB
        engine = create_engine(f'sqlite:///{db_path}', connect_args={'check_same_thread': False})
        SQLModel.metadata.create_all(engine)
        monkeypatch.setattr(db_module, 'engine', engine, raising=False)

        def _override_session() -> Generator:  # type: ignore[no-untyped-def]
            from sqlmodel import Session
            with Session(engine) as session:
                yield session

        main_module.app.dependency_overrides[get_session] = _override_session
        with TestClient(main_module.app) as c:
            yield c
        main_module.app.dependency_overrides.clear()


def test_catalog_includes_symptoms_and_rules(client: TestClient) -> None:
    response = client.get('/api/parechovirus/catalog')
    assert response.status_code == 200
    body = response.json()
    keys = {s['key'] for s in body['symptoms']}
    assert 'fever' in keys and 'seizure' in keys
    rule_keys = {r['rule_key'] for r in body['rules']}
    assert 'parecho_seizure' in rule_keys
    assert 'parecho_fever_neonate' in rule_keys


def test_log_fever_opens_today_issue(client: TestClient) -> None:
    response = client.post(
        '/api/parechovirus/symptoms',
        json={'symptom_key': 'fever', 'severity': 3, 'measurement_value': 38.6, 'actor': 'parent'},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['symptom']['symptom_key'] == 'fever'
    rule_keys = {issue['rule_key'] for issue in body['new_triage_issues']}
    assert 'parecho_fever_neonate' in rule_keys


def test_log_seizure_creates_911_issue(client: TestClient) -> None:
    response = client.post(
        '/api/parechovirus/symptoms',
        json={
            'symptom_key': 'seizure',
            'severity': 5,
            'duration_minutes': 2,
            'measurement_value': None,
            'actor': 'parent',
        },
    )
    assert response.status_code == 200
    body = response.json()
    urgencies = {issue['urgency'] for issue in body['new_triage_issues']}
    assert '911' in urgencies


def test_log_fever_and_lethargy_escalates_to_911(client: TestClient) -> None:
    client.post(
        '/api/parechovirus/symptoms',
        json={'symptom_key': 'fever', 'severity': 3, 'measurement_value': 38.6, 'actor': 'parent'},
    )
    response = client.post(
        '/api/parechovirus/symptoms',
        json={'symptom_key': 'lethargy', 'severity': 3, 'actor': 'parent'},
    )
    body = response.json()
    urgencies = {issue['urgency'] for issue in body['new_triage_issues']}
    assert '911' in urgencies


def test_invalid_severity_rejected(client: TestClient) -> None:
    response = client.post(
        '/api/parechovirus/symptoms',
        json={'symptom_key': 'fever', 'severity': 99, 'measurement_value': 38.0},
    )
    assert response.status_code == 400


def test_unknown_symptom_rejected(client: TestClient) -> None:
    response = client.post(
        '/api/parechovirus/symptoms',
        json={'symptom_key': 'not_real', 'severity': 3},
    )
    assert response.status_code == 400


def test_list_symptoms_filters_window(client: TestClient) -> None:
    client.post(
        '/api/parechovirus/symptoms',
        json={'symptom_key': 'fever', 'severity': 2, 'measurement_value': 38.0, 'actor': 'parent'},
    )
    response = client.get('/api/parechovirus/symptoms?days=1')
    assert response.status_code == 200
    body = response.json()
    assert body['count'] >= 1
    assert body['symptoms'][0]['symptom_key'] == 'fever'


def test_list_triage_default_open(client: TestClient) -> None:
    client.post(
        '/api/parechovirus/symptoms',
        json={'symptom_key': 'fever', 'severity': 3, 'measurement_value': 38.5, 'actor': 'parent'},
    )
    response = client.get('/api/parechovirus/triage')
    body = response.json()
    assert body['status'] == 'open'
    assert body['count'] >= 1


def test_manual_triage_creation_and_resolve(client: TestClient) -> None:
    create = client.post(
        '/api/parechovirus/triage',
        json={'rule_key': 'parecho_fever_neonate', 'actor': 'parent'},
    )
    assert create.status_code == 200, create.text
    issue = create.json()
    assert issue['status'] == 'open'

    ack = client.patch(
        f'/api/parechovirus/triage/{issue["id"]}',
        json={'status': 'acknowledged', 'actor': 'parent'},
    )
    assert ack.status_code == 200
    assert ack.json()['status'] == 'acknowledged'
    assert ack.json()['acknowledged_by'] == 'parent'

    resolved = client.patch(
        f'/api/parechovirus/triage/{issue["id"]}',
        json={'status': 'resolved', 'actor': 'pediatrician', 'resolution_notes': 'spoke with nurse line'},
    )
    assert resolved.status_code == 200
    payload = resolved.json()
    assert payload['status'] == 'resolved'
    assert payload['resolution_notes'] == 'spoke with nurse line'


def test_manual_triage_rejects_unknown_rule(client: TestClient) -> None:
    response = client.post(
        '/api/parechovirus/triage',
        json={'rule_key': 'nonsense', 'actor': 'parent'},
    )
    assert response.status_code == 400


def test_today_aggregates_open_issues(client: TestClient) -> None:
    client.post(
        '/api/parechovirus/symptoms',
        json={'symptom_key': 'fever', 'severity': 3, 'measurement_value': 38.5, 'actor': 'parent'},
    )
    response = client.get('/api/parechovirus/today')
    body = response.json()
    assert body['symptom_count_24h'] >= 1
    assert body['open_issue_count'] >= 1
    assert body['highest_urgency'] in {'routine', 'watch', 'soon', 'today', 'urgent', '911'}


def test_today_reports_911_when_seizure_logged(client: TestClient) -> None:
    client.post(
        '/api/parechovirus/symptoms',
        json={'symptom_key': 'seizure', 'severity': 5, 'duration_minutes': 1, 'actor': 'parent'},
    )
    response = client.get('/api/parechovirus/today')
    assert response.json()['highest_urgency'] == '911'
