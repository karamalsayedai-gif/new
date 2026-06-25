"""مستودع المشتريات.

يحتوي العمليات الذرّية (داخل معاملة واحدة) التي تربط فاتورة الشراء بـ:
- بنود الفاتورة (purchase_items)
- حركة المخزون (stock_movements + تحديث كمية الأصناف وتكلفتها)
- الخزينة (treasury) للمبلغ المدفوع
- رصيد المورّد (suppliers.balance) للمبلغ المتبقّي

وضعها في المستودع يضمن الذرّية (atomicity) دون توزيع المعاملة على عدة خدمات.
"""
from __future__ import annotations

from typing import Sequence

from app.core.utils.formatters import now_iso
from app.data.repositories.base_repository import BaseRepository
from app.domain.entities import Purchase, PurchaseItem


class PurchasesRepository(BaseRepository):
    def create_full(
        self,
        *,
        supplier_id: int,
        date: str,
        day_id: int | None,
        user_id: int | None,
        notes: str | None,
        paid: float,
        items: Sequence[dict],
        update_item_cost: bool = True,
        invoice_prefix: str = "ش-",
        treasury_id: int | None = None,
    ) -> tuple[int, float, str]:
        """ترحيل فاتورة شراء كاملة في معاملة واحدة. يعيد (المعرّف، الإجمالي، الرقم)."""
        total = sum(float(it["quantity"]) * float(it["unit_cost"]) for it in items)
        stamp = now_iso()
        with self.db.transaction() as conn:
            invoice_no = self.next_sequence(conn, "purchases", invoice_prefix)
            cur = conn.execute(
                "INSERT INTO purchases(supplier_id, invoice_no, total, paid, date, "
                "day_id, user_id, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (supplier_id, invoice_no, total, paid, date, day_id, user_id, notes),
            )
            purchase_id = int(cur.lastrowid)

            for it in items:
                qty = float(it["quantity"])
                cost = float(it["unit_cost"])
                item_id = it.get("item_id")
                conn.execute(
                    "INSERT INTO purchase_items(purchase_id, item_id, description, "
                    "quantity, unit_cost) VALUES (?, ?, ?, ?, ?)",
                    (purchase_id, item_id, it.get("description", ""), qty, cost),
                )
                if item_id is not None:
                    # إدخال للمخزون (حركة دخول) + تحديث الكمية والتكلفة.
                    conn.execute(
                        "INSERT INTO stock_movements(item_id, direction, quantity, "
                        "reason, ref_table, ref_id, user_id, created_at) "
                        "VALUES (?, 'in', ?, 'شراء', 'purchases', ?, ?, ?)",
                        (item_id, qty, purchase_id, user_id, stamp),
                    )
                    if update_item_cost:
                        conn.execute(
                            "UPDATE inventory_items SET quantity = quantity + ?, "
                            "unit_cost = ? WHERE id = ?",
                            (qty, cost, item_id),
                        )
                    else:
                        conn.execute(
                            "UPDATE inventory_items SET quantity = quantity + ? "
                            "WHERE id = ?",
                            (qty, item_id),
                        )

            if paid > 0:
                conn.execute(
                    "INSERT INTO treasury(direction, category, amount, treasury_id, "
                    "ref_table, ref_id, date, day_id, user_id, notes) "
                    "VALUES ('out', 'purchase', ?, "
                    "COALESCE(?, (SELECT id FROM treasuries WHERE is_default=1 LIMIT 1)), "
                    "'purchases', ?, ?, ?, ?, ?)",
                    (paid, treasury_id, purchase_id, stamp, day_id, user_id,
                     "سداد فاتورة شراء"),
                )

            remaining = total - paid
            if remaining != 0:
                conn.execute(
                    "UPDATE suppliers SET balance = balance + ? WHERE id = ?",
                    (remaining, supplier_id),
                )

            return purchase_id, total, invoice_no

    def delete_full(self, purchase_id: int, user_id: int | None) -> None:
        """عكس فاتورة شراء بالكامل (مخزون/خزينة/رصيد مورّد) في معاملة واحدة."""
        header = self.db.query_one(
            "SELECT * FROM purchases WHERE id = ?", (purchase_id,)
        )
        if header is None:
            return
        items = self.db.query(
            "SELECT * FROM purchase_items WHERE purchase_id = ?", (purchase_id,)
        )
        stamp = now_iso()
        with self.db.transaction() as conn:
            # عكس المخزون: صرف الكميات التي أُدخلت.
            for it in items:
                if it["item_id"] is not None:
                    conn.execute(
                        "INSERT INTO stock_movements(item_id, direction, quantity, "
                        "reason, ref_table, ref_id, user_id, created_at) "
                        "VALUES (?, 'out', ?, 'إلغاء شراء', 'purchases', ?, ?, ?)",
                        (it["item_id"], it["quantity"], purchase_id, user_id, stamp),
                    )
                    conn.execute(
                        "UPDATE inventory_items SET quantity = quantity - ? WHERE id = ?",
                        (it["quantity"], it["item_id"]),
                    )
            # عكس الخزينة: حذف حركات الصرف المرتبطة بالفاتورة.
            conn.execute(
                "DELETE FROM treasury WHERE ref_table='purchases' AND ref_id=?",
                (purchase_id,),
            )
            # عكس رصيد المورّد بمقدار المتبقّي الذي كان قد أُضيف.
            remaining = (header["total"] or 0) - (header["paid"] or 0)
            if remaining != 0:
                conn.execute(
                    "UPDATE suppliers SET balance = balance - ? WHERE id = ?",
                    (remaining, header["supplier_id"]),
                )
            # حذف الفاتورة وبنودها (CASCADE على البنود).
            conn.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))

    # ── استعلامات ───────────────────────────────────────────────────────
    def find_by_id(self, purchase_id: int) -> Purchase | None:
        row = self.db.query_one(
            """
            SELECT p.*, s.name AS supplier_name
            FROM purchases p JOIN suppliers s ON s.id = p.supplier_id
            WHERE p.id = ?
            """,
            (purchase_id,),
        )
        return Purchase.from_row(row) if row else None

    def items(self, purchase_id: int) -> list[PurchaseItem]:
        rows = self.db.query(
            "SELECT * FROM purchase_items WHERE purchase_id = ? ORDER BY id",
            (purchase_id,),
        )
        return [PurchaseItem.from_row(r) for r in rows]

    def list_recent(self, search: str = "", limit: int = 300) -> list[Purchase]:
        if search.strip():
            like = f"%{search.strip()}%"
            rows = self.db.query(
                """
                SELECT p.*, s.name AS supplier_name
                FROM purchases p JOIN suppliers s ON s.id = p.supplier_id
                WHERE s.name LIKE ? ORDER BY p.id DESC LIMIT ?
                """,
                (like, limit),
            )
        else:
            rows = self.db.query(
                """
                SELECT p.*, s.name AS supplier_name
                FROM purchases p JOIN suppliers s ON s.id = p.supplier_id
                ORDER BY p.id DESC LIMIT ?
                """,
                (limit,),
            )
        return [Purchase.from_row(r) for r in rows]
