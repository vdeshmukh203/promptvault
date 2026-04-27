# promptvault

Versioned prompt template storage with history tracking, Jinja2 rendering,
tag-based search, JSON persistence, and a desktop GUI.

## Installation

```bash
pip install promptvault
```

## Quick start

```python
from promptvault import Promptvault

vault = Promptvault()

# Save versions with optional tags
vault.save("greeting", "Hello, {{ name }}!", tags=["v1"])
vault.save("greeting", "Hi there, {{ name }}! How are you?", tags=["v2"])

# Retrieve
print(vault.get("greeting"))          # latest TemplateVersion
print(vault.get("greeting", 1))       # specific version

# Render with Jinja2
print(vault.render("greeting", name="Alice"))

# History
for v in vault.history("greeting"):
    print(v.version, v.saved_at, v.content)
```

## API reference

| Method | Description |
|---|---|
| `save(key, content, tags=None)` | Save a new version; returns `TemplateVersion` |
| `get(key, version=None)` | Get latest (or specific) version |
| `render(key, version=None, **kwargs)` | Render template with Jinja2 |
| `history(key)` | All versions, oldest first |
| `delete(key)` | Remove all versions of a template |
| `delete_version(key, version)` | Remove one specific version |
| `rename(old_key, new_key)` | Rename a template key |
| `search(query, case_sensitive=False)` | Full-text search across content |
| `search_by_tag(tag)` | Find versions carrying a specific tag |
| `keys()` | List all template keys |
| `export(path)` | Serialise vault to a JSON file |
| `load(path)` | Merge templates from a JSON file |
| `Promptvault.from_file(path)` | Create a vault pre-loaded from a file |

`"key" in vault` and `len(vault)` are also supported.

## Jinja2 templating

Templates use [Jinja2](https://jinja.palletsprojects.com/) syntax:

```python
vault.save("prompt", "Summarise this text in {{ lang }}:\n\n{{ text }}")
vault.render("prompt", lang="French", text="...")
```

Conditionals, loops, and filters all work as expected.

## Persistence

```python
vault.export("my_prompts.json")          # save to disk
vault2 = Promptvault.from_file("my_prompts.json")  # restore
```

## GUI

Launch the desktop GUI with:

```bash
promptvault          # via installed script
# or
python -m promptvault
```

The GUI provides:
- **Template list** – browse and search all stored keys
- **Editor tab** – write/edit template content and tags, save a new version
- **History tab** – view all versions, preview content, load into editor, or delete a version
- **Render tab** – supply variables and preview the rendered output
- **Export / Import** – persist and restore the vault via JSON files
