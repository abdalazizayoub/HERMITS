import logging
import os
from pathlib import Path

logger = logging.getLogger("hermits.memory.context_loader")

_MAX_CHARS = 8000
_FALLBACK = (
    "No policy document loaded. Apply standard Linux sysadmin best practices "
    "and minimal-change principles."
)

# Module-level cache: (content, mtime). Invalidated when file changes on disk.
_cache: tuple[str, float] | None = None


def load_memory_context(memory_path: str = "data/memory.md") -> str:
    """Load memory.md with mtime-based caching — re-reads only when file changes."""
    global _cache
    path = Path(memory_path)
    if not path.exists():
        logger.info("No memory file at %s, using fallback", memory_path)
        return _FALLBACK

    mtime = path.stat().st_mtime
    if _cache is not None and _cache[1] == mtime:
        return _cache[0]

    content = path.read_text(encoding="utf-8")
    if len(content) > _MAX_CHARS:
        content = content[:_MAX_CHARS] + "\n...[truncated for context window]"
        logger.debug("Memory context truncated to %d chars", _MAX_CHARS)

    _cache = (content, mtime)
    return content
