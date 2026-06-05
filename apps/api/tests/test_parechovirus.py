"""Unit tests for the parechovirus symptom catalog and triage engine."""
from __future__ import annotations

import pytest

from app.parechovirus import (
    RULE_PREDICATES,
    SYMPTOM_CATALOG,
    TRIAGE_RULES,
    evaluate_symptoms,
    get_symptom,
    highest_urgency,
)


def test_catalog_has_documented_symptoms() -> None:
    keys = {symptom.key for symptom in SYMPTOM_CATALOG}
    for required in {
        'fever',
        'lethargy',
        'seizure',
        'bulging_fontanelle',
        'apnea',
        'poor_feeding',
        'decreased_wet_diapers',
    }:
        assert required in keys, f'symptom {required!r} missing from catalog'


def test_catalog_entries_have_sources() -> None:
    for symptom in SYMPTOM_CATALOG:
        assert symptom.source_id
        assert symptom.source_title
        assert symptom.snippet
        assert 0 < symptom.confidence <= 1


def test_get_symptom_known_and_unknown() -> None:
    fever = get_symptom('fever')
    assert fever.key == 'fever'
    assert fever.unit == 'C'
    with pytest.raises(KeyError):
        get_symptom('not_a_real_symptom')


def test_seizure_always_triggers_911() -> None:
    result = evaluate_symptoms(
        [{'symptom_key': 'seizure', 'severity': 5, 'measurement_value': 30}]
    )
    assert any(r['rule_key'] == 'parecho_seizure' and r['urgency'] == '911' for r in result)


def test_bulging_fontanelle_is_911() -> None:
    result = evaluate_symptoms(
        [{'symptom_key': 'bulging_fontanelle', 'severity': 5, 'measurement_value': None}]
    )
    assert any(r['rule_key'] == 'parecho_bulging_fontanelle' for r in result)


def test_apnea_severity_4_or_above_triggers_911() -> None:
    result = evaluate_symptoms(
        [{'symptom_key': 'apnea', 'severity': 4, 'measurement_value': 25}]
    )
    assert any(r['rule_key'] == 'parecho_apnea' for r in result)


def test_fever_alone_is_today_not_911() -> None:
    result = evaluate_symptoms(
        [{'symptom_key': 'fever', 'severity': 3, 'measurement_value': 38.5}]
    )
    keys = {r['rule_key'] for r in result}
    assert 'parecho_fever_neonate' in keys
    assert 'parecho_fever_with_lethargy' not in keys
    urgencies = {r['urgency'] for r in result}
    assert urgencies <= {'today'}


def test_fever_plus_lethargy_escalates_to_911() -> None:
    result = evaluate_symptoms(
        [
            {'symptom_key': 'fever', 'severity': 3, 'measurement_value': 38.6},
            {'symptom_key': 'lethargy', 'severity': 3, 'measurement_value': None},
        ]
    )
    keys = {r['rule_key'] for r in result}
    assert 'parecho_fever_with_lethargy' in keys
    assert any(r['urgency'] == '911' for r in result)


def test_hypothermia_below_36_5_triggers_today() -> None:
    result = evaluate_symptoms(
        [{'symptom_key': 'hypothermia', 'severity': 3, 'measurement_value': 36.0}]
    )
    assert any(r['rule_key'] == 'parecho_hypothermia' for r in result)


def test_hypothermia_above_threshold_does_not_fire() -> None:
    result = evaluate_symptoms(
        [{'symptom_key': 'hypothermia', 'severity': 1, 'measurement_value': 36.7}]
    )
    assert all(r['rule_key'] != 'parecho_hypothermia' for r in result)


def test_few_wet_diapers_below_threshold_fires() -> None:
    result = evaluate_symptoms(
        [{'symptom_key': 'decreased_wet_diapers', 'severity': 3, 'measurement_value': 2}]
    )
    assert any(r['rule_key'] == 'parecho_few_wet_diapers' for r in result)


def test_persistent_irritability_threshold() -> None:
    short = evaluate_symptoms(
        [{'symptom_key': 'irritability', 'severity': 2, 'measurement_value': 30}]
    )
    long = evaluate_symptoms(
        [{'symptom_key': 'irritability', 'severity': 2, 'measurement_value': 90}]
    )
    assert all(r['rule_key'] != 'parecho_persistent_irritability' for r in short)
    assert any(r['rule_key'] == 'parecho_persistent_irritability' for r in long)


def test_rash_with_fever_is_soon() -> None:
    result = evaluate_symptoms(
        [
            {'symptom_key': 'rash', 'severity': 2, 'measurement_value': None},
            {'symptom_key': 'fever', 'severity': 2, 'measurement_value': 38.1},
        ]
    )
    keys = {r['rule_key'] for r in result}
    assert 'parecho_rash_with_fever' in keys


def test_no_symptoms_means_no_triage() -> None:
    assert evaluate_symptoms([]) == []


def test_each_rule_has_a_predicate() -> None:
    for rule in TRIAGE_RULES:
        assert rule.key in RULE_PREDICATES, f'rule {rule.key} has no predicate'


def test_highest_urgency_picks_max() -> None:
    assert highest_urgency(['routine', 'today', 'urgent']) == 'urgent'
    assert highest_urgency(['watch', 'soon']) == 'soon'
    assert highest_urgency([]) == 'routine'
