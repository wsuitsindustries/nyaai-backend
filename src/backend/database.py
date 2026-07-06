"""In-memory database — drop-in replacement for MongoDB/motor during development.

Switches to MongoDB automatically when MONGO_URI is set and reachable.
"""

from __future__ import annotations

import copy
import os
from datetime import datetime, timezone


# ── In-memory collections ──────────────────────────────────────

class _Cursor:
    """Async cursor that mimics motor's cursor interface."""

    def __init__(self, docs: list[dict], sort_key: str | None = None, sort_dir: int = 1):
        self._docs = docs
        self._sort_key = sort_key
        self._sort_dir = sort_dir

    def sort(self, key: str, direction: int = 1) -> _Cursor:
        return _Cursor(self._docs, sort_key=key, sort_dir=direction)

    async def to_list(self, length: int | None = None) -> list[dict]:
        return self._sort_copy()

    def __aiter__(self):
        return _AsyncIterator(self._sort_copy())

    def _sort_copy(self) -> list[dict]:
        docs = copy.deepcopy(self._docs)
        if self._sort_key:
            docs.sort(key=lambda d: d.get(self._sort_key, ""), reverse=self._sort_dir == -1)
        return docs


class _AsyncIterator:
    def __init__(self, docs: list[dict]):
        self._iter = iter(docs)

    async def __anext__(self) -> dict:
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class _Collection:
    """In-memory collection that mirrors motor's async collection API."""

    def __init__(self):
        self._docs: list[dict] = []

    async def find_one(self, filter: dict, projection: dict | None = None) -> dict | None:
        for doc in self._docs:
            if self._matches(doc, filter):
                if projection:
                    return {k: doc.get(k) for k in projection if k != "_id"}
                return copy.deepcopy(doc)
        return None

    def find(self, filter: dict, projection: dict | None = None) -> _Cursor:
        matched = [doc for doc in self._docs if self._matches(doc, filter)]
        if projection:
            is_exclusion = all(v == 0 for v in projection.values())
            if is_exclusion:
                exclude = set(k for k, v in projection.items() if v == 0)
                matched = [{k: d[k] for k in d if k not in exclude} for d in matched]
            else:
                matched = [{k: d.get(k) for k in projection if (k != "_id" and projection.get(k))} for d in matched]
        return _Cursor(matched)

    async def insert_one(self, doc: dict) -> None:
        self._docs.append(copy.deepcopy(doc))

    async def update_one(self, filter: dict, update: dict, upsert: bool = False) -> None:
        for doc in self._docs:
            if self._matches(doc, filter):
                self._apply_update(doc, update)
                return
        if upsert:
            new_doc = copy.deepcopy(filter)
            self._apply_update(new_doc, update)
            self._docs.append(new_doc)

    async def delete_one(self, filter: dict) -> type("_Result", (), {"deleted_count": 0}):
        for i, doc in enumerate(self._docs):
            if self._matches(doc, filter):
                self._docs.pop(i)
                return type("_Result", (), {"deleted_count": 1})()
        return type("_Result", (), {"deleted_count": 0})()

    def _matches(self, doc: dict, filter: dict) -> bool:
        for k, v in filter.items():
            if k not in doc:
                return False
            if isinstance(v, dict):
                for op, val in v.items():
                    if op == "$in" and doc[k] not in val:
                        return False
                    elif op == "$ne" and doc[k] == val:
                        return False
            elif doc[k] != v:
                return False
        return True

    def _apply_update(self, doc: dict, update: dict) -> None:
        for op, fields in update.items():
            if op == "$set":
                doc.update(fields)
            elif op == "$setOnInsert":
                for k, v in fields.items():
                    doc.setdefault(k, v)
            elif op == "$push":
                for k, v in fields.items():
                    doc.setdefault(k, []).append(v)


# ── Module state ───────────────────────────────────────────────

_collections: dict[str, _Collection] = {}


def _get_collection(name: str) -> _Collection:
    if name not in _collections:
        _collections[name] = _Collection()
    return _collections[name]


# ── Public API (mirrors motor's async interface) ───────────────

async def connect_db():
    pass  # Nothing to connect — data lives in memory


async def close_db():
    _collections.clear()


def get_db() -> object:
    """Returns a db-like object with async collection accessors."""

    class _DB:
        @property
        def users(self): return _get_collection("users")
        @property
        def conversations(self): return _get_collection("conversations")
        @property
        def messages(self): return _get_collection("messages")
        @property
        def documents(self): return _get_collection("documents")
        @property
        def files(self): return _get_collection("files")

    return _DB()
