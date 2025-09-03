import asyncio
import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite


class Database:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = asyncio.Lock()

    async def init(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS owners (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    added_at TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phrase TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    owner_user_id INTEGER,
                    owner_username TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def seed_owners(self, owner_ids: List[int]) -> None:
        if not owner_ids:
            return
        now = dt.datetime.utcnow().isoformat()
        async with self._lock:
            async with aiosqlite.connect(self._db_path) as db:
                for oid in owner_ids:
                    await db.execute(
                        "INSERT OR IGNORE INTO owners (user_id, username, added_at) VALUES (?, ?, ?)",
                        (int(oid), None, now),
                    )
                await db.commit()

    async def add_owner(self, user_id: int, username: Optional[str]) -> None:
        now = dt.datetime.utcnow().isoformat()
        async with self._lock:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO owners (user_id, username, added_at) VALUES (?, ?, ?)",
                    (int(user_id), username, now),
                )
                await db.commit()

    async def is_owner(self, user_id: int) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT 1 FROM owners WHERE user_id = ?", (int(user_id),)) as cur:
                row = await cur.fetchone()
                return row is not None

    async def add_mapping(
        self,
        phrase: str,
        file_id: str,
        owner_user_id: Optional[int],
        owner_username: Optional[str],
    ) -> int:
        now = dt.datetime.utcnow().isoformat()
        async with self._lock:
            async with aiosqlite.connect(self._db_path) as db:
                cur = await db.execute(
                    "INSERT INTO mappings (phrase, file_id, owner_user_id, owner_username, created_at) VALUES (?, ?, ?, ?, ?)",
                    (phrase, file_id, owner_user_id, owner_username, now),
                )
                await db.commit()
                return int(cur.lastrowid)

    async def list_mappings(self, limit: int = 50) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT id, phrase, file_id, owner_user_id, owner_username, created_at FROM mappings ORDER BY created_at DESC LIMIT ?",
                (int(limit),),
            ) as cur:
                rows = await cur.fetchall()
        result: List[Dict[str, Any]] = []
        for r in rows:
            result.append(
                {
                    "id": r[0],
                    "phrase": r[1],
                    "file_id": r[2],
                    "owner_user_id": r[3],
                    "owner_username": r[4],
                    "created_at": r[5],
                }
            )
        return result

    async def count_mappings(self) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT COUNT(1) FROM mappings") as cur:
                row = await cur.fetchone()
                return int(row[0]) if row and row[0] is not None else 0

    async def list_mappings_paginated(self, limit: int, offset: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                """
                SELECT id, phrase, file_id, owner_user_id, owner_username, created_at
                FROM mappings
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (int(limit), int(offset)),
            ) as cur:
                rows = await cur.fetchall()
        result: List[Dict[str, Any]] = []
        for r in rows:
            result.append(
                {
                    "id": r[0],
                    "phrase": r[1],
                    "file_id": r[2],
                    "owner_user_id": r[3],
                    "owner_username": r[4],
                    "created_at": r[5],
                }
            )
        return result

    @staticmethod
    def _is_subsequence(needle: str, haystack: str) -> bool:
        it = iter(haystack)
        return all(ch in it for ch in needle)

    @staticmethod
    def _score(query: str, phrase: str) -> int:
        q = query.lower().strip()
        p = phrase.lower().strip()
        if not q or not p:
            return 0
        if q == p:
            return 100
        if p.startswith(q):
            return 80
        if q in p:
            return 60
        if Database._is_subsequence(q, p):
            return 40
        return 0

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT id, phrase, file_id, owner_user_id, owner_username, created_at FROM mappings",
            ) as cur:
                rows = await cur.fetchall()
        candidates: List[Tuple[int, Dict[str, Any]]] = []
        for r in rows:
            item = {
                "id": r[0],
                "phrase": r[1],
                "file_id": r[2],
                "owner_user_id": r[3],
                "owner_username": r[4],
                "created_at": r[5],
            }
            score = self._score(query, item["phrase"])
            if score > 0:
                candidates.append((score, item))

        candidates.sort(key=lambda t: (t[0], t[1]["created_at"]), reverse=True)
        return [it for _, it in candidates[: int(limit)]]


