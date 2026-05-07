# promptvault

Versioned prompt template storage with history tracking, Jinja2 rendering, tag-based search, and a web GUI.

## Install

```bash
pip install promptvault          # core library
pip install 'promptvault[gui]'   # + Streamlit GUI
```

## Quick start

```python
from promptvault import Promptvault

# In-memory vault (no persistence)
vault = Promptvault()

# Persist to a JSON file
vault = Promptvault(storage_path="prompts.json")

# Save versioned templates (Jinja2 syntax)
vault.save("greeting", "Hello, {{ name }}!", tags=["production"])
vault.save("greeting", "Hi {{ name }}! How are you?")

# Retrieve latest or a specific version
latest = vault.get("greeting")          # v2
v1     = vault.get("greeting", 1)       # v1

# Render with Jinja2
result = vault.render("greeting", name="Alice")
# → "Hi Alice! How are you?"

# Full version history (oldest first)
for tv in vault.history("greeting"):
    print(tv.version, tv.saved_at, tv.tags)

# Search by content or tags
vault.search("{{ name }}")              # content substring
vault.search_by_tags(["production"])    # tag filter

# All unique tags
vault.list_all_tags()

# Rename / delete
vault.rename("greeting", "greet")
vault.delete_version("greet", 1)
vault.delete("greet")

# Export / import
vault.export("backup.json")
vault.import_from("backup.json", overwrite=False)
```

## Web GUI

```bash
promptvault-gui
```

Opens a Streamlit app in your browser with tabs for creating and editing templates, browsing version history, rendering with live variable inputs, searching by content or tags, and importing/exporting.

## Template syntax

Templates use [Jinja2](https://jinja.palletsprojects.com/). Variables are written as `{{ variable }}`:

```
Summarize the following {{ language }} code in {{ style }} style:

{{ code }}
```

Render it:

```python
vault.render("summarize", language="Python", style="concise", code="def f(): ...")
```

Jinja2 control structures (`{% if %}`, `{% for %}`, filters, etc.) are fully supported.

## API reference

| Method | Description |
|--------|-------------|
| `save(key, content, tags)` | Save a new version; returns `TemplateVersion` |
| `get(key, version=None)` | Get latest or specific version |
| `render(key, version=None, **kwargs)` | Render with Jinja2 |
| `history(key)` | All versions, oldest first |
| `delete(key)` | Delete all versions |
| `delete_version(key, version)` | Delete one version |
| `rename(old_key, new_key)` | Rename a template |
| `search(query, case_sensitive)` | Content substring search |
| `search_by_tags(tags)` | Tag intersection search |
| `list_all_tags()` | All unique tags, sorted |
| `export(path)` | Write vault to JSON |
| `import_from(path, overwrite)` | Load vault from JSON |
| `keys()` | All template keys |
| `len(vault)` | Number of templates |
| `key in vault` | Membership test |
