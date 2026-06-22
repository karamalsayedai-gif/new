"""مستودع التقارير — استعلامات تجميعية للقراءة فقط على البيانات الحقيقية.

مصدر وحيد لكل استعلامات التقارير لتفادي تكرار المنطق. التواريخ:
- sales/purchases.date مخزّنة بصيغة يوم (yyyy-mm-dd) فتُقارَن مباشرة.
- treasury.date طابع زمني كامل فنستخدم substr(date,1,10) للمقارنة باليوم.
"""
from __future__ import annotations

from app.data.repositories.base_repository import BaseRepository


class ReportsRepository(BaseRepository):
    # ── المبيعات ────────────────────────────────────────────────────────
    def sales(self, dfrom: str, dto: str):
        return self.db.query(
            """
            SELECT s.id, s.date, s.total, s.discount, s.paid,
                   (s.total - s.paid) AS remaining, s.customer_id, s.user_id,
                   c.name AS customer_name, u.username
            FROM sales s
            LEFT JOIN customers c ON c.id = s.customer_id
            LEFT JOIN users u ON u.id = s.user_id
            WHERE s.type='cash' AND s.date BETWEEN ? AND ?
            ORDER BY s.id
            """,
            (dfrom, dto),
        )

    def sales_profit(self, dfrom: str, dto: str) -> tuple[float, float]:
        row = self.db.query_one(
            """
            SELECT COALESCE(SUM(si.quantity*si.unit_price),0) AS revenue,
                   COALESCE(SUM(si.quantity*COALESCE(inv.unit_cost,0)),0) AS cost
            FROM sale_items si JOIN sales s ON s.id = si.sale_id
            LEFT JOIN inventory_items inv ON inv.id = si.item_id
            WHERE s.type='cash' AND s.date BETWEEN ? AND ?
            """,
            (dfrom, dto),
        )
        return (float(row["revenue"]), float(row["cost"])) if row else (0.0, 0.0)

    def sales_by_item(self, dfrom: str, dto: str):
        return self.db.query(
            """
            SELECT si.description,
                   SUM(si.quantity) AS qty,
                   SUM(si.quantity*si.unit_price) AS revenue,
                   SUM(si.quantity*COALESCE(inv.unit_cost,0)) AS cost
            FROM sale_items si JOIN sales s ON s.id = si.sale_id
            LEFT JOIN inventory_items inv ON inv.id = si.item_id
            WHERE s.type IN ('cash','installment') AND s.date BETWEEN ? AND ?
            GROUP BY si.description ORDER BY revenue DESC
            """,
            (dfrom, dto),
        )

    def sales_daily(self, dfrom: str, dto: str):
        return self.db.query(
            "SELECT date, COALESCE(SUM(total),0) AS total FROM sales "
            "WHERE type='cash' AND date BETWEEN ? AND ? GROUP BY date ORDER BY date",
            (dfrom, dto),
        )

    def all_sales_discounts(self, dfrom: str, dto: str) -> float:
        row = self.db.query_one(
            "SELECT COALESCE(SUM(discount),0) AS d FROM sales "
            "WHERE date BETWEEN ? AND ?",
            (dfrom, dto),
        )
        return float(row["d"]) if row else 0.0

    # ── المشتريات ───────────────────────────────────────────────────────
    def purchases(self, dfrom: str, dto: str):
        return self.db.query(
            """
            SELECT p.id, p.date, p.total, p.paid, (p.total - p.paid) AS remaining,
                   s.name AS supplier_name
            FROM purchases p JOIN suppliers s ON s.id = p.supplier_id
            WHERE p.date BETWEEN ? AND ?
            ORDER BY p.id
            """,
            (dfrom, dto),
        )

    # ── الخزينة ─────────────────────────────────────────────────────────
    def treasury(self, dfrom: str, dto: str):
        return self.db.query(
            """
            SELECT t.*, u.username
            FROM treasury t LEFT JOIN users u ON u.id = t.user_id
            WHERE substr(t.date,1,10) BETWEEN ? AND ?
            ORDER BY t.id
            """,
            (dfrom, dto),
        )

    def treasury_opening(self, dfrom: str) -> float:
        row = self.db.query_one(
            "SELECT COALESCE(SUM(CASE WHEN direction='in' THEN amount "
            "ELSE -amount END),0) AS bal FROM treasury WHERE substr(date,1,10) < ?",
            (dfrom,),
        )
        return float(row["bal"]) if row else 0.0

    # ── المخزون ─────────────────────────────────────────────────────────
    def inventory_snapshot(self):
        return self.db.query(
            """
            SELECT i.*,
                   (SELECT MAX(created_at) FROM stock_movements m
                    WHERE m.item_id = i.id) AS last_move
            FROM inventory_items i ORDER BY i.name
            """
        )

    # ── كشف حساب العميل ─────────────────────────────────────────────────
    def customer_open(self, customer_id: int, dfrom: str) -> float:
        debit = self.db.query_one(
            "SELECT COALESCE(SUM(total),0) AS s FROM sales "
            "WHERE customer_id=? AND date < ?",
            (customer_id, dfrom),
        )
        credit = self.db.query_one(
            "SELECT COALESCE(SUM(amount),0) AS s FROM treasury "
            "WHERE ref_table='sales' AND substr(date,1,10) < ? AND ref_id IN "
            "(SELECT id FROM sales WHERE customer_id=?)",
            (dfrom, customer_id),
        )
        return float(debit["s"]) - float(credit["s"])

    def customer_sales_range(self, customer_id: int, dfrom: str, dto: str):
        return self.db.query(
            "SELECT id, date, total FROM sales WHERE customer_id=? "
            "AND date BETWEEN ? AND ? ORDER BY date, id",
            (customer_id, dfrom, dto),
        )

    def customer_payments_range(self, customer_id: int, dfrom: str, dto: str):
        return self.db.query(
            "SELECT id, substr(date,1,10) AS d, amount, notes FROM treasury "
            "WHERE ref_table='sales' AND substr(date,1,10) BETWEEN ? AND ? "
            "AND ref_id IN (SELECT id FROM sales WHERE customer_id=?) "
            "ORDER BY d, id",
            (dfrom, dto, customer_id),
        )

    # ── كشف حساب المورّد ────────────────────────────────────────────────
    def supplier_open(self, supplier_id: int, dfrom: str) -> float:
        credit = self.db.query_one(
            "SELECT COALESCE(SUM(total),0) AS s FROM purchases "
            "WHERE supplier_id=? AND date < ?",
            (supplier_id, dfrom),
        )
        debit = self.db.query_one(
            "SELECT COALESCE(SUM(amount),0) AS s FROM treasury "
            "WHERE ref_table='purchases' AND substr(date,1,10) < ? AND ref_id IN "
            "(SELECT id FROM purchases WHERE supplier_id=?)",
            (dfrom, supplier_id),
        )
        return float(credit["s"]) - float(debit["s"])

    def supplier_purchases_range(self, supplier_id: int, dfrom: str, dto: str):
        return self.db.query(
            "SELECT id, date, total FROM purchases WHERE supplier_id=? "
            "AND date BETWEEN ? AND ? ORDER BY date, id",
            (supplier_id, dfrom, dto),
        )

    def supplier_payments_range(self, supplier_id: int, dfrom: str, dto: str):
        return self.db.query(
            "SELECT id, substr(date,1,10) AS d, amount, notes FROM treasury "
            "WHERE ref_table='purchases' AND substr(date,1,10) BETWEEN ? AND ? "
            "AND ref_id IN (SELECT id FROM purchases WHERE supplier_id=?) "
            "ORDER BY d, id",
            (dfrom, dto, supplier_id),
        )
