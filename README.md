# promptvault

Versioned prompt template storage with Jinja2 rendering, tag-based search, and JSON persistence.

## Installation

```bash
pip install promptvault
```

## Quick start

```python
from promptvault import Promptvault

vault = Promptvault()

# Save versions of a template (Jinja2 syntax)
vault.save("greeting", "Hello, {{ name }}!", tags=["production"])
vault.save("greeting", "Hi there, {{ name }}! How are you?")

# Render the latest version
print(vault.render("greeting", name="Alice"))
# → Hi there, Alice! How are you?

# Render a specific version
print(vault.render("greeting", version=1, name="Bob"))
# → Hello, Bob!

# Browse history
for tv in vault.history("greeting"):
    print(tv.version, tv.saved_at, tv.tags)

# Search by content or tag
vault.search("{{ name }}")        # → {"greeting": [...]}
vault.search_by_tag("production") # → {"greeting": [v1]}

# Persist to disk
vault.save_to_file("my_vault.json")
vault2 = Promptvault.load_from_file("my_vault.json")
```

## GUI

A graphical interface is included. Launch it with:

```bash
promptvault-gui
```

Or from Python:

```python
from promptvault.gui import main
main()
```

The GUI lets you create, edit, and version templates; search by content; render
with variable substitution; and save/load vault files.

## API reference

| Method | Description |
|---|---|
| `save(key, content, tags=None)` | Save a new version; returns `TemplateVersion` |
| `get(key, version=None)` | Get latest (or specific) version |
| `render(key, version=None, **kwargs)` | Render with Jinja2; returns `None` if key missing |
| `history(key)` | All versions, oldest first |
| `delete(key)` | Delete all versions of a key |
| `delete_version(key, version)` | Delete one specific version |
| `rename(old_key, new_key)` | Rename a key |
| `search(query, case_sensitive=False)` | Find by content substring |
| `search_by_tag(tag)` | Find by tag |
| `keys()` | List all stored keys |
| `save_to_file(path)` | Persist vault to JSON |
| `Promptvault.load_from_file(path)` | Load vault from JSON |

## License

MIT
