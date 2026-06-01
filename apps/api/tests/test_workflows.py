
from __future__ import annotations

from app.doctor_prep import THOMAS_QUESTIONS, generate_markdown, generate_minimal_pdf
from app.normalization import age_days, age_specific_reference, convert_unit, normalize_lab_name
from app.recommendations import RecommendationPayload, SourceRef


def test_normalization_units_synonyms_and_age_reference() -> None:
    assert convert_unit(1, 'kg', 'g') == 1000
    assert round(convert_unit(100.4, 'F', 'C'), 1) == 38.0
    assert normalize_lab_name('TSB') == 'bilirubin_total'
    assert age_days('2026-05-17', '2026-05-18') == 1
    newborn = age_specific_reference('hemoglobin', 3)
    later = age_specific_reference('hemoglobin', 20)
    assert newborn != later


def test_recommendation_payload_is_mechanically_enforced() -> None:
    payload = RecommendationPayload(evidence='red flag source says less than 4 wet diapers', action='seek medical attention now', urgency='urgent', confidence='high', source=SourceRef(source_id='SRC-003', title='ER AVS', page=2, snippet='Less than 4 wet diapers', confidence=0.99))
    assert 'Because ' in payload.display_text()


def test_doctor_prep_generates_ten_questions_and_pdf(tmp_path) -> None:
    assert len(THOMAS_QUESTIONS) == 10
    md = generate_markdown(tmp_path)
    pdf = generate_minimal_pdf(tmp_path)
    assert 'Confirm final blood, CSF, and urine culture status' in md.read_text()
    assert pdf.read_bytes().startswith(b'%PDF')
