"""خدمة التقارير — تبني نتائج التقارير (صفوف + إجماليات + كشوف) فوق المستودع.

لا تكرّر منطق الوحدات؛ تقرأ البيانات الحقيقية وتجمّعها فقط. كشوف الحساب تُبنى من
الـ ledger الحقيقي (فواتير كمدين، مدفوعات كدائن) مع رصيد افتتاحي/ختامي.
"""
from __future__ import annotations

from datetime import date

from app.data.repositories.installments_repository import InstallmentsRepository
from app.data.repositories.reports_repository import ReportsRepository


class ReportsService:
    def __init__(
        self, repo: ReportsRepository, installments_repo: InstallmentsRepository
    ):
        self._repo = repo
        self._installments = installments_repo

    # ── المبيعات ────────────────────────────────────────────────────────
    def sales_report(self, dfrom: str, dto: str) -> dict:
        rows = self._repo.sales(dfrom, dto)
        total = sum(r["total"] or 0 for r in rows)
        paid = sum(r["paid"] or 0 for r in rows)
        remaining = sum(r["remaining"] or 0 for r in rows)
        discount = sum(r["discount"] or 0 for r in rows)
        cash = sum(1 for r in rows if (r["remaining"] or 0) <= 0)
        credit = sum(1 for r in rows if (r["paid"] or 0) <= 0 and (r["remaining"] or 0) > 0)
        partial = len(rows) - cash - credit
        revenue, cost = self._repo.sales_profit(dfrom, dto)
        return {
            "rows": rows,
            "totals": {
                "count": len(rows), "total": total, "paid": paid,
                "remaining": remaining, "discount": discount,
                "cash": cash, "credit": credit, "partial": partial,
                "profit": revenue - cost,
            },
        }

    # ── المشتريات ───────────────────────────────────────────────────────
    def purchases_report(self, dfrom: str, dto: str) -> dict:
        rows = self._repo.purchases(dfrom, dto)
        total = sum(r["total"] or 0 for r in rows)
        paid = sum(r["paid"] or 0 for r in rows)
        remaining = sum(r["remaining"] or 0 for r in rows)
        fully = sum(1 for r in rows if (r["remaining"] or 0) <= 0)
        unpaid = sum(1 for r in rows if (r["paid"] or 0) <= 0 and (r["remaining"] or 0) > 0)
        partial = len(rows) - fully - unpaid
        return {
            "rows": rows,
            "totals": {
                "count": len(rows), "total": total, "paid": paid,
                "remaining": remaining, "fully": fully, "unpaid": unpaid,
                "partial": partial,
            },
        }

    # ── الخزينة ─────────────────────────────────────────────────────────
    def treasury_report(self, dfrom: str, dto: str) -> dict:
        rows = self._repo.treasury(dfrom, dto)
        opening = self._repo.treasury_opening(dfrom)
        total_in = sum(r["amount"] or 0 for r in rows if r["direction"] == "in")
        total_out = sum(r["amount"] or 0 for r in rows if r["direction"] == "out")
        net = total_in - total_out
        return {
            "rows": rows,
            "totals": {
                "opening": opening, "total_in": total_in, "total_out": total_out,
                "net": net, "closing": opening + net,
            },
        }

    # ── الأرباح ─────────────────────────────────────────────────────────
    def profit_report(self, dfrom: str, dto: str) -> dict:
        revenue, cost = self._repo.sales_profit(dfrom, dto)
        discounts = self._repo.all_sales_discounts(dfrom, dto)
        by_item = self._repo.sales_by_item(dfrom, dto)
        return {
            "revenue": revenue, "cost": cost, "discounts": discounts,
            "profit": revenue - cost, "by_item": by_item,
        }

    # ── المخزون ─────────────────────────────────────────────────────────
    def inventory_report(self, stagnant_days: int = 30) -> dict:
        rows = self._repo.inventory_snapshot()
        today = date.today()
        total_value = 0.0
        out: list[dict] = []
        for r in rows:
            qty = r["quantity"] or 0
            value = qty * (r["unit_cost"] or 0)
            total_value += value
            stagnant = False
            last = r["last_move"]
            if last:
                try:
                    last_d = date.fromisoformat(last[:10])
                    stagnant = (today - last_d).days >= stagnant_days
                except (ValueError, TypeError):
                    stagnant = False
            else:
                stagnant = True
            low = (r["min_stock"] or 0) > 0 and qty <= (r["min_stock"] or 0)
            out.append(
                {
                    "name": r["name"], "category": r["category"] or "",
                    "quantity": qty, "min_stock": r["min_stock"] or 0,
                    "unit_cost": r["unit_cost"] or 0, "value": value,
                    "low": low, "stagnant": stagnant, "last_move": last,
                }
            )
        return {
            "rows": out, "total_value": total_value,
            "low_count": sum(1 for x in out if x["low"]),
            "stagnant_count": sum(1 for x in out if x["stagnant"]),
        }

    # ── الأقساط والمتأخرات ──────────────────────────────────────────────
    def arrears_report(self) -> dict:
        today = date.today().isoformat()
        rows = self._installments.overdue_by_customer(today)
        due = self._installments.due_on(today)
        total_overdue = sum(r["overdue_amount"] or 0 for r in rows)
        enriched = []
        for r in rows:
            try:
                days = (date.fromisoformat(today) - date.fromisoformat(r["oldest_due"])).days
            except (ValueError, TypeError):
                days = 0
            enriched.append({
                "customer_id": r["customer_id"], "customer_name": r["customer_name"],
                "count": r["overdue_count"], "amount": r["overdue_amount"] or 0,
                "oldest_due": r["oldest_due"], "days": max(days, 0),
                "bucket": self._aging_bucket(max(days, 0)),
            })
        return {"rows": enriched, "due_today": due, "total_overdue": total_overdue}

    @staticmethod
    def _aging_bucket(days: int) -> str:
        if days <= 30:
            return "1-30 يوم"
        if days <= 60:
            return "31-60 يوم"
        if days <= 90:
            return "61-90 يوم"
        return "أكثر من 90 يوم"

    # ── كشوف الحساب ─────────────────────────────────────────────────────
    def customer_statement(self, customer_id: int, dfrom: str, dto: str) -> dict:
        opening = self._repo.customer_open(customer_id, dfrom)
        movements: list[dict] = []
        for s in self._repo.customer_sales_range(customer_id, dfrom, dto):
            movements.append({
                "date": s["date"], "desc": f"فاتورة #{s['id']}",
                "debit": s["total"] or 0, "credit": 0.0, "sort": (s["date"], 0),
            })
        for p in self._repo.customer_payments_range(customer_id, dfrom, dto):
            movements.append({
                "date": p["d"], "desc": p["notes"] or "تحصيل",
                "debit": 0.0, "credit": p["amount"] or 0, "sort": (p["d"], 1),
            })
        movements.sort(key=lambda m: m["sort"])
        balance = opening
        for m in movements:
            balance += m["debit"] - m["credit"]
            m["balance"] = balance
        return {"opening": opening, "movements": movements, "closing": balance}

    def supplier_statement(self, supplier_id: int, dfrom: str, dto: str) -> dict:
        opening = self._repo.supplier_open(supplier_id, dfrom)
        movements: list[dict] = []
        for p in self._repo.supplier_purchases_range(supplier_id, dfrom, dto):
            movements.append({
                "date": p["date"], "desc": f"فاتورة شراء #{p['id']}",
                "credit": p["total"] or 0, "debit": 0.0, "sort": (p["date"], 0),
            })
        for pay in self._repo.supplier_payments_range(supplier_id, dfrom, dto):
            movements.append({
                "date": pay["d"], "desc": pay["notes"] or "دفعة",
                "credit": 0.0, "debit": pay["amount"] or 0, "sort": (pay["d"], 1),
            })
        movements.sort(key=lambda m: m["sort"])
        balance = opening
        for m in movements:
            balance += m["credit"] - m["debit"]
            m["balance"] = balance
        return {"opening": opening, "movements": movements, "closing": balance}
