"""The bounded trial must prove recovery and reject vacuous success."""
import pytest
from fastapi.responses import JSONResponse
from tools import lab_stress


def test_bounded_wave_recovers_every_pair():
    result = lab_stress.run_trial(6, pairs=4)
    assert result['confirmed_receipts'] == result['pairs_requested'] == 4
    assert result['recovery_requests'] == 8
    assert result['idempotency'] == result['signatures'] == 'PASS'


def test_unavailable_service_cannot_report_pass(monkeypatch):
    factory = lab_stress.create_app

    def unavailable(**kwargs):
        app = factory(**kwargs)

        async def wrapped(scope, receive, send):
            if scope['type'] == 'http':
                return await JSONResponse({'error': {'code': 'UNAVAILABLE'}}, status_code=503)(scope, receive, send)
            return await app(scope, receive, send)
        return wrapped

    monkeypatch.setattr(lab_stress, 'create_app', unavailable)
    with pytest.raises(AssertionError, match='recovery did not complete'):
        lab_stress.run_trial(1, pairs=1)
