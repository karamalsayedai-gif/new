"""ترقيات مخطط قاعدة البيانات بين الإصدارات.

عند رفع ``AppConfig.DB_SCHEMA_VERSION`` أضف فرعًا جديدًا ينفّذ عبارات
ALTER/CREATE اللازمة. أساسي لتحديث المنتج لدى العملاء دون فقد بياناتهم.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.data.database import Database


def run(db: "Database", old_version: int, new_version: int) -> None:
    with db.transaction() as conn:
        # مثال للمستقبل:
        # if old_version < 2:
        #     conn.execute("ALTER TABLE customers ADD COLUMN email TEXT;")
        _ = (conn, old_version, new_version)
