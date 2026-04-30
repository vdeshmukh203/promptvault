"""Tests for promptvault."""
import pytest
from promptvault import Promptvault, TemplateVersion
from promptvault.vault import RenderError


# ------------------------------------------------------------------ core CRUD

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


def test_history():
    v = Promptvault()
    v.save("t", "v1")
    v.save("t", "v2")
    h = v.history("t")
    assert len(h) == 2
    assert h[0].version == 1


def test_missing_key():
    v = Promptvault()
    assert v.get("nope") is None
    assert v.history("nope") == []


# -------------------------------------------------------------------- render

def test_render():
    v = Promptvault()
    v.save("greet", "Hello, {{ name }}!")
    assert v.render("greet", name="Alice") == "Hello, Alice!"


def test_render_multiple_vars():
    v = Promptvault()
    v.save("t", "{{ greeting }}, {{ name }}!")
    assert v.render("t", greeting="Hi", name="Bob") == "Hi, Bob!"


def test_render_missing_key():
    v = Promptvault()
    assert v.render("nonexistent") is None


def test_render_syntax_error():
    v = Promptvault()
    v.save("bad", "{% if %}")
    with pytest.raises(RenderError):
        v.render("bad")


def test_render_undefined_variable():
    v = Promptvault()
    v.save("t", "Hello, {{ name }}!")
    with pytest.raises(RenderError):
        v.render("t")  # name not provided — StrictUndefined raises


def test_template_version_render_directly():
    tv = TemplateVersion(content="{{ x }} + {{ y }}", saved_at="2026-01-01T00:00:00+00:00", version=1)
    assert tv.render(x="1", y="2") == "1 + 2"


# ------------------------------------------------------------------- delete

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


def test_delete_version_nonexistent():
    v = Promptvault()
    v.save("t", "v1")
    assert v.delete_version("t", 99) is False
    assert v.delete_version("missing", 1) is False


# ------------------------------------------------------------------- rename

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


# -------------------------------------------------------------------- search

def test_search_content():
    v = Promptvault()
    v.save("greet", "Hello, {{ name }}!")
    v.save("bye", "Goodbye, {{ name }}!")
    v.save("other", "No variable here")
    results = v.search("{{ name }}")
    assert "greet" in results
    assert "bye" in results
    assert "other" not in results


def test_search_case_insensitive():
    v = Promptvault()
    v.save("t", "Hello World")
    assert "t" in v.search("hello world")
    assert "t" in v.search("HELLO WORLD")


def test_search_case_sensitive():
    v = Promptvault()
    v.save("t", "Hello World")
    assert "t" not in v.search("hello world", case_sensitive=True)
    assert "t" in v.search("Hello World", case_sensitive=True)


# ----------------------------------------------------------------- tag search

def test_tags_stored():
    v = Promptvault()
    tv = v.save("t", "content", tags=["production", "v2"])
    assert "production" in tv.tags
    assert "v2" in tv.tags


def test_tags_default_empty():
    tv = TemplateVersion(content="x", saved_at="2026-01-01T00:00:00+00:00", version=1)
    assert tv.tags == []


def test_tags_no_shared_default():
    """Mutable default must not be shared between instances."""
    tv1 = TemplateVersion(content="a", saved_at="2026-01-01T00:00:00+00:00", version=1)
    tv2 = TemplateVersion(content="b", saved_at="2026-01-01T00:00:00+00:00", version=2)
    tv1.tags.append("tag")
    assert tv2.tags == []


def test_search_by_tag():
    v = Promptvault()
    v.save("a", "content", tags=["prod"])
    v.save("b", "content", tags=["dev"])
    v.save("c", "content", tags=["prod", "dev"])
    results = v.search_by_tag("prod")
    assert "a" in results
    assert "c" in results
    assert "b" not in results


def test_search_by_tag_no_match():
    v = Promptvault()
    v.save("t", "content", tags=["dev"])
    assert v.search_by_tag("prod") == {}


# ---------------------------------------------------------------- persistence

def test_persist_roundtrip(tmp_path):
    v = Promptvault()
    v.save("greet", "Hello, {{ name }}!", tags=["test"])
    v.save("greet", "Hi, {{ name }}!")
    path = tmp_path / "vault.json"
    v.save_to_file(path)

    v2 = Promptvault.load_from_file(path)
    assert len(v2.history("greet")) == 2
    tv = v2.get("greet")
    assert tv.content == "Hi, {{ name }}!"
    assert v2.get("greet", 1).tags == ["test"]
    assert tv.render(name="World") == "Hi, World!"


def test_persist_empty_vault(tmp_path):
    v = Promptvault()
    path = tmp_path / "empty.json"
    v.save_to_file(path)
    v2 = Promptvault.load_from_file(path)
    assert v2.keys() == []


def test_persist_file_is_json(tmp_path):
    import json
    v = Promptvault()
    v.save("t", "content", tags=["a"])
    path = tmp_path / "vault.json"
    v.save_to_file(path)
    data = json.loads(path.read_text())
    assert "t" in data
    assert data["t"][0]["content"] == "content"
    assert data["t"][0]["tags"] == ["a"]


# -------------------------------------------------------------------- keys()

def test_keys():
    v = Promptvault()
    v.save("b", "x")
    v.save("a", "y")
    assert set(v.keys()) == {"a", "b"}
