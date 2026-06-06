import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from components.services.three_pillars import (
    ThreePillarGenerationError,
    ThreePillarsGenerator,
    UnsafeCommandError,
)
from components.gemini_client import GeminiParseError
from components.models.ticket import Ticket

_TICKET = Ticket(
    id=7001,
    title="nginx down",
    description="nginx not responding on port 80",
    customer_id=5001,
    customer_name="ACME Corp",
    priority="high",
    status="OPEN",
    created_at=datetime(2026, 6, 1, 10, 0, 0),
    service_hint="nginx",
)

_VALID_JSON = {
    "service_state_cmd": "systemctl is-active nginx && echo PASS",
    "functional_impact_cmd": "curl -sf http://localhost/health | grep -q ok && echo PASS",
    "durability_cmd": "systemctl is-enabled nginx && echo PASS",
    "definition_of_done": "nginx is active and enabled",
}


def _make_generator(return_value):
    mock_client = MagicMock()
    mock_client.generate_json.return_value = return_value
    return ThreePillarsGenerator(client=mock_client)


def test_valid_json_parse():
    gen = _make_generator(_VALID_JSON)
    spec = gen.generate(_TICKET)
    assert spec.service_state_cmd == _VALID_JSON["service_state_cmd"]
    assert spec.definition_of_done == _VALID_JSON["definition_of_done"]


def test_markdown_fence_stripping():
    from components.gemini_client import GeminiClient
    client = GeminiClient.__new__(GeminiClient)
    fenced = "```json\n" + json.dumps(_VALID_JSON) + "\n```"
    assert json.loads(client._strip_fences(fenced)) == _VALID_JSON

    fenced2 = "```\n" + json.dumps(_VALID_JSON) + "\n```"
    assert json.loads(client._strip_fences(fenced2)) == _VALID_JSON


def test_unsafe_command_detected():
    unsafe = {
        "service_state_cmd": "rm -rf /etc && echo PASS",
        "functional_impact_cmd": "curl -sf http://localhost/health && echo PASS",
        "durability_cmd": "systemctl is-enabled nginx && echo PASS",
        "definition_of_done": "done",
    }
    gen = _make_generator(unsafe)
    with pytest.raises(UnsafeCommandError):
        gen.generate(_TICKET)


def test_unsafe_systemctl_stop():
    unsafe = {
        "service_state_cmd": "systemctl stop nginx && echo done",
        "functional_impact_cmd": "curl -sf http://localhost && echo PASS",
        "durability_cmd": "systemctl is-enabled nginx && echo PASS",
        "definition_of_done": "done",
    }
    gen = _make_generator(unsafe)
    with pytest.raises(UnsafeCommandError):
        gen.generate(_TICKET)


def test_retry_on_parse_failure():
    mock_client = MagicMock()
    mock_client.generate_json.side_effect = [
        GeminiParseError("bad json"),
        _VALID_JSON,
    ]
    gen = ThreePillarsGenerator(client=mock_client)
    spec = gen.generate(_TICKET)
    assert spec.durability_cmd == _VALID_JSON["durability_cmd"]
    assert mock_client.generate_json.call_count == 2


def test_raises_after_two_failures():
    mock_client = MagicMock()
    mock_client.generate_json.side_effect = GeminiParseError("bad json")
    gen = ThreePillarsGenerator(client=mock_client)
    with pytest.raises(ThreePillarGenerationError):
        gen.generate(_TICKET)
