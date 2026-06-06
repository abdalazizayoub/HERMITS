from datetime import datetime
from unittest.mock import MagicMock

from components.services.pillar_validator import PillarValidator
from components.models.pillar import PillarResult, ThreePillarSpec
from components.models.ticket import Ticket

_TICKET = Ticket(
    id=7003,
    title="nginx down",
    description="nginx not responding",
    customer_id=5003,
    customer_name="GammaCo",
    priority="high",
    status="in_progress",
    created_at=datetime(2026, 6, 1),
)

_SPEC = ThreePillarSpec(
    service_state_cmd="systemctl is-active nginx && echo PASS",
    functional_impact_cmd="curl -sf http://localhost/health | grep -q ok && echo PASS",
    durability_cmd="systemctl is-enabled nginx && echo PASS",
    definition_of_done="nginx running and enabled",
)

_BASELINE = PillarResult(
    service_state_output="inactive",
    functional_impact_output="connection refused",
    durability_output="disabled",
)


def _make_validator(response: dict) -> PillarValidator:
    mock_client = MagicMock()
    mock_client.generate_json.return_value = response
    return PillarValidator(client=mock_client)


def test_all_pass():
    validator = _make_validator({
        "service_state_passed": True,
        "functional_impact_passed": True,
        "durability_passed": True,
        "overall_passed": True,
        "notes": "All pillars green",
    })
    after = PillarResult(
        service_state_output="active PASS",
        functional_impact_output="ok PASS",
        durability_output="enabled PASS",
    )
    result = validator.validate(_SPEC, _BASELINE, after, _TICKET)
    assert result.overall_passed is True
    assert result.service_state_passed is True


def test_all_fail():
    validator = _make_validator({
        "service_state_passed": False,
        "functional_impact_passed": False,
        "durability_passed": False,
        "overall_passed": False,
        "notes": "Still broken",
    })
    after = PillarResult(
        service_state_output="inactive",
        functional_impact_output="refused",
        durability_output="disabled",
    )
    result = validator.validate(_SPEC, _BASELINE, after, _TICKET)
    assert result.overall_passed is False


def test_partial_pass_two_of_three():
    validator = _make_validator({
        "service_state_passed": True,
        "functional_impact_passed": True,
        "durability_passed": False,
        "overall_passed": False,
        "notes": "Service is running but not enabled for auto-start.",
    })
    after = PillarResult(
        service_state_output="active PASS",
        functional_impact_output="ok PASS",
        durability_output="disabled",
    )
    result = validator.validate(_SPEC, _BASELINE, after, _TICKET)
    assert result.service_state_passed is True
    assert result.functional_impact_passed is True
    assert result.durability_passed is False
    assert result.overall_passed is False
    assert "not enabled" in result.notes
