# Changelog

All notable changes to promptvault are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-27

### Added
- **Jinja2 rendering** – templates are now rendered via the Jinja2 templating
  engine, matching the description in the JOSS paper.  Conditionals, loops,
  filters, and all standard Jinja2 constructs are supported.
- **Persistence** – `Promptvault.export(path)`, `Promptvault.load(path)`, and
  the class-method `Promptvault.from_file(path)` serialise/restore the vault
  to/from a JSON file.
- **`TemplateVersion.to_dict()` / `TemplateVersion.from_dict()`** – round-trip
  serialisation helpers used by the persistence layer.
- **`search_by_tag(tag)`** – retrieve all templates/versions carrying a
  specific tag.
- **`__len__`** – `len(vault)` returns the number of distinct template keys.
- **`__contains__`** – `"key" in vault` membership testing.
- **Tkinter GUI** – a full desktop interface accessible via `promptvault` CLI
  or `python -m promptvault`, offering an editor, version history browser,
  Jinja2 render preview, tag management, and export/import.
- **`promptvault` console-script entry point** to launch the GUI.

### Fixed
- `delete_version` now removes the key entirely when the last version is
  deleted, preventing stale empty entries in the store.
- `TemplateVersion.tags` uses `field(default_factory=list)` to avoid the
  shared-mutable-default pitfall.
- `save` and `rename` validate that key/new_key are non-empty strings, raising
  `ValueError` / `TypeError` on bad input.

### Changed
- Version bumped to **0.2.0**.
- `jinja2 >= 3.0` added as a runtime dependency.
- `TemplateVersion` exported from the top-level package alongside `Promptvault`.

## [0.1.0] - 2026-04-25

### Added
- Initial release of promptvault.
- Versioned storage of named prompt templates.
- Tag-based search across templates and versions.
