"""شاشة الخزينة الرئيسية: رصيد الصندوق وحركات اليوم وتسجيل قبض/صرف."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.constants.permissions import Permissions
from app.core.utils.formatters import format_currency
from app.domain.enums import DayStatus, TreasuryCategory, TreasuryDirection
from app.services.treasury_service import TreasuryError
from app.ui.components.widgets import StatCard, title_label

if TYPE_CHECKING:
    from app.core.container import Container

_DIRECTION_AR = {"in": "قبض", "out": "صرف"}
_CATEGORY_AR = {
    "income": "إيراد",
    "expense": "مصروف",
    "manual": "تسوية",
    "sale": "بيع",
    "installment": "قسط",
    "purchase": "شراء",
}


def _fmt_time(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%Y/%m/%d %H:%M")
    except (ValueError, TypeError):
        return iso or ""


class TreasuryView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.addWidget(title_label("الخزينة الرئيسية"))
        header.addStretch(1)
        can_manage = self._c.auth.can(Permissions.TREASURY_MANAGE)
        self._in_btn = QPushButton("قبض (إيداع)")
        self._in_btn.clicked.connect(lambda: self._add(TreasuryDirection.IN.value))
        self._out_btn = QPushButton("صرف")
        self._out_btn.setObjectName("Danger")
        self._out_btn.clicked.connect(lambda: self._add(TreasuryDirection.OUT.value))
        for btn in (self._in_btn, self._out_btn):
            btn.setEnabled(can_manage)
            header.addWidget(btn)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(16)
        self._balance_card = StatCard("رصيد الصندوق")
        self._in_card = StatCard("إجمالي القبض اليوم")
        self._out_card = StatCard("إجمالي الصرف اليوم")
        self._net_card = StatCard("صافي اليوم")
        grid.addWidget(self._balance_card, 0, 0)
        grid.addWidget(self._in_card, 0, 1)
        grid.addWidget(self._out_card, 0, 2)
        grid.addWidget(self._net_card, 0, 3)
        layout.addLayout(grid)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["التاريخ", "النوع", "التصنيف", "المبلغ", "ملاحظات"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        layout.addWidget(self._table)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self._delete_btn = QPushButton("حذف الحركة المحددة")
        self._delete_btn.setObjectName("Ghost")
        self._delete_btn.setEnabled(can_manage)
        self._delete_btn.clicked.connect(self._delete_selected)
        footer.addWidget(self._delete_btn)
        layout.addLayout(footer)

    # ── البيانات ────────────────────────────────────────────────────────
    def refresh(self) -> None:
        symbol = self._c.settings.currency_symbol
        day = self._c.day_closing.get_or_open_today()
        summary = self._c.treasury.day_summary(day.id)

        self._balance_card.set_value(
            format_currency(self._c.treasury.current_balance(), symbol)
        )
        self._in_card.set_value(format_currency(summary["in"], symbol))
        self._out_card.set_value(format_currency(summary["out"], symbol))
        self._net_card.set_value(format_currency(summary["net"], symbol))

        # منع التسجيل عند إقفال اليوم.
        day_open = day.status == DayStatus.OPEN.value
        can_manage = self._c.auth.can(Permissions.TREASURY_MANAGE)
        self._in_btn.setEnabled(can_manage and day_open)
        self._out_btn.setEnabled(can_manage and day_open)
        self._delete_btn.setEnabled(can_manage and day_open)

        rows = self._c.treasury.list_for_day(day.id)
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            entry_id = row["id"]
            date_item = QTableWidgetItem(_fmt_time(row["date"]))
            date_item.setData(Qt.ItemDataRole.UserRole, entry_id)
            self._table.setItem(r, 0, date_item)
            self._table.setItem(
                r, 1, QTableWidgetItem(_DIRECTION_AR.get(row["direction"], row["direction"]))
            )
            self._table.setItem(
                r, 2, QTableWidgetItem(_CATEGORY_AR.get(row["category"], row["category"]))
            )
            self._table.setItem(
                r, 3, QTableWidgetItem(format_currency(row["amount"], symbol))
            )
            self._table.setItem(r, 4, QTableWidgetItem(row["notes"] or ""))

    # ── إجراءات ─────────────────────────────────────────────────────────
    def _add(self, direction: str) -> None:
        dialog = _EntryDialog(self._c, direction, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _delete_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "تنبيه", "اختر حركة أولًا.")
            return
        item = self._table.item(row, 0)
        entry_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if entry_id is None:
            return
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


class _EntryDialog(QDialog):
    def __init__(self, container: "Container", direction: str, parent: QWidget):
        super().__init__(parent)
        self._c = container
        self._direction = direction
        self.setWindowTitle(_DIRECTION_AR.get(direction, "حركة") + " من الخزينة")
        self.setMinimumWidth(360)

        form = QFormLayout(self)
        self._amount = QDoubleSpinBox()
        self._amount.setRange(0.01, 1_000_000_000)
        self._amount.setDecimals(2)

        self._category = QComboBox()
        if direction == TreasuryDirection.IN.value:
            self._category.addItem("إيراد", TreasuryCategory.INCOME.value)
        else:
            self._category.addItem("مصروف", TreasuryCategory.EXPENSE.value)
        self._category.addItem("تسوية", TreasuryCategory.MANUAL.value)

        self._notes = QLineEdit()

        form.addRow(QLabel("المبلغ"), self._amount)
        form.addRow(QLabel("التصنيف"), self._category)
        form.addRow(QLabel("ملاحظات"), self._notes)

        buttons = QHBoxLayout()
        save = QPushButton("حفظ")
        save.clicked.connect(self._save)
        cancel = QPushButton("إلغاء")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        form.addRow(buttons)

    def _save(self) -> None:
        user = self._c.auth.current_user
        try:
            self._c.treasury.add_entry(
                direction=self._direction,
                category=self._category.currentData(),
                amount=self._amount.value(),
                user_id=user.id if user else None,
                notes=self._notes.text().strip() or None,
            )
        except TreasuryError as exc:
            QMessageBox.warning(self, "تعذّر الحفظ", str(exc))
            return
        self.accept()
