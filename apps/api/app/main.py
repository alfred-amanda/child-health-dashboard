
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .alerts import emit_alert
from .bilirubin import BilirubinPoint, assess, threshold_curve
from .config import get_settings
from .db import get_session, init_db
from .doctor_prep import THOMAS_QUESTIONS
from .growth import MeasurementInput, compute_growth_snapshot
from .ingestion import ingest_file
from .models import Condition, Encounter, LabResult, ParentObservation, Question, Task
from .predictions import forecast_gaps
from .recommendations import RecommendationPayload, SourceRef
from .red_flags import Observation, evaluate_observation, load_thomas_rules
from .research import load_weekly_digest, refresh_weekly_digest
from .seed import import_thomas_seed, load_profile
from .watch import build_what_to_watch

app = FastAPI(title='Child Health Dashboard API')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])


@app.on_event('startup')
def startup() -> None:
    init_db()


@app.get('/api/health')
def health() -> dict[str, str | bool]:
    settings = get_settings()
    return {'ok': True, 'external_services_enabled': settings.external_services.enabled, 'phi_local_first': not settings.external_services.enabled}


@app.post('/api/seed/thomas')
def seed_thomas() -> dict[str, int]:
    return import_thomas_seed()


@app.get('/api/today')
def today(alarm: bool = False) -> dict[str, Any]:
    profile = load_profile()
    rules = load_thomas_rules(Path(get_settings().seed_root))
    red_flag = evaluate_observation(Observation('wet_diapers_24h', 3), rules) if alarm else None
    routine = RecommendationPayload(
        evidence='Thomas continued to feed well throughout his hospital stay and fever resolved by discharge',
        action='watch feeding, wet diapers, temperature, and use the discharge red-flag reference if symptoms appear',
        urgency='routine',
        confidence='moderate',
        source=SourceRef(source_id='SRC-003', title='ER AVS May 31 2026', page=1, snippet='continued to feed well throughout his hospital stay', confidence=0.95),
    )
    return {
        'child': profile['patient']['name'],
        'status': 'alarm' if red_flag else 'routine',
        'status_strip': 'URGENT: source-driven red flag active' if red_flag else 'Routine watch: reassuring signs first, keep red flags one tap away',
        'primary_recommendation': (red_flag or routine).model_dump(),
        'reassurance_first': [
            {'label': 'CSF without pleocytosis', 'source': 'structured_profile.er_hospitalization.key_results.CSF'},
            {'label': 'CRP <0.3 and procalcitonin 0.16', 'source': 'structured_profile.er_hospitalization.key_results'},
            {'label': 'Clinically improved at discharge', 'source': 'SRC-003 p.1'},
        ],
        'watching': ['DAT-positive jaundice/anemia watch', 'Hep B catch-up', 'culture final confirmation'],
        'red_flags': [rule.__dict__ for rule in rules],
    }


@app.get('/api/timeline')
def timeline(session: Annotated[Session, Depends(get_session)]) -> list[dict[str, Any]]:
    return [encounter.model_dump() for encounter in session.exec(select(Encounter).order_by(Encounter.date)).all()]


@app.get('/api/conditions')
def conditions(session: Annotated[Session, Depends(get_session)]) -> list[dict[str, Any]]:
    return [condition.model_dump() for condition in session.exec(select(Condition)).all()]


@app.get('/api/red-flags')
def red_flags() -> list[dict[str, Any]]:
    return [rule.__dict__ for rule in load_thomas_rules(Path(get_settings().seed_root))]


@app.get('/api/charts/bilirubin')
def bilirubin_chart() -> dict[str, Any]:
    profile = load_profile()
    points = []
    for item in profile['blood_type_jaundice']['bilirubin_values']:
        numeric = float(str(item['value']).split()[0])
        hours_text = item['age'].replace('~', '').replace('hours', '').replace('DOL', '').strip()
        hours = float(hours_text) if hours_text.replace('.', '').isdigit() else 12 * 24
        if 'DOL' in item['age']:
            hours = float(item['age'].split('DOL')[1].strip()) * 24
        point = BilirubinPoint(hours=hours, bilirubin_mg_dl=numeric, test=item['test'], source='structured-profile')
        assessment = assess(point, profile['birth_history']['gestational_age'], dat_positive=True)
        points.append({'hour': hours, 'value': numeric, 'test': item['test'], 'assessment': assessment.__dict__})
    curve = threshold_curve(profile['birth_history']['gestational_age'], True)
    return {'points': points, 'threshold_curve': curve, 'risk_factor': 'DAT-positive / isoimmune hemolytic disease', 'source': 'local AAP-2022 table'}


