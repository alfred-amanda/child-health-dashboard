from __future__ import annotations

from typing import Any

RED_FLAG_ITEMS = [
    {
        'title': 'Unsuppressible shaking or seizure-like activity',
        'action': 'Call 911 now per discharge instructions.',
        'urgency': '911',
        'confidence': 'high',
        'source_type': 'discharge_red_flag',
        'sources': [{'title': 'ER AVS May 31 2026', 'url': 'local:SRC-003-p2', 'date': '2026-05-31'}],
    },
    {
        'title': 'Less than 4 wet diapers in 24 hours',
        'action': 'Seek medical attention now per discharge instructions.',
        'urgency': 'urgent',
        'confidence': 'high',
        'source_type': 'discharge_red_flag',
        'sources': [{'title': 'ER AVS May 31 2026', 'url': 'local:SRC-003-p2', 'date': '2026-05-31'}],
    },
]

FORBIDDEN_REASSURANCE = ('safe to wait', 'safe to defer', 'safe to skip', 'safe to delay')
ROUTINE_DOCTOR_REFRAINS = ('ask your pediatrician', 'ask your doctor', 'consult your doctor', 'consult a physician')


def _assert_voice_guardrails(text: str) -> None:
    lowered = text.lower()
    for phrase in (*FORBIDDEN_REASSURANCE, *ROUTINE_DOCTOR_REFRAINS):
        if phrase in lowered:
            raise ValueError(f'forbidden guidance phrase: {phrase}')


def _normalize_research_signal(signal: dict[str, Any]) -> dict[str, Any]:
    item = {
        'title': signal['title'],
        'action': signal['action'],
        'urgency': signal.get('urgency', 'watch' if signal.get('confidence') == 'high' else 'routine'),
        'confidence': signal['confidence'],
        'source_type': 'research',
        'sources': signal.get('sources', []),
    }
    _assert_voice_guardrails(f"{item['title']} {item['action']}")
    return item


def build_what_to_watch(*, research_signals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    actionable = [dict(item) for item in RED_FLAG_ITEMS]
    lower_confidence: list[dict[str, Any]] = []
    for signal in research_signals or []:
        item = _normalize_research_signal(signal)
        if item['confidence'] == 'high':
            actionable.append(item)
        else:
            item['action'] = item['action'].replace('Ask your pediatrician', 'Shown for awareness only')
            _assert_voice_guardrails(f"{item['title']} {item['action']}")
            lower_confidence.append(item)
    joined = ' '.join(item['action'] for item in actionable + lower_confidence)
    if any(phrase in joined.lower() for phrase in FORBIDDEN_REASSURANCE):
        raise ValueError('unsafe defer reassurance in what-to-watch output')
    return {
        'global_boundary_note': 'This local dashboard supports the care plan and keeps physician questions in Doctor Prep.',
        'actionable': actionable,
        'lower_confidence': lower_confidence,
    }
