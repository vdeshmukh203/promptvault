# Changelog

All notable changes to promptvault are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-30

### Added
- Jinja2 rendering engine (replaces `str.format`); templates now use `{{ variable }}` syntax.
- `search_by_tag(tag)` method for tag-based retrieval.
- `save_to_file(path)` / `load_from_file(path)` for JSON persistence.
- `RenderError` and `PromptVaultError` exception hierarchy.
- `TemplateVersion` and exception classes exported from the top-level package.
- Tkinter GUI (`promptvault-gui` entry point) with key list, version selector, Jinja2 editor, search, and render dialog.
- `StrictUndefined` Jinja2 mode — undefined variables raise `RenderError` instead of silently producing empty strings.
- `dataclasses.field(default_factory=list)` for `tags` to prevent shared mutable defaults.
- Expanded test suite (29 tests covering persistence, tag search, render errors, and mutation isolation).

## [0.1.0] - 2026-04-25

### Added
- Initial release of promptvault.
- Versioned storage of named prompt templates.
- Tag-based search across templates and versions.
- Jinja2 rendering for parameterized prompts.
