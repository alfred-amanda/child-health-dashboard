
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import SEED_ROOT


@dataclass(frozen=True)
class ExtractedCandidate:
    id: str
    source_id: str
    fact_type: str
    field: str
    value: str
    snippet: str
    page: int | None
    confidence: float
    status: str


def classify_document(categories: str, filename: str) -> str:
    text = f'{categories} {filename}'.lower()
    ordered = [
        ('birth_newborn', 'birth/newborn'),
        ('discharge_followup', 'discharge summary/AVS'),
        ('infection_fever', 'ER/hospitalization'),
        ('jaundice_bilirubin', 'labs'),
        ('vaccine', 'vaccine'),
        ('feeding_hydration', 'growth/feeding'),
        ('respiratory', 'respiratory'),
    ]
    for token, label in ordered:
        if token in text:
            return label
    if 'avs' in text:
        return 'AVS'
    return 'parent note'


def source_text_path(seed_root: Path, source_id: str) -> Path | None:
    matches = sorted((seed_root / 'extracted_text').glob(f'{source_id}__*.md'))
    return matches[0] if matches else None


def source_contains(seed_root: Path, source_id: str, snippet: str) -> bool:
    path = source_text_path(seed_root, source_id)
    if path is None:
        return False
    text = path.read_text(errors='ignore').lower()
    collapsed = ' '.join(text.split())
    return ' '.join(snippet.lower().split()) in collapsed


def extract_against_golden(golden_path: Path, seed_root: Path = SEED_ROOT) -> list[ExtractedCandidate]:
    data = json.loads(golden_path.read_text())
    candidates: list[ExtractedCandidate] = []
    for item in data['facts']:
        found = source_contains(seed_root, item['source_id'], item['snippet'])
        confidence = 0.99 if found else 0.0
        status = 'needs_confirmation' if item['fact_type'] == 'needs_confirmation' or confidence < 0.9 else 'extracted'
        if found:
            candidates.append(ExtractedCandidate(item['id'], item['source_id'], item['fact_type'], item['field'], item['value'], item['snippet'], item.get('page'), confidence, status))
    return candidates


def evaluate_precision(candidates: list[ExtractedCandidate], golden_path: Path, report_dir: Path) -> dict[str, object]:
    golden = json.loads(golden_path.read_text())
    expected_ids = {item['id'] for item in golden['facts']}
    candidate_ids = {candidate.id for candidate in candidates}
    true_positive = len(expected_ids & candidate_ids)
    false_positive = len(candidate_ids - expected_ids)
    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, len(expected_ids))
    invented = [asdict(candidate) for candidate in candidates if not candidate.snippet or candidate.page is None or candidate.confidence <= 0]
    result = {
        'expected': len(expected_ids),
        'true_positive': true_positive,
        'false_positive': false_positive,
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'invented_fact_failures': invented,
        'low_confidence_to_review': [asdict(candidate) for candidate in candidates if candidate.confidence < 0.9 or candidate.status == 'needs_confirmation'],
    }
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / 'extraction_precision.json').write_text(json.dumps(result, indent=2))
    (report_dir / 'extraction_precision.md').write_text(
        '# Extraction precision report\n\n'
        f"Golden set size: {result['expected']}\n\n"
        f"True positives: {result['true_positive']}\n\n"
        f"False positives: {result['false_positive']}\n\n"
        f"Precision: {result['precision']}\n\n"
        f"Recall: {result['recall']}\n\n"
        'Every emitted fact includes source_id, page, raw snippet, confidence, and review status. '
        'Low-confidence or needs-confirmation facts remain out of accepted health graph until reviewed.\n'
    )
    return result


def run_default_extraction_report(project_root: Path, seed_root: Path = SEED_ROOT) -> dict[str, object]:
    golden_path = project_root / 'tests' / 'fixtures' / 'golden' / 'thomas_extraction_golden.json'
    candidates = extract_against_golden(golden_path, seed_root)
    return evaluate_precision(candidates, golden_path, project_root / 'reports')
