# promptvault

Versioned prompt template storage with history tracking, Jinja2 rendering, tag-based search, and optional JSON persistence.

## Installation

```bash
pip install promptvault
```

## Quick start

```python
from promptvault import Promptvault

vault = Promptvault()                           # in-memory
# vault = Promptvault(path="vault.json")        # auto-persist to disk

vault.save("greeting", "Hello, {{ name }}!")
vault.save("greeting", "Hi there, {{ name }}!  How are you?",
           tags=["friendly", "v2"])

# Retrieve and render
tv = vault.get("greeting")                      # latest version
print(tv.render(name="Alice"))                  # Hi there, Alice!  How are you?

# Or render directly
print(vault.render("greeting", name="Bob"))

# Browse history
for tv in vault.history("greeting"):
    print(tv.version, tv.saved_at, tv.tags)

# Search by content or tag
vault.search("{{ name }}")
vault.search_by_tag("friendly")
```

## GUI

Launch the desktop GUI (requires Tk, which ships with standard Python):

```bash
promptvault-gui
```

Or from Python:

```python
from promptvault.gui import launch_gui
launch_gui()
```

## Jinja2 templates

Templates use [Jinja2](https://jinja.palletsprojects.com/) syntax:

```
Hello, {{ name }}!
{% for item in items %}• {{ item }}
{% endfor %}
{% if flag %}optional block{% endif %}
```

## Persistence

```python
vault = Promptvault(path="my_vault.json")
# All save/delete/rename calls are written back automatically.

# Manual export / import:
vault.export_json("backup.json")
vault2 = Promptvault.from_json("backup.json")
```

## Running tests

```bash
pip install -e ".[dev]"
pytest
```
