"""Versioned prompt template storage with render, search, and history."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import jinja2

_jinja_env = jinja2.Environment(undefined=jinja2.StrictUndefined)


@dataclass
class TemplateVersion:
    content: str
    saved_at: str
    version: int
    tags: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"TemplateVersion(version={self.version}, "
            f"saved_at={self.saved_at!r}, tags={self.tags!r})"
        )

    def render(self, **kwargs: Any) -> str:
        """Render the template with Jinja2 using the given keyword arguments."""
        return _jinja_env.from_string(self.content).render(**kwargs)

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "saved_at": self.saved_at,
            "version": self.version,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TemplateVersion:
        return cls(
            content=data["content"],
            saved_at=data["saved_at"],
            version=data["version"],
            tags=data.get("tags", []),
        )


class Promptvault:
    """Versioned prompt template storage with optional JSON persistence.

    Parameters
    ----------
    path:
        Optional path to a JSON file used for persistence.  If the file
        exists it is loaded on construction; every mutating operation
        automatically writes it back.
    """

    def __init__(self, path: Optional[str | os.PathLike] = None) -> None:
        self._store: Dict[str, List[TemplateVersion]] = {}
        self._path: Optional[Path] = Path(path) if path is not None else None
        if self._path and self._path.exists():
            self._load()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        with self._path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self._store = {
            key: [TemplateVersion.from_dict(v) for v in versions]
            for key, versions in raw.items()
        }

    def _autosave(self) -> None:
        if self._path is not None:
            self.save_to_disk()

    def save_to_disk(self) -> None:
        """Write the vault to its configured JSON file (atomic replace)."""
        if self._path is None:
            raise ValueError("No file path configured for this vault.")
        tmp = self._path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(
                {k: [v.to_dict() for v in vs] for k, vs in self._store.items()},
                fh,
                indent=2,
            )
        tmp.replace(self._path)

    # ------------------------------------------------------------------ #
    # Core CRUD
    # ------------------------------------------------------------------ #

    def save(
        self,
        key: str,
        content: str,
        tags: Optional[List[str]] = None,
    ) -> TemplateVersion:
        """Save a new version of a template and return it."""
        if not key:
            raise ValueError("key must not be empty")
        versions = self._store.setdefault(key, [])
        tv = TemplateVersion(
            content=content,
            saved_at=datetime.now(timezone.utc).isoformat(),
            version=len(versions) + 1,
            tags=list(tags) if tags else [],
        )
        versions.append(tv)
        self._autosave()
        return tv

    def get(self, key: str, version: Optional[int] = None) -> Optional[TemplateVersion]:
        """Return a template version; the latest version if *version* is None."""
        versions = self._store.get(key)
        if not versions:
            return None
        if version is None:
            return versions[-1]
        for v in versions:
            if v.version == version:
                return v
        return None

    def render(
        self,
        key: str,
        version: Optional[int] = None,
        **kwargs: Any,
    ) -> Optional[str]:
        """Render the latest (or specified) template version with Jinja2."""
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
            self._autosave()
            return True
        return False

    def delete_version(self, key: str, version: int) -> bool:
        """Delete a specific version. Returns True if found and removed.

        If removing the version leaves the key empty, the key itself is
        also removed.
        """
        versions = self._store.get(key)
        if not versions:
            return False
        original_len = len(versions)
        remaining = [v for v in versions if v.version != version]
        if len(remaining) == original_len:
            return False
        if remaining:
            self._store[key] = remaining
        else:
            del self._store[key]
        self._autosave()
        return True

    def rename(self, old_key: str, new_key: str) -> bool:
        """Rename a template key. Returns True on success."""
        if not new_key:
            raise ValueError("new_key must not be empty")
        if old_key not in self._store or new_key in self._store:
            return False
        self._store[new_key] = self._store.pop(old_key)
        self._autosave()
        return True

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #

    def search(
        self,
        query: str,
        case_sensitive: bool = False,
    ) -> Dict[str, List[TemplateVersion]]:
        """Return versions whose *content* contains *query*."""
        q = query if case_sensitive else query.lower()
        results: Dict[str, List[TemplateVersion]] = {}
        for key, versions in self._store.items():
            matched = [
                v
                for v in versions
                if q in (v.content if case_sensitive else v.content.lower())
            ]
            if matched:
                results[key] = matched
        return results

    def search_by_tags(self, *tags: str) -> Dict[str, List[TemplateVersion]]:
        """Return versions that carry *all* of the specified tags."""
        tag_set = set(tags)
        results: Dict[str, List[TemplateVersion]] = {}
        for key, versions in self._store.items():
            matched = [v for v in versions if tag_set.issubset(set(v.tags))]
            if matched:
                results[key] = matched
        return results

    # ------------------------------------------------------------------ #
    # Listing / serialisation
    # ------------------------------------------------------------------ #

    def keys(self) -> List[str]:
        """Return all stored template keys."""
        return list(self._store.keys())

    def export_json(self) -> str:
        """Serialise the entire vault to a JSON string."""
        return json.dumps(
            {k: [v.to_dict() for v in vs] for k, vs in self._store.items()},
            indent=2,
        )

    @classmethod
    def import_json(cls, data: str) -> Promptvault:
        """Deserialise a vault from a JSON string produced by *export_json*."""
        vault = cls()
        raw = json.loads(data)
        vault._store = {
            key: [TemplateVersion.from_dict(v) for v in versions]
            for key, versions in raw.items()
        }
        return vault
