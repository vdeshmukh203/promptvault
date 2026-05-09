"""Versioned prompt template storage with render, search, and history."""
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError


class PromptVaultError(Exception):
    """Base exception for promptvault errors."""


class TemplateNotFoundError(PromptVaultError):
    """Raised when a requested template key or version does not exist."""


class RenderError(PromptVaultError):
    """Raised when Jinja2 rendering fails due to syntax or undefined variables."""


_jinja_env = Environment(undefined=StrictUndefined)


@dataclass
class TemplateVersion:
    content: str
    saved_at: str
    version: int
    tags: List[str] = field(default_factory=list)

    def render(self, **kwargs: Any) -> str:
        """Render the template with Jinja2 using the given keyword arguments."""
        try:
            return _jinja_env.from_string(self.content).render(**kwargs)
        except UndefinedError as exc:
            raise RenderError(f"Undefined variable: {exc}") from exc
        except TemplateSyntaxError as exc:
            raise RenderError(f"Template syntax error: {exc}") from exc

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "saved_at": self.saved_at,
            "version": self.version,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateVersion":
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
        Optional path to a JSON file.  If the file already exists its
        contents are loaded on construction.  Every mutating operation
        (save, delete, rename) automatically writes the updated state back
        to disk when a path is configured.
    """

    def __init__(self, path: Optional[Union[str, Path]] = None):
        self._store: Dict[str, List[TemplateVersion]] = {}
        self._path: Optional[Path] = Path(path) if path else None
        if self._path and self._path.exists():
            self._load()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        with open(self._path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self._store = {
            key: [TemplateVersion.from_dict(v) for v in versions]
            for key, versions in raw.items()
        }

    def save_to_disk(self) -> None:
        """Write the current vault state to the configured JSON file."""
        if self._path is None:
            raise PromptVaultError("No file path configured; construct Promptvault(path=…).")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._to_raw(), fh, indent=2)

    def export_json(self, path: Union[str, Path]) -> None:
        """Export all templates to an arbitrary JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self._to_raw(), fh, indent=2)

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "Promptvault":
        """Load a Promptvault instance from an existing JSON file."""
        return cls(path=path)

    def _to_raw(self) -> Dict[str, Any]:
        return {
            key: [v.to_dict() for v in versions]
            for key, versions in self._store.items()
        }

    def _persist(self) -> None:
        if self._path:
            self.save_to_disk()

    # ------------------------------------------------------------------ #
    # Core CRUD
    # ------------------------------------------------------------------ #

    def save(self, key: str, content: str, tags: Optional[List[str]] = None) -> TemplateVersion:
        """Save a new version of a template and optionally persist to disk."""
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
        """Return a template version; latest if *version* is ``None``.

        Returns ``None`` when the key (or specific version) does not exist.
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

    def render(self, key: str, version: Optional[int] = None, **kwargs: Any) -> str:
        """Render a template with Jinja2.

        Raises
        ------
        TemplateNotFoundError
            When *key* (or *version*) does not exist in the vault.
        RenderError
            When Jinja2 rendering fails (undefined variable, syntax error).
        """
        tv = self.get(key, version)
        if tv is None:
            raise TemplateNotFoundError(
                f"Template '{key}'" +
                (f" version {version}" if version is not None else "") +
                " not found."
            )
        return tv.render(**kwargs)

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
        changed = len(self._store[key]) < original
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

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #

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
        """Return templates that carry *tag* in at least one version."""
        results: Dict[str, List[TemplateVersion]] = {}
        for key, versions in self._store.items():
            matched = [v for v in versions if tag in v.tags]
            if matched:
                results[key] = matched
        return results

    def keys(self) -> List[str]:
        """Return all stored template keys."""
        return list(self._store.keys())
