import logging
import re
from typing import Optional

from components.knowledge_base.store import KBStore
from components.models.kb_entry import KBMatch
from components.models.ticket import Ticket

logger = logging.getLogger("hermits.knowledge_base.matcher")

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "on",
    "at", "for", "with", "from", "by",
}


def _tokenize(text: str) -> set[str]:
    tokens = re.split(r"[^a-z0-9]+", text.lower())
    return {t for t in tokens if t and t not in _STOPWORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def _keyword_overlap(ticket_tokens: set[str], stored_keywords: list[str]) -> float:
    stored_set = set(stored_keywords)
    if not ticket_tokens and not stored_set:
        return 0.0
    matches = len(ticket_tokens & stored_set)
    denom = max(len(ticket_tokens), len(stored_set))
    return matches / denom if denom else 0.0


class KBMatcher:
    def __init__(self, store: Optional[KBStore] = None):
        self.store = store or KBStore()

    def match(
        self,
        ticket: Ticket,
        recon_output: Optional[dict] = None,
        top_k: int = 3,
    ) -> list[KBMatch]:
        entries = self.store.load_all()
        if not entries:
            return []

        ticket_tokens = _tokenize(ticket.title + " " + ticket.description)

        # Build incoming error tokens from recon if available
        incoming_errors: set[str] = set()
        if recon_output:
            logs = recon_output.get("logs", [])
            if isinstance(logs, list):
                for line in logs:
                    incoming_errors |= _tokenize(str(line))
            elif isinstance(logs, str):
                incoming_errors = _tokenize(logs)

        scored: list[KBMatch] = []
        for entry in entries:
            stored_error_tokens = _tokenize(" ".join(entry.recon_fingerprint.top_errors))
            jaccard = _jaccard(incoming_errors, stored_error_tokens)
            kw_overlap = _keyword_overlap(
                ticket_tokens, entry.ticket_fingerprint.symptom_keywords
            )
            service_bonus = (
                0.3
                if ticket.service_hint
                and ticket.service_hint == entry.ticket_fingerprint.service_hint
                else 0.0
            )
            final_score = min(1.0, 0.4 * jaccard + 0.35 * kw_overlap + service_bonus)
            confidence_boost = min(0.4, final_score * 0.4)
            scored.append(KBMatch(entry=entry, similarity_score=final_score, confidence_boost=confidence_boost))

        scored.sort(key=lambda m: m.similarity_score, reverse=True)
        return scored[:top_k]
