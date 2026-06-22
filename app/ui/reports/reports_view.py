"""وحدة التقارير — لوحة + صفحات تقارير كاملة (فلاتر + إجماليات + طباعة/PDF).

كل التقارير تقرأ البيانات الحقيقية عبر ReportsService دون تكرار منطق.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.utils.formatters import format_currency, format_iso_date
from app.ui.components.charts import BarChart
from app.ui.components.page import Page
from app.ui.components.widgets import Card, heading_label, muted_label, title_label
from app.ui.reports.report_base import ReportPage

if TYPE_CHECKING:
    from app.core.container import Container


def _money(c: "Container", v: float) -> str:
    return format_currency(v, c.settings.currency_symbol)


# ── لوحة التقارير (جذر الوحدة) ──────────────────────────────────────────
class ReportsView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 26)
        layout.setSpacing(14)
        layout.addWidget(title_label("التقارير"))
        layout.addWidget(muted_label("اختر تقريرًا — كل تقرير شاشة كاملة بفلاتر وإجماليات وطباعة."))

        grid = QGridLayout()
        grid.setSpacing(12)
        reports = [
            ("تقرير المبيعات", lambda: SalesReportPage(self._c)),
            ("تقرير المشتريات", lambda: PurchasesReportPage(self._c)),
            ("تقرير الخزينة", lambda: TreasuryReportPage(self._c)),
            ("تقرير الأرباح", lambda: ProfitReportPage(self._c)),
            ("تقرير المخزون", lambda: InventoryReportPage(self._c)),
            ("الأقساط والمتأخرات", lambda: ArrearsReportPage(self._c)),
            ("كشف حساب عميل", lambda: CustomerStatementPage(self._c)),
            ("كشف حساب مورّد", lambda: SupplierStatementPage(self._c)),
            ("ملخص بياني (مخططات)", lambda: ChartsReportPage(self._c)),
        ]
        for i, (label, factory) in enumerate(reports):
            btn = QPushButton(label)
            btn.setMinimumHeight(64)
            btn.clicked.connect(lambda _c, f=factory: self._c.navigator.push(f()))
            grid.addWidget(btn, i // 3, i % 3)
        layout.addLayout(grid)
        layout.addStretch(1)


# ── المبيعات ────────────────────────────────────────────────────────────
class SalesReportPage(ReportPage):
    def __init__(self, container: "Container"):
        super().__init__(container, "تقرير المبيعات")
        self.set_columns(
            ["#", "التاريخ", "العميل", "الإجمالي", "الخصم", "المقبوض", "المتبقّي",
             "المستخدم", "الحالة"]
        )
        self.run()

    def run(self) -> None:
        data = self._c.reports.sales_report(self.dfrom, self.dto)
        rows = []
        for r in data["rows"]:
            status = "مدفوعة" if (r["remaining"] or 0) <= 0 else (
                "آجل" if (r["paid"] or 0) <= 0 else "جزئي")
            rows.append([
                r["id"], format_iso_date(r["date"]), r["customer_name"] or "نقدي",
                _money(self._c, r["total"] or 0), _money(self._c, r["discount"] or 0),
                _money(self._c, r["paid"] or 0), _money(self._c, r["remaining"] or 0),
                r["username"] or "", status,
            ])
        self.fill(rows)
        t = data["totals"]
        summary = (
            f"عدد الفواتير: {t['count']} | الإجمالي: {_money(self._c, t['total'])} | "
            f"المقبوض: {_money(self._c, t['paid'])} | المتبقّي: {_money(self._c, t['remaining'])} | "
            f"الخصومات: {_money(self._c, t['discount'])} | نقدي: {t['cash']} "
            f"آجل: {t['credit']} جزئي: {t['partial']} | الربح التقريبي: "
            f"{_money(self._c, t['profit'])}"
        )
        self.set_totals(summary)
        self.build_html(
            ["#", "التاريخ", "العميل", "الإجمالي", "الخصم", "المقبوض", "المتبقّي",
             "المستخدم", "الحالة"],
            [[str(x) for x in row] for row in rows], summary,
        )


# ── المشتريات ───────────────────────────────────────────────────────────
class PurchasesReportPage(ReportPage):
    def __init__(self, container: "Container"):
        super().__init__(container, "تقرير المشتريات")
        self.set_columns(["#", "التاريخ", "المورّد", "الإجمالي", "المدفوع", "المتبقّي", "الحالة"])
        self.run()

    def run(self) -> None:
        data = self._c.reports.purchases_report(self.dfrom, self.dto)
        rows = []
        for r in data["rows"]:
            status = "مدفوعة" if (r["remaining"] or 0) <= 0 else (
                "آجل" if (r["paid"] or 0) <= 0 else "جزئي")
            rows.append([
                r["id"], format_iso_date(r["date"]), r["supplier_name"],
                _money(self._c, r["total"] or 0), _money(self._c, r["paid"] or 0),
                _money(self._c, r["remaining"] or 0), status,
            ])
        self.fill(rows)
        t = data["totals"]
        summary = (
            f"عدد الفواتير: {t['count']} | الإجمالي: {_money(self._c, t['total'])} | "
            f"المدفوع: {_money(self._c, t['paid'])} | المتبقّي: {_money(self._c, t['remaining'])} | "
            f"مسدّدة: {t['fully']} آجل: {t['unpaid']} جزئي: {t['partial']}"
        )
        self.set_totals(summary)
        self.build_html(
            ["#", "التاريخ", "المورّد", "الإجمالي", "المدفوع", "المتبقّي", "الحالة"],
            [[str(x) for x in row] for row in rows], summary,
        )


# ── الخزينة ─────────────────────────────────────────────────────────────
class TreasuryReportPage(ReportPage):
    _DIR = {"in": "قبض", "out": "صرف"}
    _CAT = {"income": "إيراد", "expense": "مصروف", "manual": "تسوية",
            "sale": "بيع", "installment": "قسط", "purchase": "شراء",
            "return": "مرتجع"}

    def __init__(self, container: "Container"):
        super().__init__(container, "تقرير حركة الخزينة")
        self.set_columns(["التاريخ", "النوع", "التصنيف", "المبلغ", "المستخدم", "ملاحظات"])
        self.run()

    def run(self) -> None:
        data = self._c.reports.treasury_report(self.dfrom, self.dto)
        rows = []
        for r in data["rows"]:
            rows.append([
                format_iso_date((r["date"] or "")[:10]),
                self._DIR.get(r["direction"], r["direction"]),
                self._CAT.get(r["category"], r["category"]),
                _money(self._c, r["amount"] or 0), r["username"] or "",
                r["notes"] or "",
            ])
        self.fill(rows)
        t = data["totals"]
        summary = (
            f"رصيد أول المدة: {_money(self._c, t['opening'])} | إجمالي القبض: "
            f"{_money(self._c, t['total_in'])} | إجمالي الصرف: {_money(self._c, t['total_out'])} | "
            f"الصافي: {_money(self._c, t['net'])} | رصيد آخر المدة: "
            f"{_money(self._c, t['closing'])}"
        )
        self.set_totals(summary)
        self.build_html(
            ["التاريخ", "النوع", "التصنيف", "المبلغ", "المستخدم", "ملاحظات"],
            [[str(x) for x in row] for row in rows], summary,
        )


# ── الأرباح ─────────────────────────────────────────────────────────────
class ProfitReportPage(ReportPage):
    def __init__(self, container: "Container"):
        super().__init__(container, "تقرير الأرباح")
        self.set_columns(["الصنف", "الكمية", "إجمالي البيع", "التكلفة", "الربح"])
        self.run()

    def run(self) -> None:
        data = self._c.reports.profit_report(self.dfrom, self.dto)
        rows = []
        for r in data["by_item"]:
            profit = (r["revenue"] or 0) - (r["cost"] or 0)
            rows.append([
                r["description"], r["qty"], _money(self._c, r["revenue"] or 0),
                _money(self._c, r["cost"] or 0), _money(self._c, profit),
            ])
        self.fill(rows)
        summary = (
            f"إجمالي البيع: {_money(self._c, data['revenue'])} | تكلفة الشراء: "
            f"{_money(self._c, data['cost'])} | الخصومات: {_money(self._c, data['discounts'])} | "
            f"صافي الربح: {_money(self._c, data['profit'])}"
        )
        self.set_totals(summary)
        self.build_html(
            ["الصنف", "الكمية", "إجمالي البيع", "التكلفة", "الربح"],
            [[str(x) for x in row] for row in rows], summary,
        )


# ── المخزون ─────────────────────────────────────────────────────────────
class InventoryReportPage(ReportPage):
    def __init__(self, container: "Container"):
        super().__init__(container, "تقرير المخزون", show_dates=False)
        self._stagnant = QSpinBox()
        self._stagnant.setRange(1, 365)
        self._stagnant.setValue(30)
        self.extra_filters.addWidget(QLabel("ركود (يوم):"))
        self.extra_filters.addWidget(self._stagnant)
        self.set_columns(
            ["الصنف", "الفئة", "المتاح", "الحد الأدنى", "التكلفة", "القيمة", "الحالة"]
        )
        self.run()

    def run(self) -> None:
        data = self._c.reports.inventory_report(self._stagnant.value())
        rows = []
        for r in data["rows"]:
            flags = []
            if r["low"]:
                flags.append("ناقص/إعادة طلب")
            if r["stagnant"]:
                flags.append("راكد")
            rows.append([
                r["name"], r["category"], f"{r['quantity']:g}", f"{r['min_stock']:g}",
                _money(self._c, r["unit_cost"]), _money(self._c, r["value"]),
                " / ".join(flags) or "سليم",
            ])
        self.fill(rows)
        summary = (
            f"قيمة المخزون: {_money(self._c, data['total_value'])} | نواقص: "
            f"{data['low_count']} | أصناف راكدة: {data['stagnant_count']}"
        )
        self.set_totals(summary)
        self.build_html(
            ["الصنف", "الفئة", "المتاح", "الحد الأدنى", "التكلفة", "القيمة", "الحالة"],
            [[str(x) for x in row] for row in rows], summary,
        )


# ── الأقساط والمتأخرات ──────────────────────────────────────────────────
class ArrearsReportPage(ReportPage):
    def __init__(self, container: "Container"):
        super().__init__(container, "تقرير الأقساط والمتأخرات", show_dates=False)
        self.set_columns(
            ["العميل", "عدد متأخر", "الإجمالي المتأخر", "أقدم استحقاق", "أيام التأخير",
             "الفئة العمرية"]
        )
        self.run()

    def run(self) -> None:
        data = self._c.reports.arrears_report()
        rows = []
        for r in data["rows"]:
            rows.append([
                r["customer_name"], r["count"], _money(self._c, r["amount"]),
                format_iso_date(r["oldest_due"]), r["days"], r["bucket"],
            ])
        self.fill(rows)
        summary = (
            f"إجمالي المتأخرات: {_money(self._c, data['total_overdue'])} | عملاء "
            f"متأخرون: {len(data['rows'])} | أقساط مستحقة اليوم: {len(data['due_today'])}"
        )
        self.set_totals(summary)
        self.build_html(
            ["العميل", "عدد متأخر", "الإجمالي المتأخر", "أقدم استحقاق", "أيام التأخير",
             "الفئة العمرية"],
            [[str(x) for x in row] for row in rows], summary,
        )


# ── كشف حساب عميل ───────────────────────────────────────────────────────
class CustomerStatementPage(ReportPage):
    def __init__(self, container: "Container"):
        super().__init__(container, "كشف حساب عميل")
        self._customer = QComboBox()
        for cust in container.customers.list():
            self._customer.addItem(cust.name, cust.id)
        self.extra_filters.addWidget(QLabel("العميل:"))
        self.extra_filters.addWidget(self._customer)
        self.set_columns(["التاريخ", "البيان", "مدين", "دائن", "الرصيد"])
        self.run()

    def run(self) -> None:
        cid = self._customer.currentData()
        if cid is None:
            QMessageBox.information(self, "تنبيه", "لا يوجد عملاء.")
            return
        data = self._c.reports.customer_statement(cid, self.dfrom, self.dto)
        rows = [["—", "رصيد افتتاحي", "", "", _money(self._c, data["opening"])]]
        for m in data["movements"]:
            rows.append([
                format_iso_date(m["date"]), m["desc"],
                _money(self._c, m["debit"]) if m["debit"] else "",
                _money(self._c, m["credit"]) if m["credit"] else "",
                _money(self._c, m["balance"]),
            ])
        self.fill(rows)
        summary = (
            f"العميل: {self._customer.currentText()} | رصيد افتتاحي: "
            f"{_money(self._c, data['opening'])} | رصيد ختامي: "
            f"{_money(self._c, data['closing'])}"
        )
        self.set_totals(summary)
        self.build_html(
            ["التاريخ", "البيان", "مدين", "دائن", "الرصيد"],
            [[str(x) for x in row] for row in rows], summary,
        )


# ── كشف حساب مورّد ──────────────────────────────────────────────────────
class SupplierStatementPage(ReportPage):
    def __init__(self, container: "Container"):
        super().__init__(container, "كشف حساب مورّد")
        self._supplier = QComboBox()
        for sup in container.suppliers.list():
            self._supplier.addItem(sup.name, sup.id)
        self.extra_filters.addWidget(QLabel("المورّد:"))
        self.extra_filters.addWidget(self._supplier)
        self.set_columns(["التاريخ", "البيان", "مدين (دفعنا)", "دائن (علينا)", "الرصيد"])
        self.run()

    def run(self) -> None:
        sid = self._supplier.currentData()
        if sid is None:
            QMessageBox.information(self, "تنبيه", "لا يوجد موردون.")
            return
        data = self._c.reports.supplier_statement(sid, self.dfrom, self.dto)
        rows = [["—", "رصيد افتتاحي", "", "", _money(self._c, data["opening"])]]
        for m in data["movements"]:
            rows.append([
                format_iso_date(m["date"]), m["desc"],
                _money(self._c, m["debit"]) if m["debit"] else "",
                _money(self._c, m["credit"]) if m["credit"] else "",
                _money(self._c, m["balance"]),
            ])
        self.fill(rows)
        summary = (
            f"المورّد: {self._supplier.currentText()} | رصيد افتتاحي: "
            f"{_money(self._c, data['opening'])} | رصيد ختامي: "
            f"{_money(self._c, data['closing'])}"
        )
        self.set_totals(summary)
        self.build_html(
            ["التاريخ", "البيان", "مدين", "دائن", "الرصيد"],
            [[str(x) for x in row] for row in rows], summary,
        )


# ── ملخص بياني (مخططات) ─────────────────────────────────────────────────
class ChartsReportPage(Page):
    def __init__(self, container: "Container"):
        super().__init__(container.navigator, "ملخص بياني")
        self._c = container

        bar = Card()
        row = QHBoxLayout()
        bar.layout().addLayout(row)
        today = QDate.currentDate()
        self._from = QDateEdit()
        self._from.setCalendarPopup(True)
        self._from.setDate(today.addDays(-6))
        self._to = QDateEdit()
        self._to.setCalendarPopup(True)
        self._to.setDate(today)
        run = QPushButton("تحديث المخططات")
        run.clicked.connect(self.refresh)
        row.addWidget(QLabel("من"))
        row.addWidget(self._from)
        row.addWidget(QLabel("إلى"))
        row.addWidget(self._to)
        row.addWidget(run)
        row.addStretch(1)
        self.body.addWidget(bar)

        self._sales_chart = BarChart("المبيعات اليومية")
        self._items_chart = BarChart("أعلى الأصناف مبيعًا")
        self._treasury_chart = BarChart("الخزينة: قبض مقابل صرف")
        self.body.addWidget(self._sales_chart, stretch=1)
        self.body.addWidget(self._items_chart, stretch=1)
        self.body.addWidget(self._treasury_chart, stretch=1)

        self.refresh()

    def refresh(self) -> None:
        dfrom = self._from.date().toString("yyyy-MM-dd")
        dto = self._to.date().toString("yyyy-MM-dd")
        self._sales_chart.set_data(self._c.reports.chart_sales_daily(dfrom, dto))
        self._items_chart.set_data(self._c.reports.chart_top_items(dfrom, dto))
        self._treasury_chart.set_data(self._c.reports.chart_treasury(dfrom, dto))