@app.get('/api/growth')
def growth() -> dict[str, Any]:
    return compute_growth_snapshot([
        MeasurementInput(kind='weight', value=8.93, unit='lb', measured_at='2026-05-31', actor='seed-record'),
        MeasurementInput(kind='length', value=21.34, unit='in', measured_at='2026-05-31', actor='seed-record'),
        MeasurementInput(kind='head', value=14.69, unit='in', measured_at='2026-05-31', actor='seed-record'),
    ], sex='male', dob='2026-05-17')


@app.get('/api/charts/growth')
def growth_chart() -> dict[str, Any]:
    snapshot = growth()
    return {'standard': snapshot['standard'], 'headline': 'newborn weight loss/regain leads', 'points': snapshot['measurements'], 'projection': snapshot['projection'], 'percentiles': snapshot['percentiles']}


@app.get('/api/research')
def research(refresh: bool = False) -> dict[str, Any]:
    cache_root = get_settings().storage_root
    if refresh:
        return refresh_weekly_digest(cache_root, allow_network=False)
    return load_weekly_digest(cache_root)


@app.get('/api/watch')
def watch() -> dict[str, Any]:
    digest = load_weekly_digest(get_settings().storage_root)
    return build_what_to_watch(research_signals=[
        {'title': update['title'], 'action': update['summary'], 'confidence': update['confidence'], 'sources': update['sources']}
        for update in digest['updates']
    ])


@app.get('/api/charts/labs')
def labs(session: Annotated[Session, Depends(get_session)]) -> list[dict[str, Any]]:
    return [lab.model_dump() for lab in session.exec(select(LabResult)).all()]


@app.get('/api/tasks')
def tasks(session: Annotated[Session, Depends(get_session)]) -> list[dict[str, Any]]:
    return [task.model_dump() for task in session.exec(select(Task)).all()]


@app.post('/api/tasks/{task_id}/resolve')
def resolve_task(task_id: str, actor: str, session: Annotated[Session, Depends(get_session)]) -> dict[str, Any]:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(404, 'task not found')
    task.status = 'resolved'  # type: ignore[assignment]
    task.resolved_by = actor
    session.add(task)
    session.commit()
    session.refresh(task)
    return task.model_dump()


@app.get('/api/questions')
def questions(session: Annotated[Session, Depends(get_session)]) -> list[dict[str, Any]]:
    return [question.model_dump() for question in session.exec(select(Question)).all()]


@app.get('/api/doctor-prep')
def doctor_prep() -> dict[str, Any]:
    return {'questions': THOMAS_QUESTIONS, 'markdown': 'reports/doctor-prep/thomas-next-visit.md', 'pdf': 'reports/doctor-prep/thomas-next-visit.pdf'}


@app.get('/api/predictions')
def predictions() -> list[dict[str, Any]]:
    return [prediction.__dict__ for prediction in forecast_gaps(load_profile())]


@app.post('/api/observations')
def observation(kind: str, value: str, actor: str, session: Annotated[Session, Depends(get_session)]) -> dict[str, Any]:
    obs = ParentObservation(child_id='thomas', kind=kind, value=value, actor=actor)
    session.add(obs)
    session.commit()
    session.refresh(obs)
    return obs.model_dump()


@app.post('/api/upload')
def upload_record(file: UploadFile, session: Annotated[Session, Depends(get_session)]) -> dict[str, Any]:
    settings = get_settings()
    filename = file.filename or 'upload.bin'
    target = settings.storage_root / 'incoming' / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('wb') as handle:
        handle.write(file.file.read())
    doc = ingest_file(session, 'thomas', target, settings.storage_root)
    return doc.model_dump()


@app.post('/api/alerts/dummy')
def dummy_alert() -> dict[str, Any]:
    rec = RecommendationPayload(
        evidence='dummy local alert test has a source and carries no external PHI by default',
        action='record dummy delivery receipt only',
        urgency='urgent',
        confidence='high',
        source=SourceRef(source_id='TEST', title='Local dummy test', page=1, snippet='dummy local alert', confidence=1),
    )
    return emit_alert(rec, get_settings().external_services).__dict__
