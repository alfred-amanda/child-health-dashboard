from __future__ import annotations

from typing import Any

from .red_flags import RedFlagRule


def _rule_to_watch_item(rule: RedFlagRule) -> dict[str, Any]:
    title = rule.label
    if rule.threshold is not None and rule.unit:
        threshold = f'{rule.threshold:g} {rule.unit}'
        title = title.replace('source threshold', threshold)
    return {
        'title': title,
        'action': rule.action,
        'urgency': rule.urgency,
        'confidence': 'high' if rule.confidence >= 0.95 else 'moderate',
        'source_type': 'discharge_parser_rule',
        'rule_key': rule.key,
        'sources': [{'title': rule.source_title, 'url': f'local:{rule.source_id}-p{rule.page or "unknown"}', 'date': '2026-05-31', 'snippet': rule.snippet}],
    }

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


def build_what_to_watch(*, red_flag_rules: list[RedFlagRule] | None = None, research_signals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    discharge_items = sorted([_rule_to_watch_item(rule) for rule in red_flag_rules or []], key=lambda item: 0 if item['urgency'] == '911' else 1)
    actionable = discharge_items
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
