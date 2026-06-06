import logging
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from components.services.runner import Phase1Result

logger = logging.getLogger("hermits.triage.prewarm_cache")


class PrewarmCache:
    """Simple TTL cache with 15-minute TTL. In-memory only."""

    TTL_SECONDS = 900

    def __init__(self):
        self._store: dict[int, tuple["Phase1Result", float]] = {}

    def set(self, ticket_id: int, result: "Phase1Result") -> None:
        self._store[ticket_id] = (result, time.monotonic())
        logger.debug("Cache set for ticket %s", ticket_id)

    def get(self, ticket_id: int) -> Optional["Phase1Result"]:
        if ticket_id not in self._store:
            return None
        if self._is_expired(ticket_id):
            del self._store[ticket_id]
            logger.debug("Cache expired for ticket %s", ticket_id)
            return None
        return self._store[ticket_id][0]

    def invalidate(self, ticket_id: int) -> None:
        self._store.pop(ticket_id, None)
        logger.debug("Cache invalidated for ticket %s", ticket_id)

    def is_warm(self, ticket_id: int) -> bool:
        if ticket_id not in self._store:
            return False
        if self._is_expired(ticket_id):
            del self._store[ticket_id]
            return False
        return True

    def _is_expired(self, ticket_id: int) -> bool:
        if ticket_id not in self._store:
            return True
        _, stored_at = self._store[ticket_id]
        return (time.monotonic() - stored_at) > self.TTL_SECONDS
