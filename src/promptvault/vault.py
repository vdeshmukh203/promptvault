"""Versioned prompt template storage with render, search, history, and persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from jinja2 import Template as _Jinja2Template, UndefinedError as _UndefinedError

    _JINJA2 = True
except ImportError:  # pragma: no cover – jinja2 is a declared dependency
    _JINJA2 = False


@dataclass
class TemplateVersion:
    """A single saved version of a prompt template."""

    content: str
    saved_at: str
    version: int
    tags: List[str] = field(default_factory=list)

    def render(self, **kwargs: Any) -> str:
        """Render the template with *kwargs*, using Jinja2 when available."""
        if _JINJA2:
            return _Jinja2Template(self.content).render(**kwargs)
        return self.content.format(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise this version to a JSON-compatible dictionary."""
        return {
            "content": self.content,
            "saved_at": self.saved_at,
            "version": self.version,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateVersion":
        """Deserialise a version from a dictionary produced by :meth:`to_dict`."""
        return cls(
            content=data["content"],
            saved_at=data["saved_at"],
            version=int(data["version"]),
            tags=list(data.get("tags", [])),
        )


class Promptvault:
    """Versioned prompt template storage.

    All data are held in-memory and can be persisted to / restored from a JSON
    file via :meth:`export` / :meth:`load`.
    """

    def __init__(self) -> None:
        self._store: Dict[str, List[TemplateVersion]] = {}

    # ------------------------------------------------------------------ #
    # core CRUD                                                             #
    # ------------------------------------------------------------------ #

    def save(
        self,
        key: str,
        content: str,
        tags: Optional[List[str]] = None,
    ) -> TemplateVersion:
        """Save a new version of *key* and return the created :class:`TemplateVersion`.

        Parameters
        ----------
        key:
            Non-empty string identifier for the template.
        content:
            Template text (Jinja2 syntax when jinja2 is installed, otherwise
            Python :meth:`str.format` syntax).
        tags:
            Optional free-form labels for retrieval via :meth:`search_by_tag`.
        """
        if not key or not isinstance(key, str):
            raise ValueError("key must be a non-empty string")
        if not isinstance(content, str):
            raise TypeError("content must be a string")
        versions = self._store.setdefault(key, [])
        tv = TemplateVersion(
            content=content,
            saved_at=datetime.now(timezone.utc).isoformat(),
            version=len(versions) + 1,
            tags=list(tags) if tags is not None else [],
        )
        versions.append(tv)
        return tv

    def get(self, key: str, version: Optional[int] = None) -> Optional[TemplateVersion]:
        """Return a template version, or *None* if not found.

        When *version* is ``None`` the latest version is returned.
        """
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
        self, key: str, version: Optional[int] = None, **kwargs: Any
    ) -> Optional[str]:
        """Render template *key* (latest or *version*) substituting *kwargs*.

        Returns *None* when *key* does not exist.  Raises
        ``jinja2.UndefinedError`` / :class:`KeyError` when a required variable
        is absent from *kwargs*.
        """
        tv = self.get(key, version)
        if tv is None:
            return None
        return tv.render(**kwargs)

    def history(self, key: str) -> List[TemplateVersion]:
        """Return all saved versions of *key*, oldest first."""
        return list(self._store.get(key, []))

    # ------------------------------------------------------------------ #
    # deletion / mutation                                                   #
    # ------------------------------------------------------------------ #

    def delete(self, key: str) -> bool:
        """Delete all versions of *key*.  Returns *True* if the key existed."""
        if key in self._store:
            del self._store[key]
            return True
        return False

    def delete_version(self, key: str, version: int) -> bool:
        """Delete a specific version of *key*.

        The key itself is removed when no versions remain.  Returns *True* if
        the requested version was found and deleted.
        """
        versions = self._store.get(key)
        if not versions:
            return False
        remaining = [v for v in versions if v.version != version]
        if len(remaining) == len(versions):
            return False  # version not found
        if remaining:
            self._store[key] = remaining
        else:
            del self._store[key]
        return True

    def rename(self, old_key: str, new_key: str) -> bool:
        """Rename *old_key* to *new_key*.

        Returns *False* when *old_key* does not exist or *new_key* is already
        taken; raises :class:`ValueError` for an empty *new_key*.
        """
        if not new_key or not isinstance(new_key, str):
            raise ValueError("new_key must be a non-empty string")
        if old_key not in self._store or new_key in self._store:
            return False
        self._store[new_key] = self._store.pop(old_key)
        return True

    # ------------------------------------------------------------------ #
    # search                                                                #
    # ------------------------------------------------------------------ #

    def search(
        self, query: str, case_sensitive: bool = False
    ) -> Dict[str, List[TemplateVersion]]:
        """Return templates whose content contains *query*.

        Parameters
        ----------
        query:
            Sub-string to look for.
        case_sensitive:
            When *False* (default) matching is case-insensitive.
        """
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

    def search_by_tag(self, tag: str) -> Dict[str, List[TemplateVersion]]:
        """Return templates that have at least one version carrying *tag*."""
        results: Dict[str, List[TemplateVersion]] = {}
        for key, versions in self._store.items():
            matched = [v for v in versions if tag in v.tags]
            if matched:
                results[key] = matched
        return results

    # ------------------------------------------------------------------ #
    # introspection                                                          #
    # ------------------------------------------------------------------ #

    def keys(self) -> List[str]:
        """Return all stored template keys."""
        return list(self._store.keys())

    def __len__(self) -> int:
        """Return the number of distinct template keys."""
        return len(self._store)

    def __contains__(self, key: object) -> bool:
        """Support ``"key" in vault`` membership testing."""
        return key in self._store

    # ------------------------------------------------------------------ #
    # persistence                                                           #
    # ------------------------------------------------------------------ #

    def export(self, path: str) -> None:
        """Serialise the entire vault to a JSON file at *path*."""
        data = {
            key: [v.to_dict() for v in versions]
            for key, versions in self._store.items()
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def load(self, path: str) -> None:
        """Merge templates from a JSON file written by :meth:`export`.

        Keys that already exist in the vault are **not** overwritten; only new
        keys are imported.
        """
        with open(path, encoding="utf-8") as fh:
            data: Dict[str, Any] = json.load(fh)
        for key, versions in data.items():
            if key not in self._store:
                self._store[key] = [TemplateVersion.from_dict(v) for v in versions]

    @classmethod
    def from_file(cls, path: str) -> "Promptvault":
        """Create a new :class:`Promptvault` populated from a JSON file."""
        vault = cls()
        vault.load(path)
        return vault
