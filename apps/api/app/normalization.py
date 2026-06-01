
from __future__ import annotations

from datetime import date, datetime

LAB_SYNONYMS = {
    'tsb': 'bilirubin_total',
    'total bilirubin': 'bilirubin_total',
    'bilirubin, total': 'bilirubin_total',
    'poct t bilirubin transcut': 'transcutaneous_bilirubin',
    'tcb': 'transcutaneous_bilirubin',
    'hgb': 'hemoglobin',
    'hemoglobin': 'hemoglobin',
    'hct': 'hematocrit',
    'hematocrit': 'hematocrit',
    'rbc': 'rbc',
    'reticulocytes': 'reticulocytes',
    'crp': 'c_reactive_protein',
    'c reactive protein': 'c_reactive_protein',
    'procalcitonin': 'procalcitonin',
}

NEONATAL_REFERENCE_BANDS = {
    'hemoglobin': [(0, 7, 13.5, 21.5), (8, 30, 10.0, 20.0), (31, 60, 9.4, 16.6)],
    'hematocrit': [(0, 7, 42.0, 65.0), (8, 30, 31.0, 55.0), (31, 60, 28.0, 42.0)],
    'rbc': [(0, 7, 3.9, 5.9), (8, 30, 3.0, 5.4), (31, 60, 2.7, 4.9)],
    'reticulocytes': [(0, 7, 1.0, 6.0), (8, 30, 0.5, 3.0), (31, 60, 0.5, 2.5)],
}


def normalize_lab_name(name: str) -> str:
    key = name.strip().lower()
    return LAB_SYNONYMS.get(key, key.replace(' ', '_').replace(',', ''))


def convert_unit(value: float, from_unit: str, to_unit: str) -> float:
    pair = (from_unit.lower(), to_unit.lower())
    if pair[0] == pair[1]:
        return value
    if pair == ('kg', 'g'):
        return value * 1000
    if pair == ('g', 'kg'):
        return value / 1000
    if pair == ('lb', 'kg'):
        return value * 0.45359237
    if pair == ('f', 'c'):
        return (value - 32) * 5 / 9
    if pair == ('c', 'f'):
        return value * 9 / 5 + 32
    raise ValueError(f'unsupported conversion {from_unit}->{to_unit}')


def parse_date(value: str) -> datetime:
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise ValueError(f'unsupported date {value}')


def age_days(dob: str, measured_at: str) -> float:
    birth = parse_date(dob)
    measurement = parse_date(measured_at)
    return (measurement - birth).total_seconds() / 86400


def age_specific_reference(lab: str, age_in_days: float) -> tuple[float, float] | None:
    normalized = normalize_lab_name(lab)
    for low_day, high_day, low, high in NEONATAL_REFERENCE_BANDS.get(normalized, []):
        if low_day <= age_in_days <= high_day:
            return low, high
    return None


def percent_weight_change(current_kg: float, birth_kg: float) -> float:
    return round(((current_kg - birth_kg) / birth_kg) * 100, 1)


def cdc_or_who_standard(child_dob: date, as_of: date) -> str:
    age_years = (as_of - child_dob).days / 365.2425
    return 'WHO-0-24-months' if age_years < 2 else 'CDC-2-20-years'
