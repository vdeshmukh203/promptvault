"""Tests for promptvault."""
import pytest
from promptvault import Promptvault
from promptvault.vault import TemplateNotFoundError, RenderError


# ------------------------------------------------------------------ #
# Basic CRUD
# ------------------------------------------------------------------ #

def test_save_and_get():
    v = Promptvault()
    tv = v.save("t", "hello {{ name }}")
    assert tv.version == 1
    assert tv.content == "hello {{ name }}"


def test_get_latest():
    v = Promptvault()
    v.save("t", "v1")
    v.save("t", "v2")
    assert v.get("t").content == "v2"


def test_get_specific_version():
    v = Promptvault()
    v.save("t", "v1")
    v.save("t", "v2")
    assert v.get("t", 1).content == "v1"


def test_get_missing_returns_none():
    v = Promptvault()
    assert v.get("nope") is None


def test_history():
    v = Promptvault()
    v.save("t", "v1")
    v.save("t", "v2")
    h = v.history("t")
    assert len(h) == 2
    assert h[0].version == 1


def test_history_missing_returns_empty():
    v = Promptvault()
    assert v.history("nope") == []


def test_keys():
    v = Promptvault()
    v.save("a", "x")
    v.save("b", "y")
    assert set(v.keys()) == {"a", "b"}


# ------------------------------------------------------------------ #
# Render (Jinja2)
# ------------------------------------------------------------------ #

def test_render_simple():
    v = Promptvault()
    v.save("greet", "Hello, {{ name }}!")
    assert v.render("greet", name="Alice") == "Hello, Alice!"


def test_render_specific_version():
    v = Promptvault()
    v.save("t", "v{{ n }}")
    v.save("t", "version {{ n }}")
    assert v.render("t", version=1, n=1) == "v1"


def test_render_jinja2_loop():
    v = Promptvault()
    v.save("loop", "{% for x in items %}{{ x }}{% endfor %}")
    assert v.render("loop", items=["a", "b", "c"]) == "abc"


def test_render_jinja2_conditional():
    v = Promptvault()
    v.save("cond", "{% if flag %}yes{% else %}no{% endif %}")
    assert v.render("cond", flag=True) == "yes"
    assert v.render("cond", flag=False) == "no"


def test_render_missing_template_raises():
    v = Promptvault()
    with pytest.raises(TemplateNotFoundError):
        v.render("nonexistent")


def test_render_missing_variable_raises():
    v = Promptvault()
    v.save("t", "{{ missing_var }}")
    with pytest.raises(RenderError):
        v.render("t")


def test_render_syntax_error_raises():
    v = Promptvault()
    v.save("bad", "{% for %}")
    with pytest.raises(RenderError):
        v.render("bad")


# ------------------------------------------------------------------ #
# Delete / Rename
# ------------------------------------------------------------------ #

def test_delete():
    v = Promptvault()
    v.save("t", "content")
    assert v.delete("t") is True
    assert v.get("t") is None
    assert v.delete("t") is False


def test_delete_version():
    v = Promptvault()
    v.save("t", "v1")
    v.save("t", "v2")
    assert v.delete_version("t", 1) is True
    assert len(v.history("t")) == 1


def test_delete_version_missing():
    v = Promptvault()
    assert v.delete_version("nope", 1) is False


def test_rename():
    v = Promptvault()
    v.save("old", "content")
    assert v.rename("old", "new") is True
    assert v.get("new").content == "content"
    assert v.get("old") is None


def test_rename_conflict():
    v = Promptvault()
    v.save("a", "c1")
    v.save("b", "c2")
    assert v.rename("a", "b") is False


def test_rename_missing():
    v = Promptvault()
    assert v.rename("nope", "other") is False


# ------------------------------------------------------------------ #
# Search
# ------------------------------------------------------------------ #

def test_search_content():
    v = Promptvault()
    v.save("greet", "Hello, {{ name }}!")
    v.save("bye", "Goodbye, {{ name }}!")
    results = v.search("{{ name }}")
    assert "greet" in results
    assert "bye" in results


def test_search_case_insensitive():
    v = Promptvault()
    v.save("t", "Hello World")
    assert "t" in v.search("hello world")
    assert "t" not in v.search("hello world", case_sensitive=True)


def test_search_by_tag():
    v = Promptvault()
    v.save("t1", "content1", tags=["prod"])
    v.save("t2", "content2", tags=["dev"])
    results = v.search_by_tag("prod")
    assert "t1" in results
    assert "t2" not in results


def test_search_by_tag_multiple_versions():
    v = Promptvault()
    v.save("t", "v1", tags=["draft"])
    v.save("t", "v2", tags=["prod"])
    results = v.search_by_tag("prod")
    assert "t" in results
    assert len(results["t"]) == 1
    assert results["t"][0].version == 2


# ------------------------------------------------------------------ #
# Tags
# ------------------------------------------------------------------ #

def test_tags_saved():
    v = Promptvault()
    tv = v.save("t", "content", tags=["production", "v2"])
    assert "production" in tv.tags
    assert "v2" in tv.tags


def test_tags_default_empty():
    v = Promptvault()
    tv = v.save("t", "content")
    assert tv.tags == []


# ------------------------------------------------------------------ #
# Persistence
# ------------------------------------------------------------------ #

def test_persistence_roundtrip(tmp_path):
    path = tmp_path / "vault.json"
    v1 = Promptvault(path=path)
    v1.save("greet", "Hello, {{ name }}!", tags=["test"])

    v2 = Promptvault(path=path)
    assert v2.get("greet").content == "Hello, {{ name }}!"
    assert "test" in v2.get("greet").tags


def test_persistence_multiple_versions(tmp_path):
    path = tmp_path / "vault.json"
    v1 = Promptvault(path=path)
    v1.save("t", "v1")
    v1.save("t", "v2")

    v2 = Promptvault(path=path)
    assert len(v2.history("t")) == 2


def test_export_import_json(tmp_path):
    path = tmp_path / "export.json"
    v1 = Promptvault()
    v1.save("t", "content", tags=["x"])
    v1.export_json(path)

    v2 = Promptvault.from_json(path)
    assert v2.get("t").content == "content"
    assert "x" in v2.get("t").tags


def test_save_to_disk_no_path_raises():
    v = Promptvault()
    with pytest.raises(Exception):
        v.save_to_disk()
