"""شاشة المصروفات والإيرادات المستقلة (كاملة).

تعرض حركات الإيراد/المصروف ضمن نطاق تاريخ مع إجماليات، وتعيد استخدام شاشة
حركة الخزينة لإضافة قبض إيراد / صرف مصروف. تحترم قفل اليوم والصلاحيات.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.constants.permissions import Permissions
from app.core.utils.formatters import format_currency, format_iso_date
from app.domain.enums import TreasuryDirection
from app.services.treasury_service import TreasuryError
from app.ui.components.widgets import heading_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container

_CAT_AR = {"income": "إيراد", "expense": "مصروف"}


class ExpensesView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._can = container.auth.can(Permissions.EXPENSES_MANAGE)
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 26)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(title_label("المصروفات والإيرادات"))
        header.addStretch(1)
        inc = QPushButton("قبض إيراد")
        inc.setEnabled(self._can)
        inc.clicked.connect(lambda: self._add(TreasuryDirection.IN.value))
        exp = QPushButton("صرف مصروف")
        exp.setObjectName("Danger")
        exp.setEnabled(self._can)
        exp.clicked.connect(lambda: self._add(TreasuryDirection.OUT.value))
        header.addWidget(inc)
        header.addWidget(exp)
        layout.addLayout(header)

        filt = QHBoxLayout()
        today = QDate.currentDate()
        self._from = QDateEdit()
        self._from.setCalendarPopup(True)
        self._from.setDate(QDate(today.year(), today.month(), 1))
        self._to = QDateEdit()
        self._to.setCalendarPopup(True)
        self._to.setDate(today)
        run = QPushButton("عرض")
        run.clicked.connect(self.refresh)
        filt.addWidget(QLabel("من"))
        filt.addWidget(self._from)
        filt.addWidget(QLabel("إلى"))
        filt.addWidget(self._to)
        filt.addWidget(run)
        filt.addStretch(1)
        self._del = QPushButton("حذف المحدد")
        self._del.setObjectName("Ghost")
        self._del.setEnabled(self._can)
        self._del.clicked.connect(self._delete)
        filt.addWidget(self._del)
        layout.addLayout(filt)

        self._totals = heading_label("")
        layout.addWidget(self._totals)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["التاريخ", "النوع", "المبلغ", "ملاحظات", "المستخدم"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._table, stretch=1)

    def refresh(self) -> None:
        symbol = self._c.settings.currency_symbol
        dfrom = self._from.date().toString("yyyy-MM-dd")
        dto = self._to.date().toString("yyyy-MM-dd")
        rows = self._c.treasury_repo.list_income_expense(dfrom, dto)
        income = sum(r["amount"] or 0 for r in rows if r["category"] == "income")
        expense = sum(r["amount"] or 0 for r in rows if r["category"] == "expense")
        self._totals.setText(
            f"إجمالي الإيرادات: {format_currency(income, symbol)}  |  "
            f"إجمالي المصروفات: {format_currency(expense, symbol)}  |  "
            f"الصافي: {format_currency(income - expense, symbol)}"
        )
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            date_item = QTableWidgetItem(format_iso_date((row["date"] or "")[:10]))
            date_item.setData(Qt.ItemDataRole.UserRole, row["id"])
            self._table.setItem(r, 0, date_item)
            self._table.setItem(
                r, 1, QTableWidgetItem(_CAT_AR.get(row["category"], row["category"]))
            )
            self._table.setItem(
                r, 2, QTableWidgetItem(format_currency(row["amount"] or 0, symbol))
            )
            self._table.setItem(r, 3, QTableWidgetItem(row["notes"] or ""))
            self._table.setItem(r, 4, QTableWidgetItem(row["username"] or ""))

    def _add(self, direction: str) -> None:
        from app.ui.treasury.treasury_view import TreasuryEntryPage
        self._c.navigator.push(TreasuryEntryPage(self._c, direction))

    def _delete(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "تنبيه", "اختر حركة أولًا.")
            return
        entry_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if (
            QMessageBox.question(self, "تأكيد", "حذف هذه الحركة؟")
            != QMessageBox.StandardButton.Yes
        ):
            return
        user = self._c.auth.current_user
        try:
            self._c.treasury.delete_entry(int(entry_id), user.id if user else None)
        except TreasuryError as exc:
            QMessageBox.warning(self, "تعذّر الحذف", str(exc))
            return
        self.refresh()
