"""Versioned prompt template storage with Jinja2 rendering, search, and history."""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import jinja2


@dataclass
class TemplateVersion:
    content: str
    saved_at: str
    version: int
    tags: List[str] = field(default_factory=list)

    def render(self, **kwargs: Any) -> str:
        """Render the template with Jinja2."""
        return jinja2.Template(self.content).render(**kwargs)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TemplateVersion":
        return cls(**d)


class Promptvault:
    """Versioned prompt template storage with optional JSON persistence."""

    def __init__(self, storage_path: Optional[str] = None):
        self._store: Dict[str, List[TemplateVersion]] = {}
        self._path = Path(storage_path) if storage_path else None
        if self._path and self._path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        with open(self._path, "r", encoding="utf-8") as fh:
            text = fh.read().strip()
        if not text:
            return
        raw = json.loads(text)
        self._store = {
            key: [TemplateVersion.from_dict(v) for v in versions]
            for key, versions in raw.items()
        }

    def _persist(self) -> None:
        if self._path is None:
            return
        data = {
            key: [v.to_dict() for v in versions]
            for key, versions in self._store.items()
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    def save(self, key: str, content: str, tags: Optional[List[str]] = None) -> TemplateVersion:
        """Save a new version of a template."""
        if not key or not key.strip():
            raise ValueError("key must be a non-empty string")
        versions = self._store.setdefault(key, [])
        tv = TemplateVersion(
            content=content,
            saved_at=datetime.now(timezone.utc).isoformat(),
            version=len(versions) + 1,
            tags=list(tags) if tags else [],
        )
        versions.append(tv)
        self._persist()
        return tv

    def get(self, key: str, version: Optional[int] = None) -> Optional[TemplateVersion]:
        """Return a template version; latest if *version* is None."""
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
        """Render a template version with Jinja2; None if key is missing."""
        tv = self.get(key, version)
        if tv is None:
            return None
        return tv.render(**kwargs)

    def history(self, key: str) -> List[TemplateVersion]:
        """Return all versions of a template, oldest first."""
        return list(self._store.get(key, []))

    # ------------------------------------------------------------------
    # Deletion & renaming
    # ------------------------------------------------------------------

    def delete(self, key: str) -> bool:
        """Delete all versions of a template. Returns True if it existed."""
        if key in self._store:
            del self._store[key]
            self._persist()
            return True
        return False

    def delete_version(self, key: str, version: int) -> bool:
        """Delete a specific version. Removes the key when no versions remain."""
        versions = self._store.get(key)
        if not versions:
            return False
        new_versions = [v for v in versions if v.version != version]
        if len(new_versions) == len(versions):
            return False
        if new_versions:
            self._store[key] = new_versions
        else:
            del self._store[key]
        self._persist()
        return True

    def rename(self, old_key: str, new_key: str) -> bool:
        """Rename a template key. Returns True on success."""
        if old_key not in self._store or new_key in self._store:
            return False
        self._store[new_key] = self._store.pop(old_key)
        self._persist()
        return True

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, case_sensitive: bool = False) -> Dict[str, List[TemplateVersion]]:
        """Return templates whose content contains *query*."""
        q = query if case_sensitive else query.lower()
        results: Dict[str, List[TemplateVersion]] = {}
        for key, versions in self._store.items():
            matched = [
                v for v in versions
                if q in (v.content if case_sensitive else v.content.lower())
            ]
            if matched:
                results[key] = matched
        return results

    def search_by_tags(self, tags: List[str]) -> Dict[str, List[TemplateVersion]]:
        """Return templates that have versions containing *all* specified tags."""
        tag_set = set(tags)
        results: Dict[str, List[TemplateVersion]] = {}
        for key, versions in self._store.items():
            matched = [v for v in versions if tag_set.issubset(set(v.tags))]
            if matched:
                results[key] = matched
        return results

    # ------------------------------------------------------------------
    # Listing helpers
    # ------------------------------------------------------------------

    def keys(self) -> List[str]:
        """Return all stored template keys."""
        return list(self._store.keys())

    def list_all_tags(self) -> List[str]:
        """Return a sorted list of every unique tag across all templates."""
        tags: set = set()
        for versions in self._store.values():
            for v in versions:
                tags.update(v.tags)
        return sorted(tags)

    # ------------------------------------------------------------------
    # Import / export
    # ------------------------------------------------------------------

    def export(self, path: str) -> None:
        """Write all templates to a JSON file at *path*."""
        data = {
            key: [v.to_dict() for v in versions]
            for key, versions in self._store.items()
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    def import_from(self, path: str, overwrite: bool = False) -> int:
        """Load templates from a JSON file. Returns the count of keys imported."""
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        count = 0
        for key, versions in raw.items():
            if key in self._store and not overwrite:
                continue
            self._store[key] = [TemplateVersion.from_dict(v) for v in versions]
            count += 1
        self._persist()
        return count

    # ------------------------------------------------------------------
    # Python protocol
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return key in self._store
