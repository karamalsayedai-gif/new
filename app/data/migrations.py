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

        # v3 -> v4: بنود فاتورة الشراء.
        if old_version < 4:
            conn.execute(schema.PURCHASE_ITEMS_DDL)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_purchase_items_purchase "
                "ON purchase_items(purchase_id)"
            )

        # v4 -> v5: خصم على فاتورة البيع.
        if old_version < 5:
            conn.execute(
                "ALTER TABLE sales ADD COLUMN discount REAL NOT NULL DEFAULT 0"
            )

        # v5 -> v6: رقم القسط + فصل الأصل/الفائدة لكل قسط.
        if old_version < 6:
            conn.execute(
                "ALTER TABLE installments ADD COLUMN number INTEGER NOT NULL DEFAULT 0"
            )
            conn.execute(
                "ALTER TABLE installments ADD COLUMN principal REAL NOT NULL DEFAULT 0"
            )
            conn.execute(
                "ALTER TABLE installments ADD COLUMN interest REAL NOT NULL DEFAULT 0"
            )

        # v6 -> v7: قفل الحساب بعد محاولات دخول فاشلة.
        if old_version < 7:
            conn.execute(
                "ALTER TABLE users ADD COLUMN failed_attempts INTEGER NOT NULL "
                "DEFAULT 0"
            )
            conn.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")

        # v7 -> v8: ترقيم رسمي تسلسلي للفواتير.
        if old_version < 8:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS number_sequences ("
                "name TEXT PRIMARY KEY, value INTEGER NOT NULL DEFAULT 0)"
            )
            conn.execute("ALTER TABLE sales ADD COLUMN invoice_no TEXT")
            conn.execute("ALTER TABLE purchases ADD COLUMN invoice_no TEXT")

        # v8 -> v9: مرتجعات البيع والشراء.
        if old_version < 9:
            conn.execute(schema.RETURNS_DDL)
            conn.execute(schema.RETURN_ITEMS_DDL)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_return_items_return "
                "ON return_items(return_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_returns_ref ON returns(type, ref_id)"
            )
