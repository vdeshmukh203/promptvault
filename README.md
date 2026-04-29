# promptvault

Versioned prompt template storage with history tracking.  
Templates are rendered with [Jinja2](https://jinja.palletsprojects.com/), so
the full Jinja2 syntax (`{{ variable }}`, `{% if %}`, filters, …) is available.

## Installation

```bash
pip install promptvault
```

## Quick start

```python
from promptvault import Promptvault

vault = Promptvault()                          # in-memory
# vault = Promptvault("prompts.json")          # persisted to disk

vault.save("greeting", "Hello, {{ name }}!")
vault.save("greeting", "Hi there, {{ name }}! How are you?", tags=["friendly"])

# Get the latest version and render it
print(vault.render("greeting", name="Alice"))
# → Hi there, Alice! How are you?

# Pin a specific version
print(vault.render("greeting", version=1, name="Bob"))
# → Hello, Bob!

# Inspect history
for tv in vault.history("greeting"):
    print(tv)

# Search by content
results = vault.search("{{ name }}")

# Search by tag
results = vault.search_by_tags("friendly")
```

## Desktop GUI

```bash
promptvault-gui                # open a blank in-memory vault
promptvault-gui prompts.json   # open (or create) a persisted vault
```

The GUI provides:
- **Template list** with live text and tag filtering
- **Version history** panel — click any version to load it into the editor
- **Jinja2 editor** with tag labelling
- **Render panel** — supply `key=value` pairs and press **Render** (or `Ctrl+Enter`)
- **File menu** — new/open/save vault, export and import JSON

## API reference

| Method | Description |
|---|---|
| `save(key, content, tags=[])` | Save a new version; returns `TemplateVersion` |
| `get(key, version=None)` | Fetch a version (latest if `version` is `None`) |
| `render(key, version=None, **kwargs)` | Render with Jinja2; returns `None` if key missing |
| `history(key)` | All versions, oldest first |
| `delete(key)` | Remove all versions |
| `delete_version(key, version)` | Remove one version |
| `rename(old_key, new_key)` | Rename a template |
| `search(query, case_sensitive=False)` | Search version content |
| `search_by_tags(*tags)` | Versions that carry **all** listed tags |
| `keys()` | All stored template names |
| `export_json()` | Serialise vault to a JSON string |
| `Promptvault.import_json(data)` | Deserialise from a JSON string |
| `save_to_disk()` | Explicitly flush to the configured JSON file |
