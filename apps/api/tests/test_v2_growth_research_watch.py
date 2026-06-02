from __future__ import annotations

from pathlib import Path

import pytest

from app.config import SEED_ROOT
from app.growth import (
    MeasurementInput,
    compute_growth_snapshot,
    lms_percentile,
    load_independent_fixture,
)
from app.red_flags import load_thomas_rules
from app.research import build_research_query, load_weekly_digest, refresh_weekly_digest
from app.watch import build_what_to_watch


@pytest.mark.parametrize(
    ('kind', 'age_days', 'value', 'expected_percentile'),
    [
        ('weight_kg', 14.0, 4.05, 58.9),
        ('length_cm', 14.0, 54.2, 72.4),
        ('head_cm', 14.0, 37.3, 82.1),
    ],
)
def test_male_who_percentiles_match_independent_committed_fixture(kind: str, age_days: float, value: float, expected_percentile: float) -> None:
    fixture = load_independent_fixture(Path(__file__).resolve().parents[3] / 'tests' / 'fixtures' / 'who_male_independent_fixture.json')
    assert fixture[(kind, age_days, value)] == expected_percentile
    assert lms_percentile(kind=kind, sex='male', age_days=age_days, value=value) == pytest.approx(expected_percentile, abs=0.15)


def test_growth_snapshot_converts_units_attributes_entries_and_suppresses_sparse_projection() -> None:
    snapshot = compute_growth_snapshot([
        MeasurementInput(kind='weight', value=8, unit='lb', measured_at='2026-06-01', actor='John'),
        MeasurementInput(kind='length', value=21.25, unit='in', measured_at='2026-06-01', actor='Patricia'),
        MeasurementInput(kind='head', value=14.7, unit='in', measured_at='2026-06-01', actor='John'),
    ], sex='male', dob='2026-05-17')
    assert snapshot['projection'] == 'points_only_no_projection'
    assert snapshot['measurements'][0]['value_kg'] == pytest.approx(3.629, abs=0.001)
    assert snapshot['measurements'][1]['value_cm'] == pytest.approx(53.975, abs=0.001)
    assert all(item['actor'] for item in snapshot['measurements'])
    assert all(item['source'] == 'parent-entered measurement' for item in snapshot['measurements'])
    assert snapshot['percentiles']['weight']['label'].startswith('tracking along the ~')


def test_research_queries_are_non_phi_cited_and_work_from_offline_cache(tmp_path: Path) -> None:
    query = build_research_query(age_band='newborn_0_2_months', season='summer', region='Bay Area')
    forbidden = ['Thomas', 'Chen', '2026-05-17', 'parechovirus', 'DAT', 'jaundice']
    assert not any(term.lower() in query.lower() for term in forbidden)
    observed_urls: list[str] = []
    def fake_fetch(url: str, timeout_seconds: float) -> str:
        observed_urls.append(url)
        return '<html><title>safe generic public-health update</title><p>respiratory virus and heat guidance for infants</p></html>'
    digest = refresh_weekly_digest(tmp_path, allow_network=True, fetcher=fake_fetch)
    assert digest['mode'] == 'network-refresh'
    assert len(observed_urls) >= 3
    assert not any(term.lower() in ' '.join(observed_urls).lower() for term in forbidden)
    assert digest['updates']
    assert all(update['sources'] for update in digest['updates'])
    assert all(source['url'].startswith('https://') and source['date'] for update in digest['updates'] for source in update['sources'])
    assert load_weekly_digest(tmp_path) == digest
    def broken_fetch(url: str, timeout_seconds: float) -> str:
        raise TimeoutError(url)
    offline = refresh_weekly_digest(tmp_path, allow_network=True, fetcher=broken_fetch)
    assert offline['mode'] == 'offline-cache'
    assert offline['updates'] == digest['updates']


def test_who_male_lms_extends_to_24_months_without_flat_clamping() -> None:
    newborn = lms_percentile(kind='weight_kg', sex='male', age_days=14, value=4.05)
    toddler = lms_percentile(kind='weight_kg', sex='male', age_days=730, value=12.2)
    assert newborn == pytest.approx(58.9, abs=0.15)
    assert 45 <= toddler <= 75
    assert toddler != newborn


def test_what_to_watch_partial_merge_voice_and_red_flag_precedence() -> None:
    source_rules = load_thomas_rules(Path(SEED_ROOT))
    result = build_what_to_watch(red_flag_rules=source_rules, research_signals=[
        {'title': 'Bay Area respiratory virus activity', 'confidence': 'high', 'action': 'watch breathing, feeding, wet diapers, and fever patterns', 'sources': [{'title': 'CDC RSV', 'url': 'https://cdc.gov/rsv', 'date': '2026-06-01'}]},
        {'title': 'Unconfirmed daycare stomach bug rumor', 'confidence': 'low', 'action': 'being monitored only', 'sources': [{'title': 'County digest', 'url': 'https://example.org', 'date': '2026-06-01'}]},
    ])
    actionable = result['actionable']
    lower = result['lower_confidence']
    assert actionable[0]['urgency'] == '911'
    assert 'call 911' in actionable[0]['action'].lower()
    assert actionable[0]['source_type'] == 'discharge_parser_rule'
    assert any(item['title'] == 'Bay Area respiratory virus activity' for item in actionable)
    assert all(item['confidence'] == 'high' for item in actionable if item['source_type'] == 'research')
    assert any(item['title'] == 'Unconfirmed daycare stomach bug rumor' for item in lower)
    combined = ' '.join(item['action'] for item in actionable + lower).lower()
    assert 'ask your pediatrician' not in combined
    assert 'ask your doctor' not in combined
    assert 'safe to wait' not in combined
    assert 'safe to defer' not in combined
    assert 'safe to skip' not in combined
