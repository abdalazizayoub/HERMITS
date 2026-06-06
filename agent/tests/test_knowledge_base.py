import tempfile
from datetime import datetime

import pytest

from components.knowledge_base.matcher import KBMatcher, _jaccard, _tokenize
from components.knowledge_base.store import KBStore
from components.models.kb_entry import KBEntry, ReconFingerprint, TicketFingerprint
from components.models.ticket import Ticket

_TICKET = Ticket(
    id=7004,
    title="nginx connection refused",
    description="nginx not responding on port 80, connection refused by server",
    customer_id=5004,
    customer_name="DeltaCo",
    priority="high",
    status="OPEN",
    created_at=datetime(2026, 6, 1),
    service_hint="nginx",
)


def _make_entry(service_hint=None, top_errors=None, symptom_keywords=None) -> KBEntry:
    return KBEntry(
        ticket_fingerprint=TicketFingerprint(
            service_hint=service_hint,
            error_patterns=["ERROR: connection refused"],
            symptom_keywords=symptom_keywords or ["nginx", "connection", "refused", "port"],
        ),
        recon_fingerprint=ReconFingerprint(
            failed_services=["nginx"],
            top_errors=top_errors or ["ERROR: connection refused", "FATAL: bind failed"],
            disk_critical=False,
        ),
        root_cause="nginx config syntax error prevented startup",
        fix_commands=["nginx -t", "systemctl restart nginx"],
        validation_passed=True,
        resolution_time_minutes=15,
        technician_id="tech1",
        erp_log_snippet="Fixed nginx config",
    )


def test_append_and_load_roundtrip(tmp_path):
    store = KBStore(path=str(tmp_path / "kb.jsonl"))
    entry = _make_entry()
    store.append(entry)
    loaded = store.load_all()
    assert len(loaded) == 1
    assert loaded[0].id == entry.id
    assert loaded[0].root_cause == entry.root_cause


def test_get_by_id(tmp_path):
    store = KBStore(path=str(tmp_path / "kb.jsonl"))
    entry = _make_entry()
    store.append(entry)
    found = store.get_by_id(entry.id)
    assert found is not None
    assert found.id == entry.id


def test_empty_store_returns_empty(tmp_path):
    store = KBStore(path=str(tmp_path / "kb.jsonl"))
    matcher = KBMatcher(store=store)
    matches = matcher.match(_TICKET)
    assert matches == []


def test_jaccard_similarity():
    a = {"nginx", "connection", "refused"}
    b = {"nginx", "connection", "timeout"}
    score = _jaccard(a, b)
    # intersection=2, union=4
    assert abs(score - 2 / 4) < 1e-9


def test_jaccard_empty():
    assert _jaccard(set(), set()) == 0.0


def test_service_hint_bonus(tmp_path):
    store = KBStore(path=str(tmp_path / "kb.jsonl"))
    entry_with_hint = _make_entry(service_hint="nginx")
    entry_no_hint = _make_entry(service_hint="apache")
    store.append(entry_with_hint)
    store.append(entry_no_hint)

    matcher = KBMatcher(store=store)
    matches = matcher.match(_TICKET, top_k=2)
    assert len(matches) == 2
    # Entry with matching service_hint should rank higher
    assert matches[0].entry.ticket_fingerprint.service_hint == "nginx"


def test_top_k_limit(tmp_path):
    store = KBStore(path=str(tmp_path / "kb.jsonl"))
    for _ in range(5):
        store.append(_make_entry(service_hint="nginx"))
    matcher = KBMatcher(store=store)
    matches = matcher.match(_TICKET, top_k=3)
    assert len(matches) == 3


def test_tokenize_removes_stopwords():
    tokens = _tokenize("the server is down and it was failing")
    assert "the" not in tokens
    assert "is" not in tokens
    assert "server" in tokens
    assert "down" in tokens
