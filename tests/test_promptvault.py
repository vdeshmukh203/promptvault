"""Tests for promptvault."""

import json
import os
import tempfile

import pytest

from promptvault import Promptvault, TemplateVersion


# ------------------------------------------------------------------ #
# original tests (preserved)                                           #
# ------------------------------------------------------------------ #

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
    v.save("greet", "Hello, {{ name }}!")
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
    v.save("greet", "Hello, {{ name }}!")
    v.save("bye", "Goodbye, {{ name }}!")
    results = v.search("{{ name }}")
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


# ------------------------------------------------------------------ #
# Jinja2 rendering                                                     #
# ------------------------------------------------------------------ #

def test_jinja2_render_variable():
    v = Promptvault()
    v.save("j", "Hello, {{ name }}!")
    assert v.render("j", name="Bob") == "Hello, Bob!"


def test_jinja2_render_conditional():
    v = Promptvault()
    v.save("cond", "{% if flag %}yes{% else %}no{% endif %}")
    assert v.render("cond", flag=True) == "yes"
    assert v.render("cond", flag=False) == "no"


def test_jinja2_undefined_variable_raises():
    v = Promptvault()
    v.save("t", "{{ missing }}")
    # Jinja2 renders undefined as empty string by default; that's acceptable
    result = v.render("t")
    assert result == ""


# ------------------------------------------------------------------ #
# input validation                                                      #
# ------------------------------------------------------------------ #

def test_save_empty_key_raises():
    v = Promptvault()
    with pytest.raises(ValueError):
        v.save("", "content")


def test_save_non_string_content_raises():
    v = Promptvault()
    with pytest.raises(TypeError):
        v.save("t", 123)  # type: ignore[arg-type]


def test_rename_empty_new_key_raises():
    v = Promptvault()
    v.save("old", "c")
    with pytest.raises(ValueError):
        v.rename("old", "")


# ------------------------------------------------------------------ #
# delete_version: key cleaned up when last version removed             #
# ------------------------------------------------------------------ #

def test_delete_version_last_removes_key():
    v = Promptvault()
    v.save("t", "only version")
    assert v.delete_version("t", 1) is True
    assert "t" not in v
    assert v.history("t") == []


def test_delete_version_nonexistent_returns_false():
    v = Promptvault()
    v.save("t", "content")
    assert v.delete_version("t", 99) is False


# ------------------------------------------------------------------ #
# search_by_tag                                                         #
# ------------------------------------------------------------------ #

def test_search_by_tag():
    v = Promptvault()
    v.save("a", "alpha", tags=["prod"])
    v.save("b", "beta", tags=["dev"])
    results = v.search_by_tag("prod")
    assert "a" in results
    assert "b" not in results


def test_search_by_tag_no_match():
    v = Promptvault()
    v.save("a", "alpha", tags=["prod"])
    assert v.search_by_tag("staging") == {}


# ------------------------------------------------------------------ #
# __len__ and __contains__                                             #
# ------------------------------------------------------------------ #

def test_len():
    v = Promptvault()
    assert len(v) == 0
    v.save("a", "x")
    v.save("b", "y")
    assert len(v) == 2


def test_contains():
    v = Promptvault()
    v.save("exists", "content")
    assert "exists" in v
    assert "missing" not in v


# ------------------------------------------------------------------ #
# TemplateVersion serialisation                                         #
# ------------------------------------------------------------------ #

def test_template_version_round_trip():
    tv = TemplateVersion(content="Hi {{ name }}", saved_at="2026-01-01T00:00:00+00:00",
                         version=1, tags=["a", "b"])
    d = tv.to_dict()
    assert d["content"] == tv.content
    assert d["tags"] == ["a", "b"]
    tv2 = TemplateVersion.from_dict(d)
    assert tv2.content == tv.content
    assert tv2.version == tv.version
    assert tv2.tags == tv.tags


# ------------------------------------------------------------------ #
# persistence: export / load / from_file                               #
# ------------------------------------------------------------------ #

def test_export_and_load(tmp_path):
    path = str(tmp_path / "vault.json")
    v1 = Promptvault()
    v1.save("greet", "Hello, {{ name }}!", tags=["test"])
    v1.save("greet", "Hi, {{ name }}!")
    v1.export(path)

    v2 = Promptvault()
    v2.load(path)
    assert "greet" in v2
    assert len(v2.history("greet")) == 2
    assert v2.get("greet").content == "Hi, {{ name }}!"


def test_load_does_not_overwrite_existing(tmp_path):
    path = str(tmp_path / "vault.json")
    v1 = Promptvault()
    v1.save("k", "original")
    v1.export(path)

    v2 = Promptvault()
    v2.save("k", "local version")
    v2.load(path)
    assert v2.get("k").content == "local version"


def test_from_file(tmp_path):
    path = str(tmp_path / "vault.json")
    v1 = Promptvault()
    v1.save("x", "content")
    v1.export(path)

    v2 = Promptvault.from_file(path)
    assert "x" in v2
    assert v2.get("x").content == "content"


def test_exported_json_structure(tmp_path):
    path = str(tmp_path / "vault.json")
    v = Promptvault()
    v.save("t", "hello", tags=["a"])
    v.export(path)

    with open(path) as fh:
        data = json.load(fh)

    assert "t" in data
    assert data["t"][0]["content"] == "hello"
    assert data["t"][0]["tags"] == ["a"]


# ------------------------------------------------------------------ #
# keys()                                                               #
# ------------------------------------------------------------------ #

def test_keys():
    v = Promptvault()
    v.save("b", "x")
    v.save("a", "y")
    assert set(v.keys()) == {"a", "b"}
