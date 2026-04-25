"""Versioned prompt template storage with render, search, and history."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class TemplateVersion:
    content: str
    saved_at: str
    version: int
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def render(self, **kwargs: Any) -> str:
        """Render the template with the given keyword arguments."""
        return self.content.format(**kwargs)


class Promptvault:
    """Versioned prompt template storage."""

    def __init__(self):
        self._store: Dict[str, List[TemplateVersion]] = {}

    def save(self, key: str, content: str, tags: Optional[List[str]] = None) -> TemplateVersion:
        """Save a new version of a template."""
        versions = self._store.setdefault(key, [])
        tv = TemplateVersion(
            content=content,
            saved_at=datetime.now(timezone.utc).isoformat(),
            version=len(versions) + 1,
            tags=tags or [],
        )
        versions.append(tv)
        return tv

    def get(self, key: str, version: Optional[int] = None) -> Optional[TemplateVersion]:
        """Get a template version. Returns latest if version is None."""
        versions = self._store.get(key)
        if not versions:
            return None
        if version is None:
            return versions[-1]
        for v in versions:
            if v.version == version:
                return v
        return None

    def render(self, key: str, version: Optional[int] = None, **kwargs: Any) -> Optional[str]:
        """Render the latest (or specified) template version with kwargs."""
        tv = self.get(key, version)
        if tv is None:
            return None
        return tv.render(**kwargs)

    def history(self, key: str) -> List[TemplateVersion]:
        """Return all versions of a template, oldest first."""
        return list(self._store.get(key, []))

    def delete(self, key: str) -> bool:
        """Delete all versions of a template. Returns True if it existed."""
        if key in self._store:
            del self._store[key]
            return True
        return False

    def delete_version(self, key: str, version: int) -> bool:
        """Delete a specific version. Returns True if found and removed."""
        versions = self._store.get(key)
        if not versions:
            return False
        original = len(versions)
        self._store[key] = [v for v in versions if v.version != version]
        return len(self._store[key]) < original

    def rename(self, old_key: str, new_key: str) -> bool:
        """Rename a template key. Returns True on success."""
        if old_key not in self._store or new_key in self._store:
            return False
        self._store[new_key] = self._store.pop(old_key)
        return True

    def search(self, query: str, case_sensitive: bool = False) -> Dict[str, List[TemplateVersion]]:
        """Search for templates whose content contains the query string."""
        q = query if case_sensitive else query.lower()
        results: Dict[str, List[TemplateVersion]] = {}
        for key, versions in self._store.items():
            matched = [v for v in versions if q in (v.content if case_sensitive else v.content.lower())]
            if matched:
                results[key] = matched
        return results

    def keys(self) -> List[str]:
        """Return all stored template keys."""
        return list(self._store.keys())
