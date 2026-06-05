"""Parechovirus symptom catalog and triage rule engine.

This module is the source of truth for:
- which symptoms a parent can log for the child
- which combinations of symptoms escalate to call the pediatrician,
  seek urgent care, or call 911
- the evidence and source backing each rule

The rules here are written to match the AAP / IDSA / CDC guidance for
human parechovirus (HPeV) infection in neonates and young infants and
the discharge instructions Thomas received on May 31 2026. They are
intentionally conservative: any doubt escalates.

Triage outputs are intentionally structured the same way as
``recommendations.RecommendationPayload`` so they can flow straight into
the dashboard.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


# ---------------------------------------------------------------------------
# Symptom catalog
# ---------------------------------------------------------------------------


class SymptomCategory(StrEnum):
    SYSTEMIC = 'systemic'
    NEURO = 'neurologic'
    FEEDING = 'feeding'
    RESPIRATORY = 'respiratory'
    SKIN = 'skin'
    GI = 'gastrointestinal'


class MeasurementKind(StrEnum):
    NONE = 'none'
    TEMPERATURE_C = 'temperature_c'
    DURATION_MIN = 'duration_minutes'
    COUNT = 'count'


@dataclass(frozen=True)
class SymptomDef:
    """A single symptom that a parent can log."""

    key: str
    label: str
    category: SymptomCategory
    severity_min: int  # 1 = mild, 5 = emergency
    severity_max: int
    measurement: MeasurementKind
    unit: str | None
    description: str
    """What this symptom looks like / when to log it."""
    parent_prompt: str
    """Question shown to the parent in the logging UI."""
    source_id: str
    source_title: str
    page: int | None
    snippet: str
    confidence: float


SYMPTOM_CATALOG: tuple[SymptomDef, ...] = (
    SymptomDef(
        key='fever',
        label='Fever (measured)',
        category=SymptomCategory.SYSTEMIC,
        severity_min=2,
        severity_max=5,
        measurement=MeasurementKind.TEMPERATURE_C,
        unit='C',
        description='A measured rectal or axillary temperature at or above 38.0 C (100.4 F).',
        parent_prompt='What was the measured temperature?',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='call your pediatrician for fevers reaching 38.0 c or above',
        confidence=0.99,
    ),
    SymptomDef(
        key='hypothermia',
        label='Low temperature (measured)',
        category=SymptomCategory.SYSTEMIC,
        severity_min=2,
        severity_max=5,
        measurement=MeasurementKind.TEMPERATURE_C,
        unit='C',
        description='A measured temperature below 36.5 C (97.7 F), or any reading that feels cold to the touch with poor color.',
        parent_prompt='What was the measured temperature?',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='seek medical attention ... if your baby has a low temperature',
        confidence=0.95,
    ),
    SymptomDef(
        key='lethargy',
        label='Lethargy / decreased activity',
        category=SymptomCategory.NEURO,
        severity_min=2,
        severity_max=5,
        measurement=MeasurementKind.NONE,
        unit=None,
        description='Hard to wake, not making eye contact, not moving normally, or not responding to you the way Thomas usually does.',
        parent_prompt='How hard was it to wake or engage Thomas?',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='Lethargy/Decreased activity',
        confidence=0.97,
    ),
    SymptomDef(
        key='irritability',
        label='Inconsolable crying / irritability',
        category=SymptomCategory.NEURO,
        severity_min=1,
        severity_max=3,
        measurement=MeasurementKind.DURATION_MIN,
        unit='min',
        description='Crying that cannot be soothed by feeding, holding, or diaper change, especially if high-pitched.',
        parent_prompt='How long did the inconsolable crying last?',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='fussiness, crying more than usual',
        confidence=0.9,
    ),
    SymptomDef(
        key='seizure',
        label='Seizure activity',
        category=SymptomCategory.NEURO,
        severity_min=5,
        severity_max=5,
        measurement=MeasurementKind.DURATION_MIN,
        unit='min',
        description='Rhythmic shaking of arms or legs that does not stop with holding, or any episode of staring with no response. Always emergent.',
        parent_prompt='How long did the episode last?',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='call 911 immediately if ... seizure',
        confidence=0.99,
    ),
    SymptomDef(
        key='bulging_fontanelle',
        label='Bulging soft spot (fontanelle)',
        category=SymptomCategory.NEURO,
        severity_min=5,
        severity_max=5,
        measurement=MeasurementKind.NONE,
        unit=None,
        description='The soft spot on top of the head looks or feels tight, raised, or bulging. Possible sign of meningitis/encephalitis.',
        parent_prompt='Did the soft spot look or feel raised or tight?',
        source_id='SRC-010',
        source_title='CSF Meningitis / Encephalitis PCR Panel',
        page=1,
        snippet='Parechovirus detected in CSF',
        confidence=0.95,
    ),
    SymptomDef(
        key='poor_feeding',
        label='Difficulty feeding / poor intake',
        category=SymptomCategory.FEEDING,
        severity_min=1,
        severity_max=3,
        measurement=MeasurementKind.DURATION_MIN,
        unit='min',
        description='Refusing bottles, taking much less than usual, or tiring out partway through feeds. Track how long the pattern has been going on.',
        parent_prompt='How long has poor feeding been going on?',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='Difficulty feeding',
        confidence=0.97,
    ),
    SymptomDef(
        key='apnea',
        label='Apnea (pauses in breathing)',
        category=SymptomCategory.RESPIRATORY,
        severity_min=4,
        severity_max=5,
        measurement=MeasurementKind.DURATION_MIN,
        unit='sec',
        description='Pauses in breathing longer than ~20 seconds, color change, or needing stimulation to start breathing again.',
        parent_prompt='How long did the pause last (in seconds)?',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='seek medical attention ... apnea or color change',
        confidence=0.95,
    ),
    SymptomDef(
        key='rash',
        label='New rash',
        category=SymptomCategory.SKIN,
        severity_min=1,
        severity_max=3,
        measurement=MeasurementKind.NONE,
        unit=None,
        description='Any new rash, especially if it spreads, has blisters, or appears with fever.',
        parent_prompt='Where is the rash and what does it look like?',
        source_id='SRC-010',
        source_title='CSF Meningitis / Encephalitis PCR Panel',
        page=1,
        snippet='Parechovirus frequently presents with rash',
        confidence=0.85,
    ),
    SymptomDef(
        key='diarrhea',
        label='Diarrhea / loose stools',
        category=SymptomCategory.GI,
        severity_min=1,
        severity_max=3,
        measurement=MeasurementKind.COUNT,
        unit='stools',
        description='Looser or more frequent stools than his baseline. Track the count over the day.',
        parent_prompt='How many loose stools in the last 24 hours?',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='Fewer wet diapers ... may indicate dehydration',
        confidence=0.8,
    ),
    SymptomDef(
        key='vomiting',
        label='Vomiting',
        category=SymptomCategory.GI,
        severity_min=1,
        severity_max=3,
        measurement=MeasurementKind.COUNT,
        unit='episodes',
        description='Forceful or repeated vomiting, especially if it prevents keeping feeds down.',
        parent_prompt='How many vomiting episodes in the last 24 hours?',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='Vomiting',
        confidence=0.85,
    ),
    SymptomDef(
        key='decreased_wet_diapers',
        label='Fewer wet diapers than discharge threshold',
        category=SymptomCategory.GI,
        severity_min=3,
        severity_max=3,
        measurement=MeasurementKind.COUNT,
        unit='diapers/24h',
        description='Fewer than the source-driven threshold of wet diapers in 24 hours (per discharge instructions).',
        parent_prompt='How many wet diapers in the last 24 hours?',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='Less than 4 wet diapers in 24 hours',
        confidence=0.99,
    ),
)


def get_symptom(key: str) -> SymptomDef:
    for symptom in SYMPTOM_CATALOG:
        if symptom.key == key:
            return symptom
    raise KeyError(f'Unknown symptom: {key!r}')


# ---------------------------------------------------------------------------
# Triage rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TriageRule:
    """A single escalation rule for parechovirus symptoms.

    ``match`` is a callable that receives a list of logged symptoms
    (each as a dict with the keys ``symptom_key``, ``severity`` and
    ``measurement_value``) and returns True when the rule fires.
    """

    key: str
    label: str
    urgency: str  # routine | watch | soon | today | urgent | 911
    action: str
    source_id: str
    source_title: str
    page: int | None
    snippet: str
    confidence: float


def _symptom_value(symptoms: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    for symptom in symptoms:
        if symptom.get('symptom_key') == key:
            return symptom
    return None


def _has_severity_at_least(symptoms: list[dict[str, Any]], key: str, level: int) -> bool:
    entry = _symptom_value(symptoms, key)
    if entry is None:
        return False
    return int(entry.get('severity', 0)) >= level


# Rule predicates. Each returns True if the rule should fire.


def _rule_seizure(symptoms: list[dict[str, Any]]) -> bool:
    return _symptom_value(symptoms, 'seizure') is not None


def _rule_apnea(symptoms: list[dict[str, Any]]) -> bool:
    entry = _symptom_value(symptoms, 'apnea')
    if entry is None:
        return False
    return int(entry.get('severity', 0)) >= 4


def _rule_bulging_fontanelle(symptoms: list[dict[str, Any]]) -> bool:
    return _symptom_value(symptoms, 'bulging_fontanelle') is not None


def _rule_fever_neonate_with_lethargy(symptoms: list[dict[str, Any]]) -> bool:
    fever = _symptom_value(symptoms, 'fever')
    if fever is None:
        return False
    if float(fever.get('measurement_value') or 0) < 38.0:
        return False
    return _has_severity_at_least(symptoms, 'lethargy', 3)


def _rule_fever_infant_under_three_months(symptoms: list[dict[str, Any]]) -> bool:
    fever = _symptom_value(symptoms, 'fever')
    if fever is None:
        return False
    return float(fever.get('measurement_value') or 0) >= 38.0


def _rule_hypothermia(symptoms: list[dict[str, Any]]) -> bool:
    entry = _symptom_value(symptoms, 'hypothermia')
    if entry is None:
        return False
    return float(entry.get('measurement_value') or 99) < 36.5


def _rule_few_wet_diapers(symptoms: list[dict[str, Any]]) -> bool:
    entry = _symptom_value(symptoms, 'decreased_wet_diapers')
    if entry is None:
        return False
    return int(entry.get('measurement_value') or 99) < 4


def _rule_poor_feeding_plus_lethargy(symptoms: list[dict[str, Any]]) -> bool:
    return _symptom_value(symptoms, 'poor_feeding') is not None and _has_severity_at_least(
        symptoms, 'lethargy', 2
    )


def _rule_persistent_irritability(symptoms: list[dict[str, Any]]) -> bool:
    entry = _symptom_value(symptoms, 'irritability')
    if entry is None:
        return False
    if int(entry.get('severity', 0)) < 2:
        return False
    return int(entry.get('measurement_value') or 0) >= 60


def _rule_rash_with_fever(symptoms: list[dict[str, Any]]) -> bool:
    return _symptom_value(symptoms, 'rash') is not None and _symptom_value(
        symptoms, 'fever'
    ) is not None


TRIAGE_RULES: tuple[TriageRule, ...] = (
    TriageRule(
        key='parecho_seizure',
        label='Seizure activity',
        urgency='911',
        action='Call 911 immediately and ask for a pediatric-capable team.',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='call 911 immediately if ... seizure',
        confidence=0.99,
    ),
    TriageRule(
        key='parecho_apnea',
        label='Apnea or color change',
        urgency='911',
        action='Stimulate gently; if not breathing normally within seconds, call 911 and start infant CPR if trained.',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='seek medical attention from the pediatrician, urgent care, or emergency department now',
        confidence=0.97,
    ),
    TriageRule(
        key='parecho_bulging_fontanelle',
        label='Bulging soft spot',
        urgency='911',
        action='Go to the emergency department now; possible meningitis/encephalitis.',
        source_id='SRC-010',
        source_title='CSF Meningitis / Encephalitis PCR Panel',
        page=1,
        snippet='Parechovirus detected in CSF',
        confidence=0.96,
    ),
    TriageRule(
        key='parecho_fever_with_lethargy',
        label='Fever (>=38.0 C) with lethargy in a neonate',
        urgency='911',
        action='Go to the emergency department now; combination is a red flag in infants under 3 months.',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='Lethargy/Decreased activity',
        confidence=0.95,
    ),
    TriageRule(
        key='parecho_fever_neonate',
        label='Fever >=38.0 C in infant under 3 months',
        urgency='today',
        action='Call the pediatrician now; any fever in a neonate needs same-day evaluation per AAP guidance.',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='call your pediatrician for fevers reaching 38.0 c or above',
        confidence=0.99,
    ),
    TriageRule(
        key='parecho_hypothermia',
        label='Low temperature (<36.5 C)',
        urgency='today',
        action='Warm Thomas with skin-to-skin and call the pediatrician; a low reading in a neonate warrants same-day evaluation.',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='low temperature',
        confidence=0.95,
    ),
    TriageRule(
        key='parecho_few_wet_diapers',
        label='Fewer than 4 wet diapers in 24 hours',
        urgency='urgent',
        action='Seek medical attention from the pediatrician, urgent care, or emergency department now.',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='Less than 4 wet diapers in 24 hours',
        confidence=0.99,
    ),
    TriageRule(
        key='parecho_poor_feeding_plus_lethargy',
        label='Poor feeding with lethargy',
        urgency='urgent',
        action='Call the pediatrician now and plan for urgent evaluation; combination suggests dehydration or worsening illness.',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='Difficulty feeding ... Lethargy/Decreased activity',
        confidence=0.9,
    ),
    TriageRule(
        key='parecho_persistent_irritability',
        label='Inconsolable crying >=60 min',
        urgency='soon',
        action='Call the pediatrician within the next few hours; persistent inconsolable crying needs a same-day check.',
        source_id='SRC-003',
        source_title='ER AVS May 31 2026',
        page=2,
        snippet='fussiness, crying more than usual',
        confidence=0.85,
    ),
    TriageRule(
        key='parecho_rash_with_fever',
        label='New rash with fever',
        urgency='soon',
        action='Call the pediatrician; a rash that arrives with fever can signal viral spread and warrants a check.',
        source_id='SRC-010',
        source_title='CSF Meningitis / Encephalitis PCR Panel',
        page=1,
        snippet='Parechovirus frequently presents with rash',
        confidence=0.8,
    ),
)


RULE_PREDICATES: dict[str, Any] = {
    'parecho_seizure': _rule_seizure,
    'parecho_apnea': _rule_apnea,
    'parecho_bulging_fontanelle': _rule_bulging_fontanelle,
    'parecho_fever_with_lethargy': _rule_fever_neonate_with_lethargy,
    'parecho_fever_neonate': _rule_fever_infant_under_three_months,
    'parecho_hypothermia': _rule_hypothermia,
    'parecho_few_wet_diapers': _rule_few_wet_diapers,
    'parecho_poor_feeding_plus_lethargy': _rule_poor_feeding_plus_lethargy,
    'parecho_persistent_irritability': _rule_persistent_irritability,
    'parecho_rash_with_fever': _rule_rash_with_fever,
}


def evaluate_symptoms(symptoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run every triage rule against ``symptoms`` and return all that fire.

    Each result is a dict with the rule fields plus ``rule_key`` so the
    caller can correlate it back to the source rule and to a persisted
    ``ParechovirusTriageIssue``.
    """
    triggered: list[dict[str, Any]] = []
    for rule in TRIAGE_RULES:
        predicate = RULE_PREDICATES[rule.key]
        if not predicate(symptoms):
            continue
        evidence = _build_evidence(rule.key, symptoms)
        triggered.append(
            {
                'rule_key': rule.key,
                'label': rule.label,
                'urgency': rule.urgency,
                'action': rule.action,
                'evidence': evidence,
                'source_id': rule.source_id,
                'source_title': rule.source_title,
                'page': rule.page,
                'snippet': rule.snippet,
                'confidence': rule.confidence,
            }
        )
    return triggered


def _build_evidence(rule_key: str, symptoms: list[dict[str, Any]]) -> str:
    keys = sorted({s.get('symptom_key', 'unknown') for s in symptoms})
    base = f"triage rule {rule_key} fired for symptoms: {', '.join(keys)}"
    fever = _symptom_value(symptoms, 'fever')
    if fever is not None and rule_key.startswith('parecho_fever'):
        base += f" (measured {fever.get('measurement_value')} C, severity {fever.get('severity')})"
    return base


def highest_urgency(urgencies: list[str]) -> str:
    """Pick the most severe urgency from a list, for top-of-page summary."""
    order = ['routine', 'watch', 'soon', 'today', 'urgent', '911']
    for level in reversed(order):
        if level in urgencies:
            return level
    return 'routine'
