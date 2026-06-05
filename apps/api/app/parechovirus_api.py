"""HTTP endpoints for the parechovirus symptom tracker and triage queue.

The flow is intentionally small:

1. ``GET  /api/parechovirus/catalog`` returns the static symptom catalog
   and triage rules so the UI can render the log form.
2. ``POST /api/parechovirus/symptoms`` accepts a single logged
   observation, persists it, then runs the rule engine against the
   last 24h of symptoms to open new triage issues.
3. ``GET  /api/parechovirus/symptoms`` lists the last N days of logs.
4. ``GET  /api/parechovirus/triage`` lists triage issues (filterable
   by status; default = open).
5. ``POST /api/parechovirus/triage`` opens an issue manually (parent
   override or doctor-supplied).
6. ``PATCH /api/parechovirus/triage/{id}`` moves an issue through
   acknowledge/resolve.
7. ``GET  /api/parechovirus/today`` returns the page payload: child,
   today\u2019s symptoms, open issues, and the highest current urgency.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from .db import get_session
from .models import (
    Child,
    ParechovirusSymptom,
    ParechovirusTriageIssue,
)
from .parechovirus import (
    RULE_PREDICATES,
    SYMPTOM_CATALOG,
    TRIAGE_RULES,
    SymptomDef,
    TriageRule,
    evaluate_symptoms,
    get_symptom,
    highest_urgency,
)

router = APIRouter(prefix='/api/parechovirus', tags=['parechovirus'])

DEFAULT_CHILD_ID = 'thomas'


def _symptom_defs() -> list[dict[str, Any]]:
    return [
        {
            'key': s.key,
            'label': s.label,
            'category': s.category.value,
            'severity_min': s.severity_min,
            'severity_max': s.severity_max,
            'measurement': s.measurement.value,
            'unit': s.unit,
            'description': s.description,
            'parent_prompt': s.parent_prompt,
            'source_id': s.source_id,
            'source_title': s.source_title,
            'page': s.page,
            'snippet': s.snippet,
            'confidence': s.confidence,
        }
        for s in SYMPTOM_CATALOG
    ]


def _triage_rule_dicts() -> list[dict[str, Any]]:
    return [
        {
            'rule_key': r.key,
            'label': r.label,
            'urgency': r.urgency,
            'action': r.action,
            'source_id': r.source_id,
            'source_title': r.source_title,
            'page': r.page,
            'snippet': r.snippet,
            'confidence': r.confidence,
        }
        for r in TRIAGE_RULES
    ]


def _symptom_to_dict(symptom: ParechovirusSymptom) -> dict[str, Any]:
    return {
        'id': symptom.id,
        'child_id': symptom.child_id,
        'symptom_key': symptom.symptom_key,
        'severity': symptom.severity,
        'measurement_value': symptom.measurement_value,
        'duration_minutes': symptom.duration_minutes,
        'observed_at': symptom.observed_at.isoformat(),
        'notes': symptom.notes,
        'actor': symptom.actor,
        'source': symptom.source,
        'created_at': symptom.created_at.isoformat(),
    }


def _issue_to_dict(issue: ParechovirusTriageIssue) -> dict[str, Any]:
    return {
        'id': issue.id,
        'child_id': issue.child_id,
        'rule_key': issue.rule_key,
        'label': issue.label,
        'urgency': issue.urgency,
        'action': issue.action,
        'evidence': issue.evidence,
        'source_id': issue.source_id,
        'source_title': issue.source_title,
        'page': issue.page,
        'snippet': issue.snippet,
        'confidence': issue.confidence,
        'status': issue.status,
        'opened_at': issue.opened_at.isoformat(),
        'acknowledged_at': issue.acknowledged_at.isoformat() if issue.acknowledged_at else None,
        'acknowledged_by': issue.acknowledged_by,
        'resolved_at': issue.resolved_at.isoformat() if issue.resolved_at else None,
        'resolved_by': issue.resolved_by,
        'resolution_notes': issue.resolution_notes,
        'related_symptom_ids': [s for s in issue.related_symptom_ids.split(',') if s],
    }


def _get_or_create_child(session: Session, child_id: str) -> Child:
    child = session.get(Child, child_id)
    if child is not None:
        return child
    child = Child(
        id=child_id,
        name='Thomas Chen' if child_id == DEFAULT_CHILD_ID else child_id,
        dob='2026-05-17' if child_id == DEFAULT_CHILD_ID else '2026-05-17',
        sex='male',
    )
    session.add(child)
    session.flush()
    return child


def _symptoms_for_window(
    session: Session, child_id: str, since: datetime
) -> list[ParechovirusSymptom]:
    return list(
        session.exec(
            select(ParechovirusSymptom)
            .where(ParechovirusSymptom.child_id == child_id)
            .where(ParechovirusSymptom.observed_at >= since)
            .order_by(ParechovirusSymptom.observed_at.desc())
        ).all()
    )


def _cooldown_open_issue(
    session: Session, child_id: str, rule_key: str, window: timedelta
) -> ParechovirusTriageIssue | None:
    """Avoid opening a duplicate issue for the same rule within ``window``."""
    cutoff = datetime.now(UTC) - window
    return session.exec(
        select(ParechovirusTriageIssue)
        .where(ParechovirusTriageIssue.child_id == child_id)
        .where(ParechovirusTriageIssue.rule_key == rule_key)
        .where(ParechovirusTriageIssue.opened_at >= cutoff)
    ).first()


@router.get('/catalog')
def get_catalog() -> dict[str, list[dict[str, Any]]]:
    return {'symptoms': _symptom_defs(), 'rules': _triage_rule_dicts()}


@router.post('/symptoms')
def post_symptom(
    payload: dict[str, Any],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Log a new symptom observation and open any matching triage issues."""
    try:
        symptom_key = str(payload['symptom_key'])
        severity = int(payload['severity'])
        actor = str(payload.get('actor', 'parent'))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(400, f'invalid payload: {exc}') from exc

    try:
        definition: SymptomDef = get_symptom(symptom_key)
    except KeyError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not (definition.severity_min <= severity <= definition.severity_max):
        raise HTTPException(
            400,
            f'severity {severity} outside allowed range {definition.severity_min}-{definition.severity_max} for {symptom_key}',
        )

    child_id = str(payload.get('child_id', DEFAULT_CHILD_ID))
    _get_or_create_child(session, child_id)

    measurement_value = payload.get('measurement_value')
    if measurement_value is not None:
        try:
            measurement_value = float(measurement_value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(400, f'measurement_value must be numeric: {exc}') from exc

    duration_minutes = payload.get('duration_minutes')
    if duration_minutes is not None:
        try:
            duration_minutes = int(duration_minutes)
        except (TypeError, ValueError) as exc:
            raise HTTPException(400, f'duration_minutes must be int: {exc}') from exc

    observed_at_raw = payload.get('observed_at')
    if observed_at_raw:
        try:
            observed_at = datetime.fromisoformat(str(observed_at_raw).replace('Z', '+00:00'))
        except ValueError as exc:
            raise HTTPException(400, f'observed_at must be ISO-8601: {exc}') from exc
    else:
        observed_at = datetime.now(UTC)

    symptom = ParechovirusSymptom(
        child_id=child_id,
        symptom_key=symptom_key,
        severity=severity,
        measurement_value=measurement_value,
        duration_minutes=duration_minutes,
        observed_at=observed_at,
        notes=payload.get('notes'),
        actor=actor,
        source=str(payload.get('source', 'parent_log')),
    )
    session.add(symptom)
    session.flush()

    new_issues = _run_triage_for_window(session, child_id, window=timedelta(hours=24))

    session.commit()
    session.refresh(symptom)

    return {
        'symptom': _symptom_to_dict(symptom),
        'new_triage_issues': [_issue_to_dict(issue) for issue in new_issues],
    }


def _run_triage_for_window(
    session: Session, child_id: str, window: timedelta
) -> list[ParechovirusTriageIssue]:
    """Run the rule engine and open any new issues (with dedupe cooldown)."""
    cutoff = datetime.now(UTC) - window
    recent = _symptoms_for_window(session, child_id, cutoff)
    rule_inputs = [
        {
            'symptom_key': s.symptom_key,
            'severity': s.severity,
            'measurement_value': s.measurement_value,
            'duration_minutes': s.duration_minutes,
            'observed_at': s.observed_at,
        }
        for s in recent
    ]
    triggered = evaluate_symptoms(rule_inputs)

    opened: list[ParechovirusTriageIssue] = []
    cooldown = timedelta(hours=6)
    for result in triggered:
        if _cooldown_open_issue(session, child_id, result['rule_key'], cooldown):
            continue
        related_ids = [str(s.id) for s in recent]
        issue = ParechovirusTriageIssue(
            child_id=child_id,
            rule_key=result['rule_key'],
            label=result['label'],
            urgency=result['urgency'],
            action=result['action'],
            evidence=result['evidence'],
            source_id=result['source_id'],
            source_title=result['source_title'],
            page=result['page'],
            snippet=result['snippet'],
            confidence=result['confidence'],
            status='open',
            related_symptom_ids=','.join(related_ids[-10:]),
        )
        session.add(issue)
        session.flush()
        opened.append(issue)
    return opened


@router.get('/symptoms')
def list_symptoms(
    session: Annotated[Session, Depends(get_session)],
    days: int = Query(7, ge=1, le=90),
    child_id: str = DEFAULT_CHILD_ID,
) -> dict[str, Any]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = list(
        session.exec(
            select(ParechovirusSymptom)
            .where(ParechovirusSymptom.child_id == child_id)
            .where(ParechovirusSymptom.observed_at >= cutoff)
            .order_by(ParechovirusSymptom.observed_at.desc())
        ).all()
    )
    return {
        'child_id': child_id,
        'days': days,
        'count': len(rows),
        'symptoms': [_symptom_to_dict(row) for row in rows],
    }


@router.get('/triage')
def list_triage(
    session: Annotated[Session, Depends(get_session)],
    status: str = Query('open'),
    child_id: str = DEFAULT_CHILD_ID,
) -> dict[str, Any]:
    rows = list(
        session.exec(
            select(ParechovirusTriageIssue)
            .where(ParechovirusTriageIssue.child_id == child_id)
            .where(ParechovirusTriageIssue.status == status)
            .order_by(ParechovirusTriageIssue.opened_at.desc())
        ).all()
    )
    return {
        'child_id': child_id,
        'status': status,
        'count': len(rows),
        'issues': [_issue_to_dict(row) for row in rows],
    }


@router.post('/triage')
def create_triage_issue(
    payload: dict[str, Any],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Manually open a triage issue (parent override / doctor-supplied)."""
    try:
        rule_key = str(payload['rule_key'])
        actor = str(payload.get('actor', 'parent'))
    except (KeyError, TypeError) as exc:
        raise HTTPException(400, f'invalid payload: {exc}') from exc

    rule = next((r for r in TRIAGE_RULES if r.key == rule_key), None)
    if rule is None:
        raise HTTPException(400, f'unknown rule_key: {rule_key}')

    child_id = str(payload.get('child_id', DEFAULT_CHILD_ID))
    _get_or_create_child(session, child_id)

    issue = ParechovirusTriageIssue(
        child_id=child_id,
        rule_key=rule.key,
        label=rule.label,
        urgency=rule.urgency,
        action=rule.action,
        evidence=str(payload.get('evidence', f'manual triage issue opened by {actor} for rule {rule.key}')),
        source_id=rule.source_id,
        source_title=rule.source_title,
        page=rule.page,
        snippet=rule.snippet,
        confidence=rule.confidence,
        status='open',
        related_symptom_ids=str(payload.get('related_symptom_ids', '')),
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return _issue_to_dict(issue)


@router.patch('/triage/{issue_id}')
def update_triage_issue(
    issue_id: str,
    payload: dict[str, Any],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    issue = session.get(ParechovirusTriageIssue, issue_id)
    if issue is None:
        raise HTTPException(404, f'triage issue {issue_id} not found')

    status = str(payload.get('status', issue.status))
    if status not in {'open', 'acknowledged', 'resolved'}:
        raise HTTPException(400, f'invalid status: {status}')

    actor = payload.get('actor')
    now = datetime.now(UTC)

    if status == 'acknowledged' and issue.status == 'open':
        issue.acknowledged_at = now
        issue.acknowledged_by = str(actor) if actor else None

    if status == 'resolved':
        issue.resolved_at = now
        issue.resolved_by = str(actor) if actor else None
        if payload.get('resolution_notes') is not None:
            issue.resolution_notes = str(payload['resolution_notes'])

    issue.status = status
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return _issue_to_dict(issue)


@router.get('/today')
def parechovirus_today(
    session: Annotated[Session, Depends(get_session)],
    child_id: str = DEFAULT_CHILD_ID,
) -> dict[str, Any]:
    """Page payload for /parechovirus: today's symptoms + open issues."""
    cutoff_24h = datetime.now(UTC) - timedelta(hours=24)
    today_symptoms = _symptoms_for_window(session, child_id, cutoff_24h)
    open_issues = list(
        session.exec(
            select(ParechovirusTriageIssue)
            .where(ParechovirusTriageIssue.child_id == child_id)
            .where(ParechovirusTriageIssue.status != 'resolved')
            .order_by(ParechovirusTriageIssue.opened_at.desc())
        ).all()
    )
    urgencies = [issue.urgency for issue in open_issues]
    return {
        'child_id': child_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'highest_urgency': highest_urgency(urgencies),
        'symptom_count_24h': len(today_symptoms),
        'open_issue_count': len(open_issues),
        'symptoms_today': [_symptom_to_dict(s) for s in today_symptoms],
        'open_issues': [_issue_to_dict(i) for i in open_issues],
    }
