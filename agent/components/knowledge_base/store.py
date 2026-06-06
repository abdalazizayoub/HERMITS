import json
import logging
import os
from pathlib import Path
from typing import Optional

from filelock import FileLock

from components.models.kb_entry import KBEntry

logger = logging.getLogger("hermits.knowledge_base.store")

_DEFAULT_PATH = os.path.join(os.getenv("HERMITS_DATA_DIR", "./data"), "knowledge_base.jsonl")


class KBStore:
    def __init__(self, path: str = _DEFAULT_PATH):
        self.path = Path(path)
        self.lock_path = Path(str(path) + ".lock")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: KBEntry) -> None:
        with FileLock(str(self.lock_path)):
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        logger.debug("KB entry %s appended", entry.id)

    def load_all(self) -> list[KBEntry]:
        if not self.path.exists():
            return []
        entries = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(KBEntry.model_validate_json(line))
                except Exception as e:
                    logger.warning("Skipping corrupt KB line: %s", e)
        return entries

    def get_by_id(self, entry_id: str) -> Optional[KBEntry]:
        for entry in self.load_all():
            if entry.id == entry_id:
                return entry
        return None
