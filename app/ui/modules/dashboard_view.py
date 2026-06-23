"""لوحة التحكم: مؤشرات أداء + إجراءات سريعة + أحدث المبيعات."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.constants.permissions import Permissions
from app.core.utils.formatters import format_currency, format_iso_date
from app.domain.enums import DayStatus
from app.ui.components.widgets import (
    StatCard,
    heading_label,
    muted_label,
    scroll_area,
    title_label,
)

if TYPE_CHECKING:
    from app.core.container import Container


class DashboardView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._cards: dict[str, StatCard] = {}
        self._build()
        self.refresh()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 18, 24, 20)
        layout.setSpacing(16)
        outer.addWidget(scroll_area(content), stretch=1)

        user = self._c.auth.current_user
        name = user.full_name if user else ""
        layout.addWidget(title_label(f"لوحة التحكم — أهلًا {name}"))
        layout.addWidget(muted_label(self._c.settings.showroom_name))

        grid = QGridLayout()
        grid.setSpacing(14)
        specs = [
            ("balance", "رصيد الصندوق"), ("sales_today", "مبيعات اليوم"),
            ("collections", "تحصيلات اليوم"), ("day", "حالة اليوم"),
            ("customers", "عدد العملاء"), ("low", "أصناف ناقصة"),
            ("overdue", "إجمالي المتأخرات"), ("expected", "النقد المتوقع"),
        ]
        for i, (key, label) in enumerate(specs):
            card = StatCard(label)
            self._cards[key] = card
            grid.addWidget(card, i // 4, i % 4)
        layout.addLayout(grid)

        # إجراءات سريعة (حسب الصلاحيات)
        actions = QHBoxLayout()
        actions.addWidget(heading_label("إجراءات سريعة"))
        actions.addSpacing(12)
        if self._c.auth.can(Permissions.SALES_CASH_CREATE):
            actions.addWidget(self._action("🧾  بيع جديد", self._new_sale))
        if self._c.auth.can(Permissions.PURCHASES_MANAGE):
            actions.addWidget(self._action("🛒  فاتورة شراء", self._new_purchase))
        if self._c.auth.can(Permissions.CUSTOMERS_MANAGE):
            actions.addWidget(self._action("👤  عميل جديد", self._new_customer))
        actions.addStretch(1)
        layout.addLayout(actions)

        layout.addWidget(heading_label("أحدث المبيعات"))
        self._recent = QTableWidget(0, 5)
        self._recent.setHorizontalHeaderLabels(
            ["رقم الفاتورة", "العميل", "التاريخ", "الإجمالي", "الحالة"]
        )
        self._recent.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._recent.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._recent.setAlternatingRowColors(True)
        layout.addWidget(self._recent, stretch=1)

    def _action(self, text: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.clicked.connect(slot)
        return btn

    # ── البيانات ────────────────────────────────────────────────────────
    def refresh(self) -> None:
        c = self._c
        symbol = c.settings.currency_symbol
        today = c.installments.today_key()
        day = c.day_closing.get_or_open_today()
        expected = c.day_closing.compute_expected_cash(day)
        sales_today = c.reports.sales_report(today, today)["totals"]
        treasury_today = c.reports.treasury_report(today, today)["totals"]
        arrears = c.reports.arrears_report()

        self._cards["balance"].set_value(format_currency(c.treasury.current_balance(), symbol))
        self._cards["sales_today"].set_value(
            f"{format_currency(sales_today['total'], symbol)}  ({sales_today['count']})"
        )
        self._cards["collections"].set_value(
            format_currency(treasury_today["total_in"], symbol)
        )
        self._cards["day"].set_value(
            "مفتوح" if day.status == DayStatus.OPEN.value else "مُقفل"
        )
        self._cards["customers"].set_value(str(c.customers.count()))
        self._cards["low"].set_value(str(len(c.inventory.low_stock())))
        self._cards["overdue"].set_value(
            format_currency(arrears["total_overdue"], symbol)
        )
        self._cards["expected"].set_value(format_currency(expected, symbol))

        recent = c.sales.list("")[:8]
        self._recent.setRowCount(len(recent))
        for r, s in enumerate(recent):
            self._recent.setItem(r, 0, QTableWidgetItem(s.display_no))
            self._recent.setItem(r, 1, QTableWidgetItem(s.customer_name or "نقدي"))
            self._recent.setItem(r, 2, QTableWidgetItem(format_iso_date(s.date)))
            self._recent.setItem(r, 3, QTableWidgetItem(format_currency(s.total, symbol)))
            self._recent.setItem(r, 4, QTableWidgetItem(s.payment_status))

    # ── إجراءات سريعة ───────────────────────────────────────────────────
    def _new_sale(self) -> None:
        from app.ui.sales.sales_view import SaleFormPage
        self._c.navigator.push(SaleFormPage(self._c))

    def _new_purchase(self) -> None:
        from app.ui.purchases.purchases_view import PurchaseFormPage
        self._c.navigator.push(PurchaseFormPage(self._c))

    def _new_customer(self) -> None:
        from app.ui.customers.customers_view import CustomerFormPage
        self._c.navigator.push(CustomerFormPage(self._c, None))
