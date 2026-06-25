"""مستودع المرتجعات (بيع/شراء).

عمليات ذرّية تعكس جزءًا من فاتورة:
- مرتجع بيع: إرجاع البضاعة للمخزون + ردّ نقدي (صرف) و/أو تخفيض مديونية العميل.
- مرتجع شراء: إخراج البضاعة من المخزون + استرداد نقدي (قبض) و/أو تخفيض ما على
  المعرض للمورّد.
"""
from __future__ import annotations

from typing import Sequence

from app.core.utils.formatters import now_iso
from app.data.repositories.base_repository import BaseRepository


class ReturnsRepository(BaseRepository):
    def create_sale_return(
        self,
        *,
        sale_id: int,
        date: str,
        day_id: int | None,
        user_id: int | None,
        notes: str | None,
        refund: float,
        items: Sequence[dict],
        treasury_id: int | None = None,
    ) -> tuple[int, float]:
        total = sum(float(it["quantity"]) * float(it["unit_price"]) for it in items)
        stamp = now_iso()
        sale = self.db.query_one("SELECT * FROM sales WHERE id = ?", (sale_id,))
        customer_id = sale["customer_id"] if sale else None
        invoice_no = sale["invoice_no"] if sale else None
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO returns(type, ref_id, invoice_no, total, refund, date, "
                "day_id, user_id, notes) VALUES ('sale', ?, ?, ?, ?, ?, ?, ?, ?)",
                (sale_id, invoice_no, total, refund, date, day_id, user_id, notes),
            )
            return_id = int(cur.lastrowid)
            for it in items:
                qty = float(it["quantity"])
                item_id = it.get("item_id")
                conn.execute(
                    "INSERT INTO return_items(return_id, item_id, description, "
                    "quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
                    (return_id, item_id, it.get("description", ""), qty,
                     float(it["unit_price"])),
                )
                if item_id is not None:
                    conn.execute(
                        "INSERT INTO stock_movements(item_id, direction, quantity, "
                        "reason, ref_table, ref_id, user_id, created_at) "
                        "VALUES (?, 'in', ?, 'مرتجع بيع', 'returns', ?, ?, ?)",
                        (item_id, qty, return_id, user_id, stamp),
                    )
                    conn.execute(
                        "UPDATE inventory_items SET quantity = quantity + ? WHERE id = ?",
                        (qty, item_id),
                    )
            if refund > 0:
                conn.execute(
                    "INSERT INTO treasury(direction, category, amount, treasury_id, "
                    "ref_table, ref_id, date, day_id, user_id, notes) "
                    "VALUES ('out', 'return', ?, "
                    "COALESCE(?, (SELECT id FROM treasuries WHERE is_default=1 LIMIT 1)), "
                    "'returns', ?, ?, ?, ?, ?)",
                    (refund, treasury_id, return_id, stamp, day_id, user_id,
                     "ردّ مرتجع بيع"),
                )
            credit = total - refund
            if credit > 0 and customer_id is not None:
                conn.execute(
                    "UPDATE customers SET balance = balance - ? WHERE id = ?",
                    (credit, customer_id),
                )
            return return_id, total

    def create_purchase_return(
        self,
        *,
        purchase_id: int,
        date: str,
        day_id: int | None,
        user_id: int | None,
        notes: str | None,
        refund: float,
        items: Sequence[dict],
        treasury_id: int | None = None,
    ) -> tuple[int, float]:
        total = sum(float(it["quantity"]) * float(it["unit_price"]) for it in items)
        stamp = now_iso()
        purchase = self.db.query_one(
            "SELECT * FROM purchases WHERE id = ?", (purchase_id,)
        )
        supplier_id = purchase["supplier_id"] if purchase else None
        invoice_no = purchase["invoice_no"] if purchase else None
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO returns(type, ref_id, invoice_no, total, refund, date, "
                "day_id, user_id, notes) VALUES ('purchase', ?, ?, ?, ?, ?, ?, ?, ?)",
                (purchase_id, invoice_no, total, refund, date, day_id, user_id, notes),
            )
            return_id = int(cur.lastrowid)
            for it in items:
                qty = float(it["quantity"])
                item_id = it.get("item_id")
                conn.execute(
                    "INSERT INTO return_items(return_id, item_id, description, "
                    "quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
                    (return_id, item_id, it.get("description", ""), qty,
                     float(it["unit_price"])),
                )
                if item_id is not None:
                    conn.execute(
                        "INSERT INTO stock_movements(item_id, direction, quantity, "
                        "reason, ref_table, ref_id, user_id, created_at) "
                        "VALUES (?, 'out', ?, 'مرتجع شراء', 'returns', ?, ?, ?)",
                        (item_id, qty, return_id, user_id, stamp),
                    )
                    conn.execute(
                        "UPDATE inventory_items SET quantity = quantity - ? WHERE id = ?",
                        (qty, item_id),
                    )
            if refund > 0:
                conn.execute(
                    "INSERT INTO treasury(direction, category, amount, treasury_id, "
                    "ref_table, ref_id, date, day_id, user_id, notes) "
                    "VALUES ('in', 'return', ?, "
                    "COALESCE(?, (SELECT id FROM treasuries WHERE is_default=1 LIMIT 1)), "
                    "'returns', ?, ?, ?, ?, ?)",
                    (refund, treasury_id, return_id, stamp, day_id, user_id,
                     "استرداد مرتجع شراء"),
                )
            debt = total - refund
            if debt > 0 and supplier_id is not None:
                conn.execute(
                    "UPDATE suppliers SET balance = balance - ? WHERE id = ?",
                    (debt, supplier_id),
                )
            return return_id, total

    # ── استعلامات ───────────────────────────────────────────────────────
    def list_for_ref(self, kind: str, ref_id: int):
        return self.db.query(
            "SELECT * FROM returns WHERE type = ? AND ref_id = ? ORDER BY id DESC",
            (kind, ref_id),
        )

    def items(self, return_id: int):
        return self.db.query(
            "SELECT * FROM return_items WHERE return_id = ? ORDER BY id",
            (return_id,),
        )

    def returned_qty(self, kind: str, ref_id: int) -> dict[int, float]:
        """إجمالي الكميات المُرتجعة سابقًا لكل صنف من فاتورة (لمنع تجاوز المباع)."""
        rows = self.db.query(
            """
            SELECT ri.item_id AS item_id, COALESCE(SUM(ri.quantity),0) AS q
            FROM return_items ri JOIN returns r ON r.id = ri.return_id
            WHERE r.type = ? AND r.ref_id = ? AND ri.item_id IS NOT NULL
            GROUP BY ri.item_id
            """,
            (kind, ref_id),
        )
        return {r["item_id"]: float(r["q"]) for r in rows}
