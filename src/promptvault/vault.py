"""Versioned prompt template storage."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

@dataclass
class TemplateVersion:
    content: str
    saved_at: str
    version: int

class Promptvault:
    """Versioned prompt template storage."""
    def __init__(self):
        self._store: Dict[str, List[TemplateVersion]] = {}

    def save(self, key: str, content: str) -> TemplateVersion:
        """Save a new version of a template."""
        versions = self._store.setdefault(key, [])
        tv = TemplateVersion(
            content=content,
            saved_at=datetime.now(timezone.utc).isoformat(),
            version=len(versions) + 1,
        )
        versions.append(tv)
        return tv

    def get(self, key: str, version: Optional[int] = None) -> Optional[TemplateVersion]:
        """Get a template version (latest by default)."""
        versions = self._store.get(key)
        if not versions:
            return None
        if version is None:
            return versions[-1]
        for v in versions:
            if v.version == version:
                return v
        return None

    def history(self, key: str) -> List[TemplateVersion]:
        """Return all versions of a template."""
        return list(self._store.get(key, []))

    def keys(self) -> List[str]:
        """Return all stored template keys."""
        return list(self._store.keys())
