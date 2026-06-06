from datetime import datetime
from unittest.mock import patch

import pytest

from components.triage.prewarm_cache import PrewarmCache
from components.services.runner import Phase1Result
from components.models.pillar import ThreePillarSpec


def _make_result(ticket_id=7001) -> Phase1Result:
    spec = ThreePillarSpec(
        service_state_cmd="systemctl is-active nginx",
        functional_impact_cmd="curl -sf http://localhost",
        durability_cmd="systemctl is-enabled nginx",
        definition_of_done="nginx running",
    )
    return Phase1Result(
        ticket_id=ticket_id,
        cache_hit=False,
        pillar_spec=spec,
        kb_matches_initial=[],
        memory_context="",
        full_result=None,
    )


def test_set_and_get():
    cache = PrewarmCache()
    result = _make_result(7001)
    cache.set(7001, result)
    assert cache.get(7001) is result


def test_is_warm_true():
    cache = PrewarmCache()
    cache.set(7001, _make_result())
    assert cache.is_warm(7001) is True


def test_is_warm_false_not_set():
    cache = PrewarmCache()
    assert cache.is_warm(9999) is False


def test_invalidate():
    cache = PrewarmCache()
    cache.set(7001, _make_result())
    cache.invalidate(7001)
    assert cache.is_warm(7001) is False
    assert cache.get(7001) is None


def test_ttl_expiry():
    cache = PrewarmCache()
    result = _make_result()

    with patch("hermits.triage.prewarm_cache.time.monotonic") as mock_mono:
        mock_mono.return_value = 1000.0
        cache.set(7001, result)

        # Before expiry
        mock_mono.return_value = 1000.0 + cache.TTL_SECONDS - 1
        assert cache.is_warm(7001) is True
        assert cache.get(7001) is result

        # After expiry
        mock_mono.return_value = 1000.0 + cache.TTL_SECONDS + 1
        assert cache.is_warm(7001) is False
        assert cache.get(7001) is None


def test_cache_hit_returns_immediately():
    cache = PrewarmCache()
    result = _make_result(7001)
    cache.set(7001, result)

    retrieved = cache.get(7001)
    assert retrieved.ticket_id == 7001
    assert retrieved.cache_hit is False  # original value preserved
