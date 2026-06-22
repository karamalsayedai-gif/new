"""مستودع التقسيط.

عمليات ذرّية تربط بيع التقسيط والتحصيل بـ: المخزون + الخزينة + رصيد العميل +
جدول الأقساط.
"""
from __future__ import annotations

from typing import Sequence

from app.core.utils.formatters import now_iso
from app.data.repositories.base_repository import BaseRepository
from app.domain.entities import Installment, InstallmentPlan


class InstallmentsRepository(BaseRepository):
    def create_installment_sale(
        self,
        *,
        customer_id: int,
        date: str,
        day_id: int | None,
        user_id: int | None,
        notes: str | None,
        sale_total: float,
        down_payment: float,
        schedule_total: float,
        months: int,
        interest: float,
        items: Sequence[dict],
        installments: Sequence[dict],
        invoice_prefix: str = "ف-",
    ) -> tuple[int, int]:
        """ترحيل بيع تقسيط كامل في معاملة واحدة. يعيد (sale_id, plan_id)."""
        stamp = now_iso()
        with self.db.transaction() as conn:
            invoice_no = self.next_sequence(conn, "sales", invoice_prefix)
            cur = conn.execute(
                "INSERT INTO sales(customer_id, type, invoice_no, total, discount, "
                "paid, date, day_id, user_id, notes) "
                "VALUES (?, 'installment', ?, ?, 0, ?, ?, ?, ?, ?)",
                (customer_id, invoice_no, sale_total, down_payment, date, day_id,
                 user_id, notes),
            )
            sale_id = int(cur.lastrowid)

            for it in items:
                qty = float(it["quantity"])
                item_id = it.get("item_id")
                conn.execute(
                    "INSERT INTO sale_items(sale_id, item_id, description, quantity, "
                    "unit_price) VALUES (?, ?, ?, ?, ?)",
                    (sale_id, item_id, it.get("description", ""), qty,
                     float(it["unit_price"])),
                )
                if item_id is not None:
                    conn.execute(
                        "INSERT INTO stock_movements(item_id, direction, quantity, "
                        "reason, ref_table, ref_id, user_id, created_at) "
                        "VALUES (?, 'out', ?, 'بيع تقسيط', 'sales', ?, ?, ?)",
                        (item_id, qty, sale_id, user_id, stamp),
                    )
                    conn.execute(
                        "UPDATE inventory_items SET quantity = quantity - ? WHERE id = ?",
                        (qty, item_id),
                    )

            if down_payment > 0:
                conn.execute(
                    "INSERT INTO treasury(direction, category, amount, ref_table, "
                    "ref_id, date, day_id, user_id, notes) "
                    "VALUES ('in', 'installment', ?, 'sales', ?, ?, ?, ?, ?)",
                    (down_payment, sale_id, stamp, day_id, user_id, "مقدّم تقسيط"),
                )

            # العميل مدين بكامل جدول الأقساط (أصل متبقٍّ + فائدة).
            conn.execute(
                "UPDATE customers SET balance = balance + ? WHERE id = ?",
                (schedule_total, customer_id),
            )

            pcur = conn.execute(
                "INSERT INTO installment_plans(sale_id, down_payment, months, "
                "interest_pct, total_amount, status) VALUES (?, ?, ?, 0, ?, 'active')",
                (sale_id, down_payment, months, schedule_total),
            )
            plan_id = int(pcur.lastrowid)

            for ins in installments:
                conn.execute(
                    "INSERT INTO installments(plan_id, number, due_date, amount, "
                    "principal, interest, paid_amount, status) "
                    "VALUES (?, ?, ?, ?, ?, ?, 0, 'pending')",
                    (plan_id, ins["number"], ins["due_date"], ins["amount"],
                     ins["principal"], ins["interest"]),
                )

            return sale_id, plan_id

    def collect(
        self, *, plan_id: int, amount: float, day_id: int | None, user_id: int | None
    ) -> float:
        """توزيع مبلغ التحصيل على الأقساط الأقدم أولًا. يعيد المبلغ المُحصَّل فعليًا."""
        plan = self.db.query_one(
            "SELECT * FROM installment_plans WHERE id = ?", (plan_id,)
        )
        if plan is None:
            return 0.0
        sale = self.db.query_one(
            "SELECT * FROM sales WHERE id = ?", (plan["sale_id"],)
        )
        customer_id = sale["customer_id"] if sale else None
        unpaid = self.db.query(
            "SELECT * FROM installments WHERE plan_id = ? "
            "AND (amount - paid_amount) > 0.0001 ORDER BY number",
            (plan_id,),
        )
        stamp = now_iso()
        money_left = amount
        collected = 0.0
        with self.db.transaction() as conn:
            for ins in unpaid:
                if money_left <= 0.0001:
                    break
                remaining = (ins["amount"] or 0) - (ins["paid_amount"] or 0)
                pay = min(remaining, money_left)
                new_paid = (ins["paid_amount"] or 0) + pay
                fully = new_paid >= (ins["amount"] or 0) - 0.0001
                conn.execute(
                    "UPDATE installments SET paid_amount = ?, status = ?, "
                    "paid_at = ? WHERE id = ?",
                    (new_paid, "paid" if fully else "partial",
                     stamp if fully else ins["paid_at"], ins["id"]),
                )
                money_left -= pay
                collected += pay

            if collected > 0:
                conn.execute(
                    "INSERT INTO treasury(direction, category, amount, ref_table, "
                    "ref_id, date, day_id, user_id, notes) "
                    "VALUES ('in', 'installment', ?, 'sales', ?, ?, ?, ?, ?)",
                    (collected, plan["sale_id"], stamp, day_id, user_id,
                     "تحصيل قسط"),
                )
                if customer_id is not None:
                    conn.execute(
                        "UPDATE customers SET balance = balance - ? WHERE id = ?",
                        (collected, customer_id),
                    )

            # اكتمال الخطة؟
            still = conn.execute(
                "SELECT COUNT(*) AS c FROM installments WHERE plan_id = ? "
                "AND (amount - paid_amount) > 0.0001",
                (plan_id,),
            ).fetchone()
            if still and still["c"] == 0:
                conn.execute(
                    "UPDATE installment_plans SET status = 'completed' WHERE id = ?",
                    (plan_id,),
                )
        return collected

    # ── استعلامات ───────────────────────────────────────────────────────
    def find_plan(self, plan_id: int) -> InstallmentPlan | None:
        row = self.db.query_one(
            """
            SELECT p.*, s.customer_id, s.total AS sale_total, s.date AS sale_date,
                   c.name AS customer_name
            FROM installment_plans p
            JOIN sales s ON s.id = p.sale_id
            LEFT JOIN customers c ON c.id = s.customer_id
            WHERE p.id = ?
            """,
            (plan_id,),
        )
        return InstallmentPlan.from_row(row) if row else None

    def list_plans(self, search: str = "", limit: int = 300) -> list[InstallmentPlan]:
        base = """
            SELECT p.*, s.customer_id, s.total AS sale_total, s.date AS sale_date,
                   c.name AS customer_name
            FROM installment_plans p
            JOIN sales s ON s.id = p.sale_id
            LEFT JOIN customers c ON c.id = s.customer_id
        """
        if search.strip():
            like = f"%{search.strip()}%"
            rows = self.db.query(
                base + " WHERE c.name LIKE ? ORDER BY p.id DESC LIMIT ?",
                (like, limit),
            )
        else:
            rows = self.db.query(base + " ORDER BY p.id DESC LIMIT ?", (limit,))
        return [InstallmentPlan.from_row(r) for r in rows]

    def installments_for_plan(self, plan_id: int) -> list[Installment]:
        rows = self.db.query(
            "SELECT * FROM installments WHERE plan_id = ? ORDER BY number",
            (plan_id,),
        )
        return [Installment.from_row(r) for r in rows]

    def collections_for_plan(self, plan_id: int):
        plan = self.db.query_one(
            "SELECT sale_id FROM installment_plans WHERE id = ?", (plan_id,)
        )
        if plan is None:
            return []
        return self.db.query(
            "SELECT * FROM treasury WHERE ref_table='sales' AND ref_id=? "
            "AND category='installment' ORDER BY id DESC",
            (plan["sale_id"],),
        )

    def plan_paid(self, plan_id: int) -> float:
        row = self.db.query_one(
            "SELECT COALESCE(SUM(paid_amount), 0) AS p FROM installments "
            "WHERE plan_id = ?",
            (plan_id,),
        )
        return float(row["p"]) if row else 0.0

    def overdue_by_customer(self, today: str):
        return self.db.query(
            """
            SELECT c.id AS customer_id, c.name AS customer_name,
                   SUM(i.amount - i.paid_amount) AS overdue_amount,
                   MIN(i.due_date) AS oldest_due,
                   COUNT(*) AS overdue_count
            FROM installments i
            JOIN installment_plans p ON p.id = i.plan_id
            JOIN sales s ON s.id = p.sale_id
            JOIN customers c ON c.id = s.customer_id
            WHERE i.due_date < ? AND (i.amount - i.paid_amount) > 0.0001
            GROUP BY c.id, c.name
            ORDER BY overdue_amount DESC
            """,
            (today,),
        )

    def due_on(self, day: str):
        return self.db.query(
            """
            SELECT i.*, c.name AS customer_name, p.id AS plan_ref
            FROM installments i
            JOIN installment_plans p ON p.id = i.plan_id
            JOIN sales s ON s.id = p.sale_id
            LEFT JOIN customers c ON c.id = s.customer_id
            WHERE i.due_date = ? AND (i.amount - i.paid_amount) > 0.0001
            ORDER BY c.name
            """,
            (day,),
        )
