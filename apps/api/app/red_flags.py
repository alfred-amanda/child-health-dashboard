
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .recommendations import RecommendationPayload, SourceRef


@dataclass(frozen=True)
class RedFlagRule:
    key: str
    label: str
    operator: str
    threshold: float | None
    unit: str | None
    urgency: str
    action: str
    source_id: str
    source_title: str
    page: int | None
    snippet: str
    confidence: float


@dataclass(frozen=True)
class Observation:
    kind: str
    value: float | bool | str
    window_hours: int | None = None


def _line_page_map(text: str) -> list[tuple[int | None, int, str]]:
    page: int | None = None
    rows: list[tuple[int | None, int, str]] = []
    for index, line in enumerate(text.splitlines(), start=1):
        match = re.match(r'--- PAGE (\d+) ---', line.strip())
        if match:
            page = int(match.group(1))
        rows.append((page, index, line))
    return rows


def _source_for_pattern(text: str, pattern: str) -> tuple[int | None, str]:
    regex = re.compile(pattern, re.IGNORECASE)
    rows = _line_page_map(text)
    for idx, (page, _line_no, line) in enumerate(rows):
        if regex.search(line):
            snippet_lines = [rows[j][2].strip() for j in range(max(0, idx - 1), min(len(rows), idx + 2))]
            return page, ' '.join(part for part in snippet_lines if part)
    return None, ''


def parse_discharge_rules(text: str, source_id: str = 'SRC-003', source_title: str = 'ER AVS May 31 2026') -> list[RedFlagRule]:
    rules: list[RedFlagRule] = []
    wet = re.search(r'Less than\s+(\d+)\s+wet diapers in\s+(\d+)\s+hours', text, re.IGNORECASE)
    if wet:
        page, snippet = _source_for_pattern(text, r'Less than\s+\d+\s+wet diapers')
        rules.append(RedFlagRule('wet_diapers_24h', 'Less than source threshold wet diapers / 24h', '<', float(wet.group(1)), 'wet diapers/24h', 'urgent', 'seek medical attention from the pediatrician, urgent care, or emergency department now', source_id, source_title, page, snippet, 0.99))
    for key, phrase in [
        ('difficulty_feeding', 'Difficulty feeding'),
        ('difficulty_breathing', 'Difficulty breathing'),
        ('increasing_jaundice', 'Increasing jaundice'),
        ('lethargy_decreased_activity', 'Lethargy/Decreased activity'),
    ]:
        page, snippet = _source_for_pattern(text, re.escape(phrase))
        if snippet:
            rules.append(RedFlagRule(key, phrase, 'present', None, None, 'urgent', 'seek medical attention from the pediatrician, urgent care, or emergency department now', source_id, source_title, page, snippet, 0.96))
    fever = re.search(r'fevers reaching\s+(\d+(?:\.\d+)?)\s*c', text, re.IGNORECASE)
    if fever:
        page, snippet = _source_for_pattern(text, r'fevers reaching')
        rules.append(RedFlagRule('fever_reaching_c', 'Fever reaching source threshold', '>=', float(fever.group(1)), 'C', 'today', 'call your pediatrician', source_id, source_title, page, snippet, 0.98))
    multiple = re.search(r'multiple fevers\s*>\s*(\d+(?:\.\d+)?)\s*c\s+in a\s+(\d+)\s+hr', text, re.IGNORECASE)
    if multiple:
        page, snippet = _source_for_pattern(text, r'multiple fevers')
        rules.append(RedFlagRule('multiple_fevers_24h_c', 'Multiple fevers above source threshold / 24h', '>', float(multiple.group(1)), 'C', 'today', 'call your pediatrician', source_id, source_title, page, snippet, 0.98))
    axillary = re.search(r'axillary temp of\s+(\d+(?:\.\d+)?)\s*c\s+or above', text, re.IGNORECASE)
    if axillary:
        page, snippet = _source_for_pattern(text, r'axillary temp')
        rules.append(RedFlagRule('axillary_temp_c', 'Axillary temp source medication threshold', '>=', float(axillary.group(1)), 'C', 'soon', 'follow discharge Tylenol instructions and confirm with pediatrician', source_id, source_title, page, snippet, 0.96))
    seizure = re.search(r'extremities shake.*?call\s+911.*?seizure', text, re.IGNORECASE | re.DOTALL)
    if seizure:
        page, snippet = _source_for_pattern(text, r'extremities shake')
        rules.append(RedFlagRule('unsuppressible_shaking', 'Unsuppressible extremity shaking', 'present', None, None, '911', 'call 911 immediately', source_id, source_title, page, snippet, 0.99))
    return rules


def load_thomas_rules(seed_root: Path) -> list[RedFlagRule]:
    path = seed_root / 'extracted_text' / 'SRC-003__attachments_er_avs.PDF.md'
    if not path.exists():
        return []
    return parse_discharge_rules(path.read_text(), 'SRC-003', 'ER AVS May 31 2026')


def evaluate_observation(observation: Observation, rules: list[RedFlagRule]) -> RecommendationPayload | None:
    for rule in rules:
        if observation.kind != rule.key:
            continue
        triggered = False
        if rule.operator == '<' and isinstance(observation.value, int | float) and rule.threshold is not None:
            triggered = float(observation.value) < rule.threshold
        elif rule.operator == '>=' and isinstance(observation.value, int | float) and rule.threshold is not None:
            triggered = float(observation.value) >= rule.threshold
        elif rule.operator == '>' and isinstance(observation.value, int | float) and rule.threshold is not None:
            triggered = float(observation.value) > rule.threshold
        elif rule.operator == 'present' and bool(observation.value):
            triggered = True
        if triggered:
            return RecommendationPayload(
                evidence=f"{rule.label} was triggered by value {observation.value} {rule.unit or ''}".strip(),
                action=rule.action,
                urgency=rule.urgency,  # type: ignore[arg-type]
                confidence='high' if rule.confidence >= 0.95 else 'moderate',
                source=SourceRef(source_id=rule.source_id, title=rule.source_title, page=rule.page, snippet=rule.snippet, confidence=rule.confidence),
            )
    return None


def missing_source_recommendation(rule_key: str) -> RecommendationPayload:
    return RecommendationPayload(
        evidence=f"{rule_key} threshold is not computable from Thomas's available discharge records",
        action='ask the pediatrician to confirm the threshold before relying on this rule',
        urgency='today',
        confidence='low',
        source=SourceRef(source_id='needs-confirmation', title='No source threshold found', page=None, snippet='not computable from available records', confidence=0.1),
    )
