
from __future__ import annotations

import socket
from pathlib import Path

import pytest

from app.alerts import emit_alert
from app.config import SEED_ROOT, ExternalServicesConfig
from app.extraction import extract_against_golden
from app.predictions import forecast_gaps, safe_copy, sparse_series_policy
from app.recommendations import RecommendationPayload, SourceRef
from app.seed import load_profile


def test_default_extraction_prediction_alerts_make_no_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def forbidden(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))
        raise AssertionError('network egress attempted')

    monkeypatch.setattr(socket.socket, 'connect', forbidden, raising=True)
    golden = Path(__file__).resolve().parents[3] / 'tests' / 'fixtures' / 'golden' / 'thomas_extraction_golden.json'
    assert extract_against_golden(golden, SEED_ROOT)
    assert forecast_gaps(load_profile())
    rec = RecommendationPayload(evidence='dummy sourced alert', action='record local dummy receipt', urgency='urgent', confidence='high', source=SourceRef(source_id='TEST', title='test', page=1, snippet='dummy', confidence=1))
    receipt = emit_alert(rec, ExternalServicesConfig())
    assert receipt.external_call_attempted is False
    assert calls == []


def test_predictions_are_bounded_and_never_reassurance_to_defer() -> None:
    predictions = forecast_gaps(load_profile())
    assert any(prediction.kind == 'vaccine_gap' for prediction in predictions)
    assert any(prediction.kind == 'culture_final_confirmation' for prediction in predictions)
    assert all(prediction.confidence in {'low', 'moderate', 'high'} for prediction in predictions)
    assert all(safe_copy(prediction.message) for prediction in predictions)
    assert sparse_series_policy([1, 2, 3]) == 'points_only_no_projection'
