
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA_PATH = Path(__file__).with_name('data') / 'aap2022_thresholds.json'


@dataclass(frozen=True)
class BilirubinPoint:
    hours: float
    bilirubin_mg_dl: float
    test: str
    source: str
    direct_mg_dl: float | None = None


@dataclass(frozen=True)
class BilirubinAssessment:
    status: str
    threshold_mg_dl: float | None
    delta_mg_dl: float | None
    interpretation: str
    source_citation: str
    risk_curve: str


def load_threshold_data() -> dict:
    return json.loads(DATA_PATH.read_text())


def gestational_week(value: str | float | int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value)
    text = value.lower().replace(' ', '')
    if 'w' in text:
        weeks = int(text.split('w')[0])
        days = 0
        if 'd' in text:
            after = text.split('w', 1)[1]
            days = int(after.split('d')[0] or 0)
        return weeks + (1 if days >= 4 else 0)
    return round(float(text))


def threshold_at(gestational_age: str | float | int, hours: float, neurotoxicity_risk: bool) -> BilirubinAssessment:
    data = load_threshold_data()
    ga = max(35, min(40, gestational_week(gestational_age)))
    valid_hours = data['hours']
    citation = data['citation']
    if hours < min(valid_hours) or hours > max(valid_hours):
        return BilirubinAssessment(
            status='needs_confirmation',
            threshold_mg_dl=None,
            delta_mg_dl=None,
            interpretation='not computable from available AAP-2022 table range; ask pediatrician',
            source_citation=citation,
            risk_curve='with-risk-factors' if neurotoxicity_risk else 'no-risk-factors',
        )
    risk_key = 'any' if neurotoxicity_risk else 'none'
    values = data['phototherapy_mg_dl'][str(ga)][risk_key]
    for idx, hour in enumerate(valid_hours):
        if hours == hour:
            threshold = values[idx]
            break
        if hours < hour:
            lower_hour = valid_hours[idx - 1]
            upper_hour = hour
            lower_value = values[idx - 1]
            upper_value = values[idx]
            fraction = (hours - lower_hour) / (upper_hour - lower_hour)
            threshold = round(lower_value + (upper_value - lower_value) * fraction, 2)
            break
    else:
        threshold = values[-1]
    return BilirubinAssessment(
        status='computed',
        threshold_mg_dl=threshold,
        delta_mg_dl=None,
        interpretation='AAP-2022 phototherapy threshold computed by hour of life and risk curve',
        source_citation=citation,
        risk_curve='with-risk-factors' if neurotoxicity_risk else 'no-risk-factors',
    )


def assess(point: BilirubinPoint, gestational_age: str, dat_positive: bool) -> BilirubinAssessment:
    base = threshold_at(gestational_age, point.hours, neurotoxicity_risk=dat_positive)
    if base.threshold_mg_dl is None:
        return base
    delta = round(base.threshold_mg_dl - point.bilirubin_mg_dl, 2)
    if delta <= 0:
        interpretation = 'at or above AAP-2022 phototherapy threshold; contact pediatrician/urgent care now'
        status = 'urgent'
    elif delta <= 3:
        interpretation = 'close to AAP-2022 phototherapy threshold; arrange pediatrician-directed repeat bilirubin'
        status = 'watch'
    else:
        interpretation = 'below threshold, but continue pediatrician follow-up; do not use this as reassurance to defer care'
        status = 'routine'
    return BilirubinAssessment(
        status=status,
        threshold_mg_dl=base.threshold_mg_dl,
        delta_mg_dl=delta,
        interpretation=interpretation,
        source_citation=base.source_citation,
        risk_curve=base.risk_curve,
    )


def threshold_curve(gestational_age: str, neurotoxicity_risk: bool) -> list[dict[str, float]]:
    data = load_threshold_data()
    return [
        {
            'hour': float(hour),
            'threshold_mg_dl': threshold_at(gestational_age, float(hour), neurotoxicity_risk).threshold_mg_dl or 0.0,
        }
        for hour in data['hours']
    ]


def is_flat_curve(points: list[dict[str, float]]) -> bool:
    return len({round(point['threshold_mg_dl'], 2) for point in points}) <= 1
