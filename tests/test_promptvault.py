"""Tests for promptvault."""
import json
import tempfile
from pathlib import Path

import pytest

from promptvault import Promptvault


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


def test_render():
    v = Promptvault()
    v.save("greet", "Hello, {{ name }}!")
    result = v.render("greet", name="Alice")
    assert result == "Hello, Alice!"


def test_render_missing_key():
    v = Promptvault()
    assert v.render("nonexistent") is None


def test_render_strict_undefined():
    """Rendering with a missing variable should raise UndefinedError."""
    import jinja2
    v = Promptvault()
    v.save("t", "Hello, {{ name }}!")
    with pytest.raises(jinja2.UndefinedError):
        v.render("t")


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


def test_delete_version_removes_empty_key():
    v = Promptvault()
    v.save("t", "only version")
    assert v.delete_version("t", 1) is True
    assert v.get("t") is None
    assert "t" not in v.keys()


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


def test_rename_empty_new_key_raises():
    v = Promptvault()
    v.save("a", "content")
    with pytest.raises(ValueError):
        v.rename("a", "")


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


def test_search_by_tags():
    v = Promptvault()
    v.save("a", "content", tags=["prod", "v2"])
    v.save("b", "content", tags=["prod", "v1"])
    v.save("c", "content", tags=["dev"])
    results = v.search_by_tags("prod")
    assert "a" in results
    assert "b" in results
    assert "c" not in results


def test_search_by_tags_all_required():
    v = Promptvault()
    v.save("a", "content", tags=["prod", "v2"])
    v.save("b", "content", tags=["prod"])
    results = v.search_by_tags("prod", "v2")
    assert "a" in results
    assert "b" not in results


def test_tags():
    v = Promptvault()
    tv = v.save("t", "content", tags=["production", "v2"])
    assert "production" in tv.tags


def test_missing_key():
    v = Promptvault()
    assert v.get("nope") is None
    assert v.history("nope") == []


def test_save_empty_key_raises():
    v = Promptvault()
    with pytest.raises(ValueError):
        v.save("", "content")


def test_repr():
    v = Promptvault()
    tv = v.save("t", "content", tags=["x"])
    r = repr(tv)
    assert "TemplateVersion" in r
    assert "version=1" in r


def test_export_import_json():
    v = Promptvault()
    v.save("greet", "Hello, {{ name }}!", tags=["prod"])
    v.save("greet", "Hi, {{ name }}!")
    exported = v.export_json()
    data = json.loads(exported)
    assert "greet" in data
    assert len(data["greet"]) == 2

    v2 = Promptvault.import_json(exported)
    assert v2.get("greet", 1).content == "Hello, {{ name }}!"
    assert v2.get("greet", 2).content == "Hi, {{ name }}!"
    assert v2.get("greet", 1).tags == ["prod"]


def test_persistence(tmp_path):
    path = tmp_path / "vault.json"
    v = Promptvault(path=path)
    v.save("t", "Hello, {{ name }}!", tags=["demo"])
    v.save("t", "Hi, {{ name }}!")

    # Re-open from disk
    v2 = Promptvault(path=path)
    assert v2.get("t", 1).content == "Hello, {{ name }}!"
    assert v2.get("t", 2).content == "Hi, {{ name }}!"
    assert v2.get("t", 1).tags == ["demo"]
    assert len(v2.history("t")) == 2


def test_persistence_atomic_write(tmp_path):
    """save_to_disk must not leave a .tmp file behind."""
    path = tmp_path / "vault.json"
    v = Promptvault(path=path)
    v.save("t", "content")
    assert not (tmp_path / "vault.tmp").exists()
    assert path.exists()
