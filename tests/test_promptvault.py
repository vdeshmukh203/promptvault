"""Tests for promptvault."""
import json
import pytest
from promptvault import Promptvault
from promptvault.vault import RenderError


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Rendering (Jinja2)
# ---------------------------------------------------------------------------

def test_render():
    v = Promptvault()
    v.save("greet", "Hello, {{ name }}!")
    assert v.render("greet", name="Alice") == "Hello, Alice!"


def test_render_missing_key():
    v = Promptvault()
    assert v.render("nonexistent") is None


def test_render_missing_variable_raises():
    v = Promptvault()
    v.save("t", "Hello, {{ name }}!")
    with pytest.raises(RenderError):
        v.render("t")  # 'name' not supplied → UndefinedError → RenderError


def test_render_specific_version():
    v = Promptvault()
    v.save("t", "v1: {{ x }}")
    v.save("t", "v2: {{ x }}")
    assert v.render("t", version=1, x="hi") == "v1: hi"


def test_template_version_render_directly():
    v = Promptvault()
    tv = v.save("t", "{{ a }} + {{ b }}")
    assert tv.render(a="1", b="2") == "1 + 2"


# ---------------------------------------------------------------------------
# Delete / rename
# ---------------------------------------------------------------------------

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


def test_delete_version_last_removes_key():
    v = Promptvault()
    v.save("t", "only")
    v.delete_version("t", 1)
    assert v.get("t") is None


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


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def test_tags_saved():
    v = Promptvault()
    tv = v.save("t", "content", tags=["production", "v2"])
    assert "production" in tv.tags


def test_tags_default_empty():
    v = Promptvault()
    tv = v.save("t", "content")
    assert tv.tags == []


def test_search_by_tag():
    v = Promptvault()
    v.save("a", "hello", tags=["greeting"])
    v.save("b", "bye", tags=["farewell"])
    v.save("a", "hi", tags=["greeting", "short"])
    results = v.search_by_tag("greeting")
    assert "a" in results
    assert "b" not in results
    assert len(results["a"]) == 2


def test_search_by_tag_case_insensitive():
    v = Promptvault()
    v.save("t", "x", tags=["GPT"])
    assert "t" in v.search_by_tag("gpt")


def test_list_all_tags():
    v = Promptvault()
    v.save("a", "x", tags=["foo", "bar"])
    v.save("b", "y", tags=["baz", "foo"])
    tags = v.list_all_tags()
    assert tags == ["bar", "baz", "foo"]


# ---------------------------------------------------------------------------
# Content search
# ---------------------------------------------------------------------------

def test_search():
    v = Promptvault()
    v.save("greet", "Hello, {{ name }}!")
    v.save("bye", "Goodbye, {{ name }}!")
    results = v.search("{{ name }}")
    assert "greet" in results
    assert "bye" in results


def test_search_case_sensitive():
    v = Promptvault()
    v.save("t", "Hello World")
    assert not v.search("hello", case_sensitive=True)
    assert "t" in v.search("Hello", case_sensitive=True)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def test_save_load_roundtrip(tmp_path):
    path = tmp_path / "vault.json"
    v = Promptvault()
    v.save("greet", "Hello, {{ name }}!", tags=["test"])
    v.save_to_file(path)

    v2 = Promptvault()
    v2.load_from_file(path)
    assert v2.get("greet").content == "Hello, {{ name }}!"
    assert "test" in v2.get("greet").tags


def test_auto_persist_on_save(tmp_path):
    path = tmp_path / "vault.json"
    v = Promptvault(path=path)
    v.save("t", "hello")
    assert path.exists()

    v2 = Promptvault(path=path)
    assert v2.get("t").content == "hello"


def test_auto_persist_on_delete(tmp_path):
    path = tmp_path / "vault.json"
    v = Promptvault(path=path)
    v.save("t", "hello")
    v.delete("t")

    v2 = Promptvault(path=path)
    assert v2.get("t") is None


def test_json_file_format(tmp_path):
    path = tmp_path / "vault.json"
    v = Promptvault()
    v.save("k", "content", tags=["a"])
    v.save_to_file(path)
    data = json.loads(path.read_text())
    assert "k" in data
    assert data["k"][0]["content"] == "content"
    assert data["k"][0]["tags"] == ["a"]
