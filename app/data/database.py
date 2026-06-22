"""مدير الاتصال بقاعدة بيانات SQLite.

الطبقة الوحيدة التي تفتح الاتصال وتطبّق المخطط والترقيات والبذور. تُمرَّر
نسخة واحدة منها (Singleton عبر الحاوية) إلى كل المستودعات.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

from app.config import AppConfig
from app.data import migrations, schema


class Database:
    def __init__(self, path: Path | str):
        self._path = Path(path)
        self._conn: sqlite3.Connection | None = None

    # ── دورة الحياة ─────────────────────────────────────────────────────
    @property
    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("لم يتم تهيئة قاعدة البيانات بعد (initialize).")
        return self._conn

    def initialize(self) -> None:
        """فتح الاتصال وإنشاء المخطط/البذور أو تطبيق الترقيات حسب الحاجة."""
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")

        if not self._table_exists("users"):
            self._create_schema()
            # البذور تُستورد هنا لتفادي الاستيراد الدائري.
            from app.data.seed import seed_initial_data

            seed_initial_data(self)
            self._set_version(AppConfig.DB_SCHEMA_VERSION)
        else:
            current = self._get_version()
            if current < AppConfig.DB_SCHEMA_VERSION:
                migrations.run(self, current, AppConfig.DB_SCHEMA_VERSION)
                self._set_version(AppConfig.DB_SCHEMA_VERSION)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def backup_to(self, target_path: Path | str) -> None:
        """نسخة احتياطية آمنة على مستوى الاتصال (تتعامل مع المعاملات الجارية)."""
        dest = sqlite3.connect(str(target_path))
        try:
            self.connection.backup(dest)
        finally:
            dest.close()

    # ── مساعدات الاستعلام ───────────────────────────────────────────────
    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        return self.connection.execute(sql, params)

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        return self.connection.execute(sql, params).fetchall()

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        return self.connection.execute(sql, params).fetchone()

    def insert(self, sql: str, params: Sequence[Any] = ()) -> int:
        """تنفيذ INSERT داخل معاملة وإرجاع المعرّف الجديد."""
        with self.transaction():
            cur = self.connection.execute(sql, params)
            return int(cur.lastrowid)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """سياق معاملة: commit عند النجاح، rollback عند الخطأ."""
        conn = self.connection
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # ── داخلي ───────────────────────────────────────────────────────────
    def _create_schema(self) -> None:
        with self.transaction() as conn:
            for stmt in schema.CREATE_STATEMENTS:
                conn.execute(stmt)
            for stmt in schema.INDEX_STATEMENTS:
                conn.execute(stmt)

    def _table_exists(self, name: str) -> bool:
        row = self.query_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        )
        return row is not None

    def _get_version(self) -> int:
        row = self.connection.execute("PRAGMA user_version;").fetchone()
        return int(row[0]) if row else 0

    def _set_version(self, version: int) -> None:
        # PRAGMA لا يقبل المعاملات (placeholders) فيُدرج العدد مباشرة.
        self.connection.execute(f"PRAGMA user_version = {int(version)};")
        self.connection.commit()
