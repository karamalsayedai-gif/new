"""مستودع المبيعات.

يحتوي العمليات الذرّية (داخل معاملة واحدة) التي تربط فاتورة البيع بـ:
- بنود الفاتورة (sale_items)
- حركة المخزون (stock_movements + إنقاص كمية الأصناف)
- الخزينة (treasury) للمبلغ المقبوض
- رصيد العميل (customers.balance) للمبلغ المتبقّي (آجل/جزئي)
"""
from __future__ import annotations

from typing import Sequence

from app.core.utils.formatters import now_iso
from app.data.repositories.base_repository import BaseRepository
from app.domain.entities import Sale, SaleItem


class SalesRepository(BaseRepository):
    def create_full(
        self,
        *,
        customer_id: int | None,
        date: str,
        day_id: int | None,
        user_id: int | None,
        notes: str | None,
        discount: float,
        paid: float,
        items: Sequence[dict],
    ) -> tuple[int, float]:
        """ترحيل فاتورة بيع كاملة في معاملة واحدة. يعيد (المعرّف، الإجمالي)."""
        gross = sum(float(it["quantity"]) * float(it["unit_price"]) for it in items)
        total = gross - discount
        stamp = now_iso()
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO sales(customer_id, type, total, discount, paid, date, "
                "day_id, user_id, notes) VALUES (?, 'cash', ?, ?, ?, ?, ?, ?, ?)",
                (customer_id, total, discount, paid, date, day_id, user_id, notes),
            )
            sale_id = int(cur.lastrowid)

            for it in items:
                qty = float(it["quantity"])
                price = float(it["unit_price"])
                item_id = it.get("item_id")
                conn.execute(
                    "INSERT INTO sale_items(sale_id, item_id, description, quantity, "
                    "unit_price) VALUES (?, ?, ?, ?, ?)",
                    (sale_id, item_id, it.get("description", ""), qty, price),
                )
                if item_id is not None:
                    conn.execute(
                        "INSERT INTO stock_movements(item_id, direction, quantity, "
                        "reason, ref_table, ref_id, user_id, created_at) "
                        "VALUES (?, 'out', ?, 'بيع', 'sales', ?, ?, ?)",
                        (item_id, qty, sale_id, user_id, stamp),
                    )
                    conn.execute(
                        "UPDATE inventory_items SET quantity = quantity - ? WHERE id = ?",
                        (qty, item_id),
                    )

            if paid > 0:
                conn.execute(
                    "INSERT INTO treasury(direction, category, amount, ref_table, "
                    "ref_id, date, day_id, user_id, notes) "
                    "VALUES ('in', 'sale', ?, 'sales', ?, ?, ?, ?, ?)",
                    (paid, sale_id, stamp, day_id, user_id, "تحصيل فاتورة بيع"),
                )

            remaining = total - paid
            if remaining > 0 and customer_id is not None:
                conn.execute(
                    "UPDATE customers SET balance = balance + ? WHERE id = ?",
                    (remaining, customer_id),
                )

            return sale_id, total

    def delete_full(self, sale_id: int, user_id: int | None) -> None:
        """عكس فاتورة بيع بالكامل (مخزون/خزينة/رصيد عميل) في معاملة واحدة."""
        header = self.db.query_one("SELECT * FROM sales WHERE id = ?", (sale_id,))
        if header is None:
            return
        items = self.db.query(
            "SELECT * FROM sale_items WHERE sale_id = ?", (sale_id,)
        )
        stamp = now_iso()
        with self.db.transaction() as conn:
            for it in items:
                if it["item_id"] is not None:
                    conn.execute(
                        "INSERT INTO stock_movements(item_id, direction, quantity, "
                        "reason, ref_table, ref_id, user_id, created_at) "
                        "VALUES (?, 'in', ?, 'إلغاء بيع', 'sales', ?, ?, ?)",
                        (it["item_id"], it["quantity"], sale_id, user_id, stamp),
                    )
                    conn.execute(
                        "UPDATE inventory_items SET quantity = quantity + ? WHERE id = ?",
                        (it["quantity"], it["item_id"]),
                    )
            conn.execute(
                "DELETE FROM treasury WHERE ref_table='sales' AND ref_id=?",
                (sale_id,),
            )
            remaining = (header["total"] or 0) - (header["paid"] or 0)
            if remaining > 0 and header["customer_id"] is not None:
                conn.execute(
                    "UPDATE customers SET balance = balance - ? WHERE id = ?",
                    (remaining, header["customer_id"]),
                )
            conn.execute("DELETE FROM sales WHERE id = ?", (sale_id,))

    # ── استعلامات ───────────────────────────────────────────────────────
    def find_by_id(self, sale_id: int) -> Sale | None:
        row = self.db.query_one(
            """
            SELECT s.*, c.name AS customer_name
            FROM sales s LEFT JOIN customers c ON c.id = s.customer_id
            WHERE s.id = ?
            """,
            (sale_id,),
        )
        return Sale.from_row(row) if row else None

    def items(self, sale_id: int) -> list[SaleItem]:
        rows = self.db.query(
            "SELECT * FROM sale_items WHERE sale_id = ? ORDER BY id", (sale_id,)
        )
        return [SaleItem.from_row(r) for r in rows]

    def list_recent(self, search: str = "", limit: int = 300) -> list[Sale]:
        if search.strip():
            like = f"%{search.strip()}%"
            rows = self.db.query(
                """
                SELECT s.*, c.name AS customer_name
                FROM sales s LEFT JOIN customers c ON c.id = s.customer_id
                WHERE s.type='cash' AND (c.name LIKE ? OR CAST(s.id AS TEXT) LIKE ?)
                ORDER BY s.id DESC LIMIT ?
                """,
                (like, like, limit),
            )
        else:
            rows = self.db.query(
                """
                SELECT s.*, c.name AS customer_name
                FROM sales s LEFT JOIN customers c ON c.id = s.customer_id
                WHERE s.type='cash'
                ORDER BY s.id DESC LIMIT ?
                """,
                (limit,),
            )
        return [Sale.from_row(r) for r in rows]
