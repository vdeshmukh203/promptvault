"""Versioned prompt template storage with Jinja2 render, search, history, and persistence."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, StrictUndefined, TemplateError, UndefinedError

_ENV = Environment(undefined=StrictUndefined)


@dataclass
class TemplateVersion:
    content: str
    saved_at: str
    version: int
    tags: List[str] = field(default_factory=list)

    def render(self, **kwargs: Any) -> str:
        """Render the template with Jinja2 (strict undefined)."""
        return _ENV.from_string(self.content).render(**kwargs)


class RenderError(ValueError):
    """Raised when Jinja2 template rendering fails."""


class Promptvault:
    """Versioned prompt template storage with optional JSON persistence."""

    def __init__(self, path: Optional[str | os.PathLike] = None):
        """Create a vault, optionally backed by a JSON file at *path*."""
        self._store: Dict[str, List[TemplateVersion]] = {}
        self._path: Optional[Path] = Path(path) if path is not None else None
        if self._path is not None and self._path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    def save(self, key: str, content: str, tags: Optional[List[str]] = None) -> TemplateVersion:
        """Save a new version of a template and persist if a path is set."""
        versions = self._store.setdefault(key, [])
        tv = TemplateVersion(
            content=content,
            saved_at=datetime.now(timezone.utc).isoformat(),
            version=len(versions) + 1,
            tags=list(tags or []),
        )
        versions.append(tv)
        self._persist()
        return tv

    def get(self, key: str, version: Optional[int] = None) -> Optional[TemplateVersion]:
        """Return a template version; latest if *version* is ``None``."""
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
        """Render the latest (or specified) template version with Jinja2.

        Raises ``RenderError`` if the template is malformed or a required
        variable is missing.
        """
        tv = self.get(key, version)
        if tv is None:
            return None
        try:
            return tv.render(**kwargs)
        except UndefinedError as exc:
            raise RenderError(f"Missing variable in template '{key}': {exc}") from exc
        except TemplateError as exc:
            raise RenderError(f"Template error in '{key}': {exc}") from exc

    def history(self, key: str) -> List[TemplateVersion]:
        """Return all versions of a template, oldest first."""
        return list(self._store.get(key, []))

    def delete(self, key: str) -> bool:
        """Delete all versions of a template. Returns ``True`` if it existed."""
        if key in self._store:
            del self._store[key]
            self._persist()
            return True
        return False

    def delete_version(self, key: str, version: int) -> bool:
        """Delete a specific version. Returns ``True`` if found and removed."""
        versions = self._store.get(key)
        if not versions:
            return False
        original = len(versions)
        self._store[key] = [v for v in versions if v.version != version]
        if not self._store[key]:
            del self._store[key]
        changed = len(self._store.get(key, [])) < original
        if changed:
            self._persist()
        return changed

    def rename(self, old_key: str, new_key: str) -> bool:
        """Rename a template key. Returns ``True`` on success."""
        if old_key not in self._store or new_key in self._store:
            return False
        self._store[new_key] = self._store.pop(old_key)
        self._persist()
        return True

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, case_sensitive: bool = False) -> Dict[str, List[TemplateVersion]]:
        """Return versions whose *content* contains *query*."""
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

    def search_by_tag(self, tag: str, case_sensitive: bool = False) -> Dict[str, List[TemplateVersion]]:
        """Return versions that carry *tag*."""
        t = tag if case_sensitive else tag.lower()
        results: Dict[str, List[TemplateVersion]] = {}
        for key, versions in self._store.items():
            matched = [
                v for v in versions
                if t in ([x for x in v.tags] if case_sensitive else [x.lower() for x in v.tags])
            ]
            if matched:
                results[key] = matched
        return results

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def keys(self) -> List[str]:
        """Return all stored template keys."""
        return list(self._store.keys())

    def list_all_tags(self) -> List[str]:
        """Return a sorted, deduplicated list of every tag in the vault."""
        tags: set[str] = set()
        for versions in self._store.values():
            for v in versions:
                tags.update(v.tags)
        return sorted(tags)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_to_file(self, path: str | os.PathLike) -> None:
        """Serialise the vault to a JSON file."""
        data = {
            key: [asdict(v) for v in versions]
            for key, versions in self._store.items()
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_from_file(self, path: str | os.PathLike) -> None:
        """Replace the current vault contents from a JSON file."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self._store = {
            key: [TemplateVersion(**v) for v in versions]
            for key, versions in raw.items()
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _persist(self) -> None:
        if self._path is not None:
            self.save_to_file(self._path)

    def _load(self) -> None:
        self.load_from_file(self._path)  # type: ignore[arg-type]
