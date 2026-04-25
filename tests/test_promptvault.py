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

def test_history():
    v = Promptvault()
    v.save("t", "v1"); v.save("t", "v2")
    h = v.history("t")
    assert len(h) == 2
    assert h[0].version == 1

def test_get_specific_version():
    v = Promptvault()
    v.save("t", "v1"); v.save("t", "v2")
    assert v.get("t", 1).content == "v1"

def test_missing_key():
    v = Promptvault()
    assert v.get("nope") is None
    assert v.history("nope") == []
