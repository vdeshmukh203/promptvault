"""Tests for promptvault."""
import pytest
from promptvault import Promptvault


def test_save_and_get():
    v = Promptvault()
    tv = v.save("t", "hello {name}")
    assert tv.version == 1
    assert tv.content == "hello {name}"


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


def test_render():
    v = Promptvault()
    v.save("greet", "Hello, {name}!")
    result = v.render("greet", name="Alice")
    assert result == "Hello, Alice!"


def test_render_missing_key():
    v = Promptvault()
    assert v.render("nonexistent") is None


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


def test_search():
    v = Promptvault()
    v.save("greet", "Hello, {name}!")
    v.save("bye", "Goodbye, {name}!")
    results = v.search("{name}")
    assert "greet" in results
    assert "bye" in results


def test_tags():
    v = Promptvault()
    tv = v.save("t", "content", tags=["production", "v2"])
    assert "production" in tv.tags


def test_missing_key():
    v = Promptvault()
    assert v.get("nope") is None
    assert v.history("nope") == []
