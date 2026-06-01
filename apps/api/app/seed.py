
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from .config import SEED_ROOT
from .db import engine, init_db
from .doctor_prep import generate_markdown, generate_minimal_pdf
from .extraction import run_default_extraction_report
from .models import (
    Child,
    Condition,
    Encounter,
    LabResult,
    Measurement,
    Question,
    RiskSignal,
    SourceDocument,
    Task,
    VaccineEvent,
)
from .normalization import age_days, normalize_lab_name, percent_weight_change
from .red_flags import load_thomas_rules


def _upsert(session: Session, obj: Any) -> None:
    existing = session.get(type(obj), obj.id)
    if existing is None:
        session.add(obj)


def load_profile(seed_root: Path = SEED_ROOT) -> dict[str, Any]:
    return json.loads((seed_root / 'data' / 'structured_profile.json').read_text())


def import_thomas_seed(seed_root: Path = SEED_ROOT) -> dict[str, int]:
    init_db()
    profile = load_profile(seed_root)
    counts: dict[str, int] = {}
    with Session(engine) as session:
        child = session.exec(select(Child).where(Child.name == profile['patient']['name'])).first()
        if child is None:
            child = Child(id='thomas', name=profile['patient']['name'], dob=profile['patient']['dob'], sex=profile['patient']['sex'], pcp=profile['patient']['pcp'])
            session.add(child)
        session.commit()
        manifest_path = seed_root / 'data' / 'source_manifest.csv'
        with manifest_path.open(newline='') as handle:
            for row in csv.DictReader(handle):
                doc = SourceDocument(
                    id=row['source_id'],
                    child_id=child.id,
                    relative_path=row['relative_path'],
                    file_name=row['file_name'],
                    sha256=row['sha256'],
                    bytes=int(row['bytes'] or 0),
                    pages=int(row['pages'] or 0),
                    text_chars=int(row['text_chars'] or 0),
                    extraction_method=row['extraction_method'],
                    extraction_quality=row['extraction_quality'],
                    categories=row['inferred_categories'],
                    output_text_path=row['output_text_path'],
                )
                _upsert(session, doc)
        conditions = [
            ('parechovirus-meningitis', 'Parechovirus meningitis / neonatal fever admission', 'watching', 'major', 'Parechovirus detected in CSF; fever resolved by discharge.', 'Confirm final cultures; enhanced developmental watch.', 'SRC-010', 1, 'Parechovirus detected in CSF'),
            ('jaundice-abo-dat', 'Jaundice due to ABO isoimmunization / DAT-positive ABO incompatibility', 'watching', 'major', 'ABO incompatibility and DAT positive.', 'Use AAP-2022 risk-factor bilirubin curve; ask about anemia follow-up.', 'SRC-001', 5, 'Direct Antiglob-Cord POS'),
            ('torticollis', 'Congenital torticollis / right head preference', 'active', 'minor', 'Right head tilt noted in newborn record.', 'Continue stretches; ask if PT is needed.', 'SRC-001', 5, 'mild right torticollis'),
            ('left-pinna-fold', 'Left pinna fold / ear deformity referral', 'active', 'minor', 'Left pinna fold noted in newborn record.', 'Ask about plastics/taping timing.', 'SRC-001', 5, 'Left pinna fold'),
            ('hepb-deferred', 'Hepatitis B vaccine deferred', 'open', 'major', 'Hep B deferred in structured newborn profile.', 'Ask pediatrician for catch-up plan.', 'SRC-015', 1, 'Hepatitis B'),
            ('feeding-hydration-watch', 'Feeding and hydration watch after discharge', 'watching', 'major', 'Discharge instructions give wet diaper and feeding red flags.', 'Use one-tap feed/diaper logging and source-driven red-flag rules.', 'SRC-003', 2, 'Less than 4 wet diapers in 24 hours'),
        ]
        for cid, name, status, severity, evidence, next_action, src, page, snippet in conditions:
            _upsert(session, Condition(id=cid, child_id=child.id, name=name, status=status, severity=severity, evidence=evidence, watch_items=next_action, next_action=next_action, source_document_id=src, page=page, snippet=snippet, confidence=0.95))
        for idx, weight in enumerate(profile['growth_feeding']['weights']):
            _upsert(session, Measurement(id=f'weight-{idx}', child_id=child.id, measured_at=weight['date'], kind='weight', value=float(weight['kg']), unit='kg', raw_value=f"{weight['kg']} kg", age_days=age_days(profile['patient']['dob'], weight['date']), source_document_id='structured-profile', page=1, snippet=json.dumps(weight), confidence=0.9))
        birth_weight = profile['birth_history']['birth_weight_kg']
        for idx, value in enumerate(profile['blood_type_jaundice']['bilirubin_values']):
            numeric = float(str(value['value']).split()[0])
            _upsert(session, LabResult(id=f'bilirubin-{idx}', child_id=child.id, collected_at=value['date'], lab_name=normalize_lab_name(value['test']), value=numeric, unit='mg/dL', raw_value=value['value'], age_days=age_days(profile['patient']['dob'], value['date']), source_document_id='SRC-018' if idx in {1, 3} else 'structured-profile', page=1, snippet=json.dumps(value), confidence=0.9))
        _upsert(session, Encounter(id='birth', child_id=child.id, date='2026-05-17', category='birth_newborn', summary='Term birth, DAT-positive ABO incompatibility watch.', source_document_id='SRC-001', page=1, snippet='ABO incompatibility, DAT Positive', confidence=0.95))
        _upsert(session, Encounter(id='fever-admission', child_id=child.id, date='2026-05-29', category='ER/hospitalization', summary='Neonatal fever admission; parechovirus meningitis; discharged 2026-05-31.', source_document_id='SRC-003', page=1, snippet='admitted to the hospital with a fever', confidence=0.98))
        rules = load_thomas_rules(seed_root)
        for rule in rules:
            _upsert(session, RiskSignal(id=f'risk-{rule.key}', child_id=child.id, key=rule.key, urgency=rule.urgency, evidence=rule.label, source_document_id=rule.source_id, page=rule.page, snippet=rule.snippet, confidence=rule.confidence))
        tasks = [
            ('task-pcp-follow-up', 'PCP follow-up after fever admission', 'today', 'SRC-003', 2, 'Please see your pediatrician on 6/1/26'),
            ('task-hepb-catch-up', 'Ask for Hep B catch-up plan', 'soon', 'SRC-015', 1, 'Hepatitis B'),
            ('task-culture-final', 'Confirm blood/CSF/urine cultures final', 'soon', 'SRC-008', 1, 'Cultures remain no growth'),
            ('task-red-flag-reference', 'Keep discharge red flags offline', 'urgent', 'SRC-003', 2, 'Less than 4 wet diapers in 24 hours'),
        ]
        for tid, title, urgency, src, page, snippet in tasks:
            _upsert(session, Task(id=tid, child_id=child.id, title=title, urgency=urgency, source_document_id=src, page=page, snippet=snippet))
        _upsert(session, VaccineEvent(id='vax-hepb-deferred', child_id=child.id, vaccine='Hepatitis B', status='deferred', reason='Deferred by family at newborn discharge/first office visit; needs pediatrician plan.', source_document_id='structured-profile', page=1, snippet=profile['screenings_immunizations']['hepatitis_b'], confidence=0.9))
        from .doctor_prep import THOMAS_QUESTIONS
        for idx, question in enumerate(THOMAS_QUESTIONS, start=1):
            _upsert(session, Question(id=f'question-{idx}', child_id=child.id, question=question, source_document_id='structured-profile', page=1, snippet='pre-built Thomas next-visit question'))
        session.commit()
        counts['sources'] = len(session.exec(select(SourceDocument)).all())
        counts['conditions'] = len(session.exec(select(Condition)).all())
        counts['weights'] = len(session.exec(select(Measurement)).all())
        counts['labs'] = len(session.exec(select(LabResult)).all())
        counts['tasks'] = len(session.exec(select(Task)).all())
        counts['questions'] = len(session.exec(select(Question)).all())
        counts['weight_birth_change_last_pct'] = int(percent_weight_change(profile['growth_feeding']['weights'][-1]['kg'], birth_weight) * 10)
    project_root = Path(__file__).resolve().parents[3]
    generate_markdown(project_root / 'reports' / 'doctor-prep')
    generate_minimal_pdf(project_root / 'reports' / 'doctor-prep')
    run_default_extraction_report(project_root, seed_root)
    return counts


if __name__ == '__main__':
    print(json.dumps(import_thomas_seed(), indent=2))
