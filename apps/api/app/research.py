from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

NON_PHI_QUERY_TERMS = ('newborn infant', '0-2 months', 'seasonal pediatric advisory', 'Bay Area', 'summer')
PUBLIC_SOURCES = [
    ('CDC RSV in infants and young children', 'https://www.cdc.gov/rsv/infants-young-children/index.html'),
    ('California respiratory virus surveillance', 'https://www.cdph.ca.gov/Programs/CID/DCDC/Pages/Respiratory-Viruses.aspx'),
    ('AirNow AQI basics', 'https://www.airnow.gov/aqi/aqi-basics/'),
    ('CDC heat and infants', 'https://www.cdc.gov/heat-health/risk-factors/index.html'),
]
Fetcher = Callable[[str, float], str]

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


def _default_fetcher(url: str, timeout_seconds: float) -> str:
    with urllib.request.urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310 - allowlisted public non-PHI URLs only
        return response.read(80_000).decode('utf-8', errors='ignore')


def _source_query_url(url: str, query: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https':
        raise ValueError(f'only https public sources allowed: {url}')
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode({'q': query})))


def _network_digest(query: str, *, fetcher: Fetcher, timeout_seconds: float) -> dict[str, Any]:
    today = date.today().isoformat()
    fetched_sources: list[dict[str, str]] = []
    for title, url in PUBLIC_SOURCES:
        fetched_url = _source_query_url(url, query)
        text = fetcher(fetched_url, timeout_seconds)
        if text:
            fetched_sources.append({'title': title, 'url': url, 'date': today})
    if len(fetched_sources) < 3:
        raise RuntimeError('fewer than 3 public sources fetched')
    return {
        'mode': 'network-refresh',
        'query': query,
        'updates': [
            {
                'title': 'Multi-source public health scan for young infants',
                'summary': 'Generic public sources were refreshed for respiratory virus, heat, air quality, and measles awareness. This uses no child-specific terms and stores citations locally.',
                'confidence': 'high',
                'sources': fetched_sources[:3],
            },
            DEFAULT_DIGEST['updates'][1],
            DEFAULT_DIGEST['updates'][2],
        ],
    }


def refresh_weekly_digest(root: Path, *, allow_network: bool = False, fetcher: Fetcher | None = None, timeout_seconds: float = 4.0) -> dict[str, Any]:
    query = build_research_query(age_band='newborn_0_2_months', season='summer', region='Bay Area')
    path = _cache_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if allow_network:
        try:
            digest = _network_digest(query, fetcher=fetcher or _default_fetcher, timeout_seconds=timeout_seconds)
            path.write_text(json.dumps(digest, indent=2))
            return digest
        except Exception:
            if path.exists():
                cached = json.loads(path.read_text())
                cached['mode'] = 'offline-cache'
                return cached
    digest = dict(DEFAULT_DIGEST)
    digest['mode'] = 'offline-cache'
    digest['query'] = query
    path.write_text(json.dumps(digest, indent=2))
    return digest


def load_weekly_digest(root: Path) -> dict[str, Any]:
    path = _cache_path(root)
    if not path.exists():
        return refresh_weekly_digest(root, allow_network=False)
    return json.loads(path.read_text())
