
from __future__ import annotations

from dataclasses import dataclass

BANNED_REASSURANCE_PHRASES = [
    'safe to wait',
    'no need to call',
    'do not call',
    'you can defer care',
    'reassuring enough to skip',
]


@dataclass(frozen=True)
class Prediction:
    kind: str
    status: str
    confidence: str
    message: str
    source: str
    action: str


def safe_copy(text: str) -> bool:
    lowered = text.lower()
    return not any(phrase in lowered for phrase in BANNED_REASSURANCE_PHRASES)


def sparse_series_policy(points: list[object], minimum: int = 4) -> str:
    return 'points_only_no_projection' if len(points) < minimum else 'projection_allowed_with_caveat'


def forecast_gaps(seed_profile: dict) -> list[Prediction]:
    predictions = [
        Prediction('vaccine_gap', 'action_needed', 'high', 'Hep B was deferred in the records; discuss catch-up timing with the pediatrician.', 'structured_profile.screenings_immunizations.hepatitis_b', 'Add Hep B catch-up question/task.'),
        Prediction('culture_final_confirmation', 'action_needed', 'moderate', 'Cultures were reassuring in notes but final status should be confirmed at the next visit.', 'SRC-008/SRC-035 culture notes', 'Ask pediatrician to confirm final blood/CSF/urine culture status.'),
    ]
    if len(seed_profile.get('blood_type_jaundice', {}).get('bilirubin_values', [])) < 4:
        predictions.append(Prediction('bilirubin_projection', 'not_computable_from_available_records', 'low', 'Not computable from available records; use pediatrician-directed bilirubin follow-up rather than projection.', 'bilirubin values', 'Ask pediatrician if repeat bilirubin is needed.'))
    return predictions
