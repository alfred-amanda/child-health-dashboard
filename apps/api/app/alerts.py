
from __future__ import annotations

from dataclasses import dataclass

from .config import ExternalServicesConfig
from .recommendations import RecommendationPayload


@dataclass(frozen=True)
class AlertReceipt:
    tier: str
    delivered: bool
    channel: str
    external_call_attempted: bool
    message: str


def emit_alert(recommendation: RecommendationPayload, config: ExternalServicesConfig) -> AlertReceipt:
    if recommendation.source.source_id == '':
        raise ValueError('no alert may fire without source')
    tier = 'urgent' if recommendation.urgency in {'urgent', '911'} else 'active' if recommendation.urgency in {'today', 'soon'} else 'passive'
    if not config.enabled:
        return AlertReceipt(tier=tier, delivered=True, channel='dummy-local', external_call_attempted=False, message=recommendation.display_text())
    if not config.allow_phi:
        return AlertReceipt(tier=tier, delivered=False, channel=config.alert_channel, external_call_attempted=False, message='external alerts disabled for PHI by default')
    return AlertReceipt(tier=tier, delivered=False, channel=config.alert_channel, external_call_attempted=True, message='opt-in external channel would be used')
