"""F12 - Tests documents_service avec FakeSession + LocalStorage tmp."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest

from app.projets import documents_service as ds
from app.storage.local import LocalStorage


@dataclass
class DocFakeRow:
    id: Any = None
    projet_id: Any = None
    account_id: Any = None
    name: str = "n"
    original_filename: str = "f.pdf"
    mime_type: str = "application/pdf"
    size_bytes: int = 100
    type: str = "faisabilite"
    storage_path: str = "x"
    uploaded_by: Any = None
    created_at: datetime | None = None


class FakeResult:
    def __init__(self, *, first_val=None, all_val=None, scalar_val=None):
        self._first = first_val
        self._all = all_val or []
        self._scalar = scalar_val
    def first(self):
        return self._first
    def all(self):
        return self._all
    def scalar_one(self):
        return self._scalar


class FakeSession:
    def __init__(self):
        self.responses: list[FakeResult] = []
        class _SP:
            def commit(self_): pass
            def rollback(self_): pass
        self._sp = _SP()
    def queue(self, *r):
        self.responses.extend(r)
    def execute(self, sql, params=None):
        s = str(sql).upper()
        if "AUDIT_LOG" in s and "INSERT" in s:
            return FakeResult()
        if self.responses:
            return self.responses.pop(0)
        return FakeResult()
    def flush(self):
        pass
    def begin_nested(self):
        return self._sp


def test_upload_document_ok(tmp_path):
    storage = LocalStorage(tmp_path)
    aid, pid, uid = uuid4(), uuid4(), uuid4()
    db = FakeSession()
    new_doc = DocFakeRow(id=uuid4(), projet_id=pid, account_id=aid, name="Doc")
    db.queue(
        FakeResult(first_val=(1,)),     # _projet_exists_for_account
        FakeResult(scalar_val=0),       # _count_docs
        FakeResult(),                   # INSERT document_projet
        FakeResult(first_val=new_doc),  # SELECT after insert
    )
    data = b"hello pdf bytes"
    out = ds.upload_document(
        db, storage,
        projet_id=pid, account_id=aid, user_id=uid,
        name="My doc", original_filename="f.pdf",
        mime_type="application/pdf", size_bytes=len(data),
        doc_type="faisabilite", data=data,
    )
    assert out.name == "Doc"


def test_upload_projet_not_found(tmp_path):
    storage = LocalStorage(tmp_path)
    db = FakeSession()
    db.queue(FakeResult(first_val=None))
    with pytest.raises(ds.ProjetNotFound):
        ds.upload_document(
            db, storage,
            projet_id=uuid4(), account_id=uuid4(), user_id=uuid4(),
            name="x", original_filename="f.pdf",
            mime_type="application/pdf", size_bytes=4,
            doc_type="faisabilite", data=b"abcd",
        )


def test_upload_size_mismatch(tmp_path):
    storage = LocalStorage(tmp_path)
    db = FakeSession()
    db.queue(FakeResult(first_val=(1,)))
    with pytest.raises(ds.ValidationError) as exc:
        ds.upload_document(
            db, storage,
            projet_id=uuid4(), account_id=uuid4(), user_id=uuid4(),
            name="x", original_filename="f.pdf",
            mime_type="application/pdf", size_bytes=99,
            doc_type="faisabilite", data=b"abcd",
        )
    assert exc.value.code == "size_mismatch"


def test_upload_too_many_docs(tmp_path):
    storage = LocalStorage(tmp_path)
    db = FakeSession()
    db.queue(
        FakeResult(first_val=(1,)),
        FakeResult(scalar_val=50),
    )
    with pytest.raises(ds.TooManyDocuments):
        ds.upload_document(
            db, storage,
            projet_id=uuid4(), account_id=uuid4(), user_id=uuid4(),
            name="x", original_filename="f.pdf",
            mime_type="application/pdf", size_bytes=4,
            doc_type="faisabilite", data=b"abcd",
        )


def test_upload_invalid_mime(tmp_path):
    storage = LocalStorage(tmp_path)
    db = FakeSession()
    db.queue(FakeResult(first_val=(1,)))
    with pytest.raises(ds.ValidationError) as exc:
        ds.upload_document(
            db, storage,
            projet_id=uuid4(), account_id=uuid4(), user_id=uuid4(),
            name="x", original_filename="f.exe",
            mime_type="application/x-evil", size_bytes=4,
            doc_type="faisabilite", data=b"abcd",
        )
    assert exc.value.code == "mime_not_allowed"


def test_upload_invalid_size(tmp_path):
    storage = LocalStorage(tmp_path)
    db = FakeSession()
    db.queue(FakeResult(first_val=(1,)))
    with pytest.raises(ds.ValidationError) as exc:
        ds.upload_document(
            db, storage,
            projet_id=uuid4(), account_id=uuid4(), user_id=uuid4(),
            name="x", original_filename="f.pdf",
            mime_type="application/pdf",
            size_bytes=26214401,  # > 25MB
            doc_type="faisabilite",
            data=b"x" * 26214401,
        )
    assert exc.value.code == "size_too_large"


def test_list_documents(tmp_path):
    db = FakeSession()
    pid = uuid4()
    aid = uuid4()
    rows = [DocFakeRow(id=uuid4(), projet_id=pid, account_id=aid)]
    db.queue(
        FakeResult(first_val=(1,)),  # _projet_exists
        FakeResult(all_val=rows),
    )
    out = ds.list_documents(db, projet_id=pid, account_id=aid)
    assert len(out) == 1


def test_list_documents_projet_not_found():
    db = FakeSession()
    db.queue(FakeResult(first_val=None))
    with pytest.raises(ds.ProjetNotFound):
        ds.list_documents(db, projet_id=uuid4(), account_id=uuid4())


def test_get_document_not_found():
    db = FakeSession()
    db.queue(FakeResult(first_val=None))
    with pytest.raises(ds.DocumentNotFound):
        ds.get_document(db, doc_id=uuid4(), projet_id=uuid4(), account_id=uuid4())


def test_read_document(tmp_path):
    storage = LocalStorage(tmp_path)
    storage.save("doc.pdf", b"content")
    aid, pid, did = uuid4(), uuid4(), uuid4()
    row = DocFakeRow(id=did, projet_id=pid, account_id=aid, storage_path="doc.pdf")
    db = FakeSession()
    db.queue(FakeResult(first_val=row))
    doc, data = ds.read_document(db, storage, doc_id=did, projet_id=pid, account_id=aid)
    assert data == b"content"


def test_delete_document(tmp_path):
    storage = LocalStorage(tmp_path)
    storage.save("doc.pdf", b"x")
    aid, pid, did = uuid4(), uuid4(), uuid4()
    row = DocFakeRow(id=did, projet_id=pid, account_id=aid, storage_path="doc.pdf")
    db = FakeSession()
    db.queue(
        FakeResult(first_val=row),  # get_document
        FakeResult(),               # UPDATE deleted_at
    )
    ds.delete_document(
        db, storage,
        doc_id=did, projet_id=pid, account_id=aid, user_id=uuid4(),
    )
    assert not storage.exists("doc.pdf")
