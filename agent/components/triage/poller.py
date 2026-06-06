import logging
import os
import threading
import time
from typing import Protocol, runtime_checkable

from components.services.runner import Phase1Result, HermitsAgent
from components.gemini_client import GeminiClient
from components.models.ticket import Ticket
from components.triage.prewarm_cache import PrewarmCache

logger = logging.getLogger("hermits.triage.poller")


@runtime_checkable
class ERPClient(Protocol):
    def list_open_tickets(self) -> list[Ticket]: ...
    def get_ticket(self, ticket_id: int) -> Ticket: ...


_URGENCY_SYSTEM = """\
You are a sysadmin triage expert. Given a ticket, return a JSON urgency score from 0.0 to 1.0 based on: severity of the symptom described, customer impact, time since the ticket was created, and the priority field. Higher = more urgent. Return ONLY JSON:
{"urgency_score": 0.85, "rationale": "..."}"""


class TriagePoller:
    """
    Polls the ERP for open tickets every POLL_INTERVAL_SECONDS (default 120).
    Scores each ticket for urgency, sorts them, pre-warms top N (default 3).
    Runs in a background thread.
    """

    POLL_INTERVAL_SECONDS = int(os.getenv("TRIAGE_POLL_INTERVAL_SECONDS", "120"))
    PREWARM_TOP_N = int(os.getenv("TRIAGE_PREWARM_TOP_N", "3"))

    def __init__(
        self,
        erp_client: ERPClient,
        agent: HermitsAgent | None = None,
        cache: PrewarmCache | None = None,
        gemini_client: GeminiClient | None = None,
    ):
        self.erp = erp_client
        self.agent = agent or HermitsAgent()
        self.cache = cache or self.agent.cache
        self.gemini = gemini_client or GeminiClient()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _score_urgency(self, ticket: Ticket) -> float:
        user_message = (
            f"Title: {ticket.title}\n"
            f"Description: {ticket.description}\n"
            f"Priority: {ticket.priority}\n"
            f"Created at: {ticket.created_at.isoformat()}"
        )
        try:
            data = self.gemini.generate_json(_URGENCY_SYSTEM, user_message)
            score = float(data.get("urgency_score", 0.5))
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.warning("Urgency scoring failed for ticket %s: %s", ticket.id, e)
            return 0.5

    def _poll_once(self) -> None:
        try:
            tickets = self.erp.list_open_tickets()
            logger.info("Poller found %d open tickets", len(tickets))
        except Exception as e:
            logger.error("Failed to list open tickets: %s", e)
            return

        scored = []
        for ticket in tickets:
            score = self._score_urgency(ticket)
            scored.append((ticket, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        for ticket, score in scored[: self.PREWARM_TOP_N]:
            if self.cache.is_warm(ticket.id):
                logger.debug("Ticket %s already warm, skipping", ticket.id)
                continue
            try:
                logger.info("Pre-warming ticket %s (urgency=%.2f)", ticket.id, score)
                result: Phase1Result = self.agent.run_ticket_phase1(
                    ticket=ticket,
                    technician_id="prewarm",
                )
                self.cache.set(ticket.id, result)
            except Exception as e:
                logger.error("Pre-warm failed for ticket %s: %s", ticket.id, e)

    def _run_loop(self) -> None:
        logger.info("TriagePoller started (interval=%ds)", self.POLL_INTERVAL_SECONDS)
        while not self._stop_event.is_set():
            self._poll_once()
            self._stop_event.wait(timeout=self.POLL_INTERVAL_SECONDS)
        logger.info("TriagePoller stopped")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.warning("TriagePoller already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="TriagePoller")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)


if __name__ == "__main__":
    import sys

    print("TriagePoller requires an ERPClient instance. Import and call poller.start() from your app.")
    sys.exit(0)
