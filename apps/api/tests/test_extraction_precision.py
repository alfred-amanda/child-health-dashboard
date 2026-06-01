
from __future__ import annotations

from pathlib import Path
from typing import cast

from app.config import SEED_ROOT
from app.extraction import evaluate_precision, extract_against_golden


def test_extraction_never_invents_and_reports_precision(tmp_path: Path) -> None:
    golden = Path(__file__).resolve().parents[3] / 'tests' / 'fixtures' / 'golden' / 'thomas_extraction_golden.json'
    candidates = extract_against_golden(golden, SEED_ROOT)
    assert candidates
    assert all(candidate.source_id and candidate.snippet and candidate.page is not None for candidate in candidates)
    assert all(candidate.confidence > 0 for candidate in candidates)
    report = evaluate_precision(candidates, golden, tmp_path)
    assert cast(float, report['precision']) >= 0.95
    assert report['false_positive'] == 0
    assert report['invented_fact_failures'] == []
    assert (tmp_path / 'extraction_precision.md').exists()
    assert (tmp_path / 'extraction_precision.json').exists()
    low_confidence = report['low_confidence_to_review']
    assert isinstance(low_confidence, list)
    assert any(item['status'] == 'needs_confirmation' for item in low_confidence)
