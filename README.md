# promptvault

Versioned prompt template storage with history tracking, Jinja2 rendering, tag-based search, JSON persistence, and a Tkinter GUI.

## Installation

```bash
pip install promptvault
```

## Quick start

```python
from promptvault import Promptvault

vault = Promptvault()                          # in-memory
vault = Promptvault(path="vault.json")         # auto-persisted to file

vault.save("greeting", "Hello, {{ name }}!", tags=["production"])
vault.save("greeting", "Hi there, {{ name }}! How are you?")

print(vault.render("greeting", name="Alice"))  # latest version
print(vault.history("greeting"))               # all versions
```

## API

| Method | Description |
|---|---|
| `save(key, content, tags)` | Save a new version, returns `TemplateVersion` |
| `get(key, version=None)` | Retrieve a version (latest if omitted) |
| `render(key, version=None, **kwargs)` | Render via Jinja2; raises `RenderError` on failure |
| `history(key)` | List all versions oldest-first |
| `delete(key)` | Remove all versions |
| `delete_version(key, version)` | Remove one specific version |
| `rename(old_key, new_key)` | Rename a template |
| `search(query)` | Content search across all versions |
| `search_by_tag(tag)` | Tag-based search |
| `list_all_tags()` | Sorted list of all tags in the vault |
| `keys()` | All stored template keys |
| `save_to_file(path)` | Serialise vault to JSON |
| `load_from_file(path)` | Replace contents from JSON file |

## GUI

```bash
promptvault-gui
```

Launches a Tkinter desktop application with a template browser, version history, Jinja2 render panel, tag filtering, and file open/save support.

## Template syntax

Templates use [Jinja2](https://jinja.palletsprojects.com/) syntax:

```
Summarise the following text in {{ n }} bullet points:

{{ text }}
```

## License

MIT
