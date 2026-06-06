from datetime import datetime
from unittest.mock import MagicMock

import pytest

from components.services.hypothesis_generator import HypothesisGenerationError, HypothesisGenerator
from components.gemini_client import GeminiParseError
from components.models.hypothesis import BestHypothesisResult
from components.models.pillar import PillarResult
from components.models.ticket import Ticket

_TICKET = Ticket(
    id=7002,
    title="database connection refused",
    description="postgresql not accepting connections on port 5432",
    customer_id=5002,
    customer_name="BetaCo",
    priority="critical",
    status="OPEN",
    created_at=datetime(2026, 6, 1),
    service_hint="postgresql",
)

_EMPTY_BASELINE = PillarResult(
    service_state_output="inactive",
    functional_impact_output="connection refused",
    durability_output="disabled",
)

_HYPOTHESIS_A = {
    "hypothesis_title": "PostgreSQL stopped due to disk full",
    "root_cause_explanation": "The data directory disk is at 100%",
    "evidence": ["disk usage shows /var/lib/postgresql at 100%"],
    "fix_steps": [
        {"command": "df -h /var/lib/postgresql", "rationale": "check disk", "risk_level": "low"}
    ],
    "expected_pillar_outcomes": {
        "service_state": "active",
        "functional_impact": "connections accepted",
        "durability": "enabled",
    },
    "confidence_rationale": "Disk full is the most common cause",
}

_HYPOTHESIS_B = {
    "hypothesis_title": "PostgreSQL config file corrupted",
    "root_cause_explanation": "Config syntax error prevents startup",
    "evidence": ["journalctl shows config parse error"],
    "fix_steps": [
        {"command": "pg_lsclusters", "rationale": "list clusters", "risk_level": "low"}
    ],
    "expected_pillar_outcomes": {
        "service_state": "active",
        "functional_impact": "connections accepted",
        "durability": "enabled",
    },
    "confidence_rationale": "Config errors are common after updates",
}

_HYPOTHESIS_C = {
    "hypothesis_title": "PostgreSQL port conflict",
    "root_cause_explanation": "Another process is using port 5432",
    "evidence": ["ss -tlnp shows another process on 5432"],
    "fix_steps": [
        {"command": "ss -tlnp | grep 5432", "rationale": "check port", "risk_level": "low"}
    ],
    "expected_pillar_outcomes": {
        "service_state": "active",
        "functional_impact": "connections accepted",
        "durability": "enabled",
    },
    "confidence_rationale": "Port conflict is less likely but possible",
}

_VALID_RESPONSE = {
    "hypotheses": [_HYPOTHESIS_A, _HYPOTHESIS_B, _HYPOTHESIS_C],
    "best_hypothesis_index": 0,
    "selection_rationale": "Disk full is most supported by the recon evidence",
}


def test_returns_best_hypothesis_result():
    mock_client = MagicMock()
    mock_client.generate_json.return_value = _VALID_RESPONSE
    gen = HypothesisGenerator(client=mock_client)
    result = gen.generate(_TICKET, {}, _EMPTY_BASELINE, [], "")
    assert isinstance(result, BestHypothesisResult)
    assert result.ticket_id == _TICKET.id
    assert result.hypothesis.hypothesis_title == _HYPOTHESIS_A["hypothesis_title"]
    assert result.selection_rationale == _VALID_RESPONSE["selection_rationale"]


def test_best_hypothesis_index_1_returns_second():
    response = {
        "hypotheses": [_HYPOTHESIS_A, _HYPOTHESIS_B, _HYPOTHESIS_C],
        "best_hypothesis_index": 1,
        "selection_rationale": "Config corruption is actually most likely",
    }
    mock_client = MagicMock()
    mock_client.generate_json.return_value = response
    gen = HypothesisGenerator(client=mock_client)
    result = gen.generate(_TICKET, {}, _EMPTY_BASELINE, [], "")
    assert result.hypothesis.hypothesis_title == _HYPOTHESIS_B["hypothesis_title"]


def test_best_hypothesis_index_out_of_range_raises():
    response = {
        "hypotheses": [_HYPOTHESIS_A, _HYPOTHESIS_B, _HYPOTHESIS_C],
        "best_hypothesis_index": 3,
        "selection_rationale": "Out of range",
    }
    mock_client = MagicMock()
    mock_client.generate_json.side_effect = [response, GeminiParseError("fail")]
    gen = HypothesisGenerator(client=mock_client)
    with pytest.raises(HypothesisGenerationError):
        gen.generate(_TICKET, {}, _EMPTY_BASELINE, [], "")


def test_wrong_count_raises():
    mock_client = MagicMock()
    mock_client.generate_json.side_effect = [
        {"hypotheses": [_HYPOTHESIS_A, _HYPOTHESIS_B], "best_hypothesis_index": 0, "selection_rationale": "..."},
        GeminiParseError("fail"),
    ]
    gen = HypothesisGenerator(client=mock_client)
    with pytest.raises(HypothesisGenerationError):
        gen.generate(_TICKET, {}, _EMPTY_BASELINE, [], "")


def test_missing_field_raises():
    bad = {k: v for k, v in _HYPOTHESIS_A.items() if k != "root_cause_explanation"}
    mock_client = MagicMock()
    mock_client.generate_json.side_effect = [
        {"hypotheses": [bad, bad, bad], "best_hypothesis_index": 0, "selection_rationale": "..."},
        GeminiParseError("fail"),
    ]
    gen = HypothesisGenerator(client=mock_client)
    with pytest.raises(HypothesisGenerationError):
        gen.generate(_TICKET, {}, _EMPTY_BASELINE, [], "")


def test_retry_succeeds_on_second_attempt():
    mock_client = MagicMock()
    mock_client.generate_json.side_effect = [
        GeminiParseError("first failure"),
        _VALID_RESPONSE,
    ]
    gen = HypothesisGenerator(client=mock_client)
    result = gen.generate(_TICKET, {}, _EMPTY_BASELINE, [], "")
    assert isinstance(result, BestHypothesisResult)
    assert mock_client.generate_json.call_count == 2
