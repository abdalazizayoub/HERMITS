import logging
from pathlib import Path

logger = logging.getLogger("hermits.memory.context_loader")

_MAX_CHARS = 8000
_FALLBACK = (
    "No policy document loaded. Apply standard Linux sysadmin best practices "
    "and minimal-change principles."
)


def load_memory_context(memory_path: str = "data/memory.md") -> str:
    """Load memory.md, truncate to 8000 chars, return string."""
    path = Path(memory_path)
    if not path.exists():
        logger.info("No memory file at %s, using fallback", memory_path)
        return _FALLBACK

    content = path.read_text(encoding="utf-8")
    if len(content) > _MAX_CHARS:
        content = content[:_MAX_CHARS] + "\n...[truncated for context window]"
        logger.debug("Memory context truncated to %d chars", _MAX_CHARS)

    return content
