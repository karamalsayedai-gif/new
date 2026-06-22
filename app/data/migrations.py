"""ترقيات مخطط قاعدة البيانات بين الإصدارات.

عند رفع ``AppConfig.DB_SCHEMA_VERSION`` أضف فرعًا جديدًا ينفّذ عبارات
ALTER/CREATE اللازمة. أساسي لتحديث المنتج لدى العملاء دون فقد بياناتهم.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.data import schema

if TYPE_CHECKING:
    from app.data.database import Database


def run(db: "Database", old_version: int, new_version: int) -> None:
    with db.transaction() as conn:
        # v1 -> v2: حقول المخزون (الوحدة/الحد الأدنى/الحالة) + جدول حركة المخزون.
        if old_version < 2:
            conn.execute(
                "ALTER TABLE inventory_items ADD COLUMN unit TEXT NOT NULL "
                "DEFAULT 'قطعة'"
            )
            conn.execute(
                "ALTER TABLE inventory_items ADD COLUMN min_stock REAL NOT NULL "
                "DEFAULT 0"
            )
            conn.execute(
                "ALTER TABLE inventory_items ADD COLUMN status TEXT NOT NULL "
                "DEFAULT 'active'"
            )
            conn.execute(schema.STOCK_MOVEMENTS_DDL)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_stock_movements_item "
                "ON stock_movements(item_id)"
            )

        # v2 -> v3: الحد الائتماني للعميل.
        if old_version < 3:
            conn.execute(
                "ALTER TABLE customers ADD COLUMN credit_limit REAL NOT NULL "
                "DEFAULT 0"
            )
