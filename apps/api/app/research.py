from __future__ import annotations

import json
from pathlib import Path
from typing import Any

NON_PHI_QUERY_TERMS = ('newborn infant', '0-2 months', 'seasonal pediatric advisory', 'Bay Area', 'summer')

DEFAULT_DIGEST: dict[str, Any] = {
    'mode': 'offline-cache',
    'query': 'newborn infant 0-2 months seasonal pediatric advisory Bay Area summer',
    'updates': [
        {
            'title': 'Respiratory virus activity for young infants',
            'summary': 'Watch breathing effort, feeding stamina, wet diapers, and fever patterns during respiratory virus season.',
            'confidence': 'high',
            'sources': [
                {'title': 'CDC RSV in infants and young children', 'url': 'https://www.cdc.gov/rsv/infants-young-children/index.html', 'date': '2026-06-01'},
                {'title': 'California respiratory virus surveillance', 'url': 'https://www.cdph.ca.gov/Programs/CID/DCDC/Pages/Respiratory-Viruses.aspx', 'date': '2026-06-01'},
            ],
        },
        {
            'title': 'Air quality and heat awareness',
            'summary': 'Track local AQI and indoor cooling during heat or smoke events; infants can dehydrate quickly.',
            'confidence': 'moderate',
            'sources': [
                {'title': 'AirNow AQI basics', 'url': 'https://www.airnow.gov/aqi/aqi-basics/', 'date': '2026-06-01'},
                {'title': 'CDC heat and infants', 'url': 'https://www.cdc.gov/heat-health/risk-factors/index.html', 'date': '2026-06-01'},
            ],
        },
        {
            'title': 'Measles vaccination context',
            'summary': 'Shown for awareness only before vaccine eligibility; no child-specific inference is made.',
            'confidence': 'low',
            'sources': [
                {'title': 'CDC measles cases and outbreaks', 'url': 'https://www.cdc.gov/measles/data-research/index.html', 'date': '2026-06-01'},
            ],
        },
    ],
}


def build_research_query(*, age_band: str, season: str, region: str) -> str:
    safe_age = age_band.replace('_', ' ').replace('newborn 0 2 months', 'newborn infant 0-2 months')
    return f'{safe_age} {season} pediatric advisories {region} respiratory virus heat air quality measles'


def _cache_path(root: Path) -> Path:
    return root / 'research' / 'weekly_digest.json'


def refresh_weekly_digest(root: Path, *, allow_network: bool = False) -> dict[str, Any]:
    # Network execution intentionally remains behind an explicit flag; this build path
    # writes/reads the committed offline cache and keeps all query terms non-PHI.
    digest = dict(DEFAULT_DIGEST)
    digest['mode'] = 'network-refresh-disabled' if allow_network else 'offline-cache'
    path = _cache_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(digest, indent=2))
    return digest


def load_weekly_digest(root: Path) -> dict[str, Any]:
    path = _cache_path(root)
    if not path.exists():
        return refresh_weekly_digest(root, allow_network=False)
    return json.loads(path.read_text())
