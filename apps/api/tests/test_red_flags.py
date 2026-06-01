
from __future__ import annotations

from pathlib import Path

from app.config import SEED_ROOT
from app.red_flags import (
    Observation,
    evaluate_observation,
    load_thomas_rules,
    parse_discharge_rules,
)


def test_red_flag_rules_are_source_driven_and_cited() -> None:
    rules = load_thomas_rules(SEED_ROOT)
    by_key = {rule.key: rule for rule in rules}
    assert by_key['wet_diapers_24h'].threshold == 4
    assert by_key['wet_diapers_24h'].page == 2
    assert 'Less than 4 wet diapers' in by_key['wet_diapers_24h'].snippet
    assert by_key['fever_reaching_c'].threshold == 39
    assert by_key['unsuppressible_shaking'].urgency == '911'
    assert by_key['unsuppressible_shaking'].source_id == 'SRC-003'


def test_thresholds_change_when_source_text_changes() -> None:
    text = (Path(SEED_ROOT) / 'extracted_text' / 'SRC-003__attachments_er_avs.PDF.md').read_text()
    changed = text.replace('Less than 4 wet diapers in 24 hours', 'Less than 5 wet diapers in 24 hours').replace('fevers reaching 39c again', 'fevers reaching 40c again')
    rules = {rule.key: rule for rule in parse_discharge_rules(changed)}
    assert rules['wet_diapers_24h'].threshold == 5
    assert rules['fever_reaching_c'].threshold == 40


def test_urgent_outputs_use_recommendation_shape_with_source() -> None:
    rules = load_thomas_rules(SEED_ROOT)
    payload = evaluate_observation(Observation('wet_diapers_24h', 3, window_hours=24), rules)
    assert payload is not None
    rendered = payload.display_text()
    assert rendered.startswith('Because ')
    assert 'Urgency: urgent' in rendered
    assert 'Source: SRC-003 p.2' in rendered
