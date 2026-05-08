# Changelog

All notable changes to promptvault are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-08

### Fixed
- Replaced `str.format()` rendering with Jinja2 as documented in the JOSS paper.
- `TemplateVersion.tags` now uses `field(default_factory=list)` instead of a `None`
  sentinel, eliminating the mutable-default anti-pattern.
- `delete_version` removes the key entirely when its last version is deleted.

### Added
- `RenderError` exception raised (instead of crashing) on undefined variables or
  malformed Jinja2 templates.
- `search_by_tag(tag)` — tag-based search across all template versions.
- `list_all_tags()` — sorted, deduplicated list of every tag in the vault.
- JSON persistence: `save_to_file(path)` / `load_from_file(path)` and automatic
  persistence when a `path` is passed to `Promptvault(path=…)`.
- Tkinter GUI (`promptvault-gui` entry point) with template browser, version
  history, render panel, content/tag search, and file open/save.
- `RenderError` and `TemplateVersion` exported from the top-level package.
- `pyproject.toml`: declared `jinja2>=3.0` dependency and `[dev]` extras.

## [0.1.0] - 2026-04-25

### Added
- Initial release of promptvault.
- Versioned storage of named prompt templates.
- Tag-based search across templates and versions.
- Jinja2 rendering for parameterized prompts.
