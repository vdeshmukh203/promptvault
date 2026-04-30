"""Versioned prompt template storage with Jinja2 rendering, search, and persistence."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from jinja2 import BaseLoader, Environment, StrictUndefined, TemplateSyntaxError, UndefinedError


class PromptVaultError(Exception):
    """Base exception for promptvault."""


class RenderError(PromptVaultError):
    """Raised when a Jinja2 template cannot be rendered."""


@dataclass
class TemplateVersion:
    """A single versioned snapshot of a prompt template."""

    content: str
    saved_at: str
    version: int
    tags: List[str] = field(default_factory=list)

    def render(self, **kwargs: Any) -> str:
        """Render the template with Jinja2 using the given keyword arguments."""
        env = Environment(loader=BaseLoader(), undefined=StrictUndefined)
        try:
            return env.from_string(self.content).render(**kwargs)
        except (TemplateSyntaxError, UndefinedError) as exc:
            raise RenderError(str(exc)) from exc


class Promptvault:
    """Versioned prompt template storage with Jinja2 rendering."""

    def __init__(self) -> None:
        self._store: Dict[str, List[TemplateVersion]] = {}

    def save(
        self,
        key: str,
        content: str,
        tags: Optional[List[str]] = None,
    ) -> TemplateVersion:
        """Save a new version of a template and return it."""
        versions = self._store.setdefault(key, [])
        tv = TemplateVersion(
            content=content,
            saved_at=datetime.now(timezone.utc).isoformat(),
            version=len(versions) + 1,
            tags=list(tags) if tags else [],
        )
        versions.append(tv)
        return tv

    def get(self, key: str, version: Optional[int] = None) -> Optional[TemplateVersion]:
        """Return a template version; the latest if *version* is None."""
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
        """Render a template with Jinja2; returns None if the key does not exist."""
        tv = self.get(key, version)
        if tv is None:
            return None
        return tv.render(**kwargs)

    def history(self, key: str) -> List[TemplateVersion]:
        """Return all versions of a template, oldest first."""
        return list(self._store.get(key, []))

    def delete(self, key: str) -> bool:
        """Delete all versions of a template. Returns True if the key existed."""
        if key in self._store:
            del self._store[key]
            return True
        return False

    def delete_version(self, key: str, version: int) -> bool:
        """Delete a specific version. Returns True if it was found and removed."""
        versions = self._store.get(key)
        if not versions:
            return False
        original_len = len(versions)
        self._store[key] = [v for v in versions if v.version != version]
        return len(self._store[key]) < original_len

    def rename(self, old_key: str, new_key: str) -> bool:
        """Rename a template key. Returns True on success, False on conflict or missing key."""
        if old_key not in self._store or new_key in self._store:
            return False
        self._store[new_key] = self._store.pop(old_key)
        return True

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

    def search_by_tag(self, tag: str) -> Dict[str, List[TemplateVersion]]:
        """Return templates that include *tag* in their tag list."""
        results: Dict[str, List[TemplateVersion]] = {}
        for key, versions in self._store.items():
            matched = [v for v in versions if tag in v.tags]
            if matched:
                results[key] = matched
        return results

    def keys(self) -> List[str]:
        """Return all stored template keys."""
        return list(self._store.keys())

    def save_to_file(self, path: Union[str, Path]) -> None:
        """Persist the vault to a JSON file."""
        data: Dict[str, list] = {
            key: [
                {
                    "content": v.content,
                    "saved_at": v.saved_at,
                    "version": v.version,
                    "tags": v.tags,
                }
                for v in versions
            ]
            for key, versions in self._store.items()
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load_from_file(cls, path: Union[str, Path]) -> "Promptvault":
        """Load a vault previously saved with :meth:`save_to_file`."""
        vault = cls()
        data: Dict[str, list] = json.loads(Path(path).read_text(encoding="utf-8"))
        for key, versions in data.items():
            vault._store[key] = [
                TemplateVersion(
                    content=v["content"],
                    saved_at=v["saved_at"],
                    version=v["version"],
                    tags=v.get("tags", []),
                )
                for v in versions
            ]
        return vault
