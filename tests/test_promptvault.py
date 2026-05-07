"""Tests for promptvault."""
import json
import os
import tempfile

import pytest

from promptvault import Promptvault, TemplateVersion


# ---------------------------------------------------------------------------
# Core save / get
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


def test_get_missing_key_returns_none():
    v = Promptvault()
    assert v.get("nope") is None


def test_save_empty_key_raises():
    v = Promptvault()
    with pytest.raises(ValueError):
        v.save("", "content")


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def test_history():
    v = Promptvault()
    v.save("t", "v1")
    v.save("t", "v2")
    h = v.history("t")
    assert len(h) == 2
    assert h[0].version == 1


def test_history_missing_key():
    v = Promptvault()
    assert v.history("nope") == []


# ---------------------------------------------------------------------------
# Jinja2 rendering
# ---------------------------------------------------------------------------

def test_render():
    v = Promptvault()
    v.save("greet", "Hello, {{ name }}!")
    assert v.render("greet", name="Alice") == "Hello, Alice!"


def test_render_missing_key():
    v = Promptvault()
    assert v.render("nonexistent") is None


def test_template_version_render_directly():
    tv = TemplateVersion(content="{{ a }} + {{ b }}", saved_at="now", version=1)
    assert tv.render(a="1", b="2") == "1 + 2"


def test_render_jinja2_if_block():
    v = Promptvault()
    v.save("cond", "{% if flag %}yes{% else %}no{% endif %}")
    assert v.render("cond", flag=True) == "yes"
    assert v.render("cond", flag=False) == "no"


# ---------------------------------------------------------------------------
# Deletion
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
    assert v.delete_version("t", 1) is True
    assert "t" not in v


def test_delete_version_nonexistent_returns_false():
    v = Promptvault()
    v.save("t", "content")
    assert v.delete_version("t", 99) is False


# ---------------------------------------------------------------------------
# Rename
# ---------------------------------------------------------------------------

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

def test_tags():
    v = Promptvault()
    tv = v.save("t", "content", tags=["production", "v2"])
    assert "production" in tv.tags


def test_tags_default_empty():
    v = Promptvault()
    tv = v.save("t", "content")
    assert tv.tags == []


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


def test_search_case_insensitive():
    v = Promptvault()
    v.save("t", "Hello World")
    assert "t" in v.search("hello")
    assert "t" not in v.search("hello", case_sensitive=True)


# ---------------------------------------------------------------------------
# Tag search
# ---------------------------------------------------------------------------

def test_search_by_tags():
    v = Promptvault()
    v.save("a", "content", tags=["prod", "llm"])
    v.save("b", "content", tags=["dev"])
    results = v.search_by_tags(["prod"])
    assert "a" in results
    assert "b" not in results


def test_search_by_tags_multiple():
    v = Promptvault()
    v.save("a", "content", tags=["prod", "llm"])
    v.save("b", "content", tags=["prod"])
    results = v.search_by_tags(["prod", "llm"])
    assert "a" in results
    assert "b" not in results


def test_list_all_tags():
    v = Promptvault()
    v.save("a", "c", tags=["x", "y"])
    v.save("b", "c", tags=["y", "z"])
    assert v.list_all_tags() == ["x", "y", "z"]


# ---------------------------------------------------------------------------
# Python protocol
# ---------------------------------------------------------------------------

def test_len():
    v = Promptvault()
    assert len(v) == 0
    v.save("a", "c")
    assert len(v) == 1
    v.save("b", "c")
    assert len(v) == 2
    v.delete("a")
    assert len(v) == 1


def test_contains():
    v = Promptvault()
    v.save("a", "c")
    assert "a" in v
    assert "b" not in v


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def test_persistence_roundtrip():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        v1 = Promptvault(storage_path=path)
        v1.save("greet", "Hello, {{ name }}!", tags=["test"])
        v1.save("greet", "Hi {{ name }}!")

        v2 = Promptvault(storage_path=path)
        assert len(v2.history("greet")) == 2
        assert v2.get("greet").content == "Hi {{ name }}!"
        assert v2.get("greet", 1).tags == ["test"]
    finally:
        os.unlink(path)


def test_in_memory_does_not_create_file():
    v = Promptvault()
    v.save("t", "content")
    assert v._path is None


# ---------------------------------------------------------------------------
# Export / import
# ---------------------------------------------------------------------------

def test_export_import():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        export_path = f.name
    try:
        v1 = Promptvault()
        v1.save("a", "alpha", tags=["x"])
        v1.save("b", "beta")
        v1.export(export_path)

        v2 = Promptvault()
        n = v2.import_from(export_path)
        assert n == 2
        assert v2.get("a").content == "alpha"
        assert v2.get("b").content == "beta"
    finally:
        os.unlink(export_path)


def test_import_no_overwrite():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        export_path = f.name
    try:
        src = Promptvault()
        src.save("a", "original")
        src.export(export_path)

        dst = Promptvault()
        dst.save("a", "local")
        n = dst.import_from(export_path, overwrite=False)
        assert n == 0
        assert dst.get("a").content == "local"
    finally:
        os.unlink(export_path)


def test_import_overwrite():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        export_path = f.name
    try:
        src = Promptvault()
        src.save("a", "from_export")
        src.export(export_path)

        dst = Promptvault()
        dst.save("a", "local")
        n = dst.import_from(export_path, overwrite=True)
        assert n == 1
        assert dst.get("a").content == "from_export"
    finally:
        os.unlink(export_path)
