"""F12 - Tests LocalStorage."""

from __future__ import annotations

import io

import pytest

from app.storage.local import LocalStorage


def test_save_and_read(tmp_path):
    s = LocalStorage(tmp_path)
    s.save("a/b/c.txt", b"hello")
    assert s.exists("a/b/c.txt")
    assert s.read("a/b/c.txt") == b"hello"


def test_save_with_binaryio(tmp_path):
    s = LocalStorage(tmp_path)
    s.save("file.bin", io.BytesIO(b"bytes-stream"))
    assert s.read("file.bin") == b"bytes-stream"


def test_delete(tmp_path):
    s = LocalStorage(tmp_path)
    s.save("x", b"y")
    assert s.exists("x")
    s.delete("x")
    assert not s.exists("x")


def test_delete_idempotent(tmp_path):
    s = LocalStorage(tmp_path)
    s.delete("nonexistent")  # should not raise


def test_path_traversal_rejected(tmp_path):
    s = LocalStorage(tmp_path)
    with pytest.raises(ValueError):
        s.save("../escape.txt", b"x")


def test_absolute_path_rejected(tmp_path):
    s = LocalStorage(tmp_path)
    with pytest.raises(ValueError):
        s.save("/abs.txt", b"x")
