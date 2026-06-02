from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import NormalDist
from typing import Any


@dataclass(frozen=True)
class MeasurementInput:
    kind: str
    value: float
    unit: str
    measured_at: str
    actor: str


# Compact committed LMS anchors for Thomas's current newborn window. Values are sourced
# from WHO male 0-24 month LMS tables and linearly interpolated by age in this app.
# The independent test fixture stores expected percentile outputs separately so tests do
# not assert this table against itself.
MALE_WHO_LMS: dict[str, list[tuple[float, float, float, float]]] = {
    'weight_kg': [
        (0.0, 0.3487, 3.3464, 0.14602),
        (14.0, 0.2297, 3.9273, 0.13820),
        (30.4375, 0.1970, 4.4709, 0.13395),
        (60.875, 0.1738, 5.5675, 0.12385),
        (91.3125, 0.1553, 6.3762, 0.11727),
        (182.625, 0.1395, 7.9340, 0.10881),
        (365.25, 0.0922, 9.6479, 0.10163),
        (547.875, 0.0460, 10.9415, 0.09575),
        (730.5, 0.0270, 12.1515, 0.09036),
    ],
    'length_cm': [
        (0.0, 1.0, 49.8842, 0.03795),
        (14.0, 1.0, 53.0502, 0.03644),
        (30.4375, 1.0, 54.7244, 0.03557),
        (60.875, 1.0, 58.4249, 0.03424),
        (91.3125, 1.0, 61.4292, 0.03328),
        (182.625, 1.0, 67.6236, 0.03137),
        (365.25, 1.0, 75.7488, 0.02996),
        (547.875, 1.0, 82.2587, 0.02933),
        (730.5, 1.0, 87.1161, 0.02907),
    ],
    'head_cm': [
        (0.0, 1.0, 34.4618, 0.03686),
        (14.0, 1.0, 36.1390, 0.03495),
        (30.4375, 1.0, 37.2759, 0.03377),
        (60.875, 1.0, 39.1285, 0.03204),
        (91.3125, 1.0, 40.5135, 0.03090),
        (182.625, 1.0, 43.3306, 0.02876),
        (365.25, 1.0, 46.0661, 0.02668),
        (547.875, 1.0, 47.4819, 0.02561),
        (730.5, 1.0, 48.5629, 0.02496),
    ],
}

KIND_TO_STANDARD = {'weight': 'weight_kg', 'length': 'length_cm', 'head': 'head_cm'}


def load_independent_fixture(path: Path) -> dict[tuple[str, float, float], float]:
    rows = json.loads(path.read_text())
    return {(row['kind'], float(row['age_days']), float(row['value'])): float(row['expected_percentile']) for row in rows}


def _interpolate(kind: str, age_days: float) -> tuple[float, float, float]:
    anchors = MALE_WHO_LMS[kind]
    if age_days <= anchors[0][0]:
        return anchors[0][1], anchors[0][2], anchors[0][3]
    if age_days >= anchors[-1][0]:
        return anchors[-1][1], anchors[-1][2], anchors[-1][3]
    for left, right in zip(anchors, anchors[1:], strict=False):
        if left[0] <= age_days <= right[0]:
            span = right[0] - left[0]
            fraction = (age_days - left[0]) / span
            return tuple(left[index] + fraction * (right[index] - left[index]) for index in (1, 2, 3))  # type: ignore[return-value]
    return anchors[-1][1], anchors[-1][2], anchors[-1][3]


def lms_z_score(*, kind: str, sex: str, age_days: float, value: float) -> float:
    if sex != 'male':
        raise ValueError('Child Health Dashboard v2 currently commits only male WHO LMS curves for Thomas')
    if kind not in MALE_WHO_LMS:
        raise ValueError(f'unsupported WHO LMS kind: {kind}')
    l_value, median, sigma = _interpolate(kind, age_days)
    if l_value == 0:
        return math.log(value / median) / sigma
    return ((value / median) ** l_value - 1) / (l_value * sigma)


def lms_percentile(*, kind: str, sex: str, age_days: float, value: float) -> float:
    z = lms_z_score(kind=kind, sex=sex, age_days=age_days, value=value)
    return round(NormalDist().cdf(z) * 100, 1)


def _age_days(dob: str, measured_at: str) -> float:
    return float((date.fromisoformat(measured_at) - date.fromisoformat(dob)).days)


def _normalize_value(measurement: MeasurementInput) -> tuple[str, float, str]:
    unit = measurement.unit.lower()
    if measurement.kind == 'weight':
        kg = measurement.value * 0.45359237 if unit in {'lb', 'lbs', 'pound', 'pounds'} else measurement.value
        return 'weight_kg', kg, 'kg'
    if measurement.kind in {'length', 'head'}:
        cm = measurement.value * 2.54 if unit in {'in', 'inch', 'inches'} else measurement.value
        return KIND_TO_STANDARD[measurement.kind], cm, 'cm'
    raise ValueError(f'unsupported measurement kind: {measurement.kind}')


def compute_growth_snapshot(measurements: list[MeasurementInput], *, sex: str, dob: str) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    percentiles: dict[str, dict[str, Any]] = {}
    for measurement in measurements:
        standard_kind, value, unit = _normalize_value(measurement)
        age = _age_days(dob, measurement.measured_at)
        percentile = lms_percentile(kind=standard_kind, sex=sex, age_days=age, value=value)
        display_kind = measurement.kind
        row: dict[str, Any] = {
            'kind': display_kind,
            'measured_at': measurement.measured_at,
            'actor': measurement.actor,
            'raw_value': f'{measurement.value:g} {measurement.unit}',
            'unit': unit,
            'age_days': age,
            'percentile': percentile,
            'source': 'parent-entered measurement',
        }
        if unit == 'kg':
            row['value_kg'] = round(value, 3)
        else:
            row['value_cm'] = round(value, 3)
        normalized.append(row)
        label = f'tracking along the ~{round(percentile):.0f}th percentile'
        percentiles[display_kind if display_kind != 'head' else 'head'] = {
            'percentile': percentile,
            'label': label,
            'source': 'WHO male LMS fixture',
            'confidence': 'high',
        }
    return {
        'standard': 'WHO-0-24-months-male-LMS',
        'measurements': normalized,
        'percentiles': percentiles,
        'projection': 'points_only_no_projection' if len(measurements) < 4 else 'bounded_trend_available',
    }
