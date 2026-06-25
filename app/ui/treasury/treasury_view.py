"""شاشة الخزينة الرئيسية: رصيد الصندوق وحركات اليوم وتسجيل قبض/صرف."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
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
from app.ui.components.flow_layout import toolbar
from app.ui.components.page import Page
from app.ui.components.widgets import (
    Card,
    StatCard,
    heading_label,
    muted_label,
    title_label,
    treasury_combo,
)

if TYPE_CHECKING:
    from app.core.container import Container

_DIRECTION_AR = {"in": "إيداع", "out": "سحب"}
_CATEGORY_AR = {
    "income": "إيراد",
    "expense": "مصروف",
    "manual": "تسوية",
    "sale": "بيع نقدي",
    "installment": "قسط",
    "purchase": "شراء",
    "return": "مرتجع",
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

        title_row = QHBoxLayout()
        title_row.addWidget(title_label("الخزينة"))
        title_row.addStretch(1)
        layout.addLayout(title_row)

        can_manage = self._c.auth.can(Permissions.TREASURY_MANAGE)
        # اختيار الخزنة المعروضة.
        self._account = QComboBox()
        self._account.setMinimumWidth(200)
        self._reload_accounts()
        self._account.currentIndexChanged.connect(self.refresh)
        self._in_btn = QPushButton("إيداع")
        self._in_btn.setObjectName("Success")
        self._in_btn.clicked.connect(lambda: self._add(TreasuryDirection.IN.value))
        self._out_btn = QPushButton("سحب")
        self._out_btn.setObjectName("Danger")
        self._out_btn.clicked.connect(lambda: self._add(TreasuryDirection.OUT.value))
        manage_btn = QPushButton("إدارة الخزائن")
        manage_btn.setObjectName("Ghost")
        manage_btn.clicked.connect(self._manage_accounts)
        for btn in (self._in_btn, self._out_btn):
            btn.setEnabled(can_manage)
        layout.addWidget(
            toolbar([QLabel("الخزنة:"), self._account, self._in_btn,
                     self._out_btn, manage_btn])
        )

        grid = QGridLayout()
        grid.setSpacing(16)
        self._balance_card = StatCard("رصيد الصندوق", icon="💰", tone="#4E63C7")
        self._in_card = StatCard("إجمالي القبض اليوم", icon="⬆️", tone="#2E9E5B")
        self._out_card = StatCard("إجمالي الصرف اليوم", icon="⬇️", tone="#E0584F")
        self._net_card = StatCard("صافي اليوم", icon="📊", tone="#D9A441")
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

    # ── الخزائن ─────────────────────────────────────────────────────────
    def _reload_accounts(self) -> None:
        prev = self._current_account_id()
        self._account.blockSignals(True)
        self._account.clear()
        for acc in self._c.treasury.active_accounts():
            self._account.addItem(acc["name"], acc["id"])
            if acc["id"] == prev:
                self._account.setCurrentIndex(self._account.count() - 1)
        self._account.blockSignals(False)

    def _current_account_id(self) -> int | None:
        return self._account.currentData() if self._account.count() else None

    def _manage_accounts(self) -> None:
        self._c.navigator.push(TreasuriesManagePage(self._c))

    # ── البيانات ────────────────────────────────────────────────────────
    def refresh(self) -> None:
        self._reload_accounts()  # التقاط أي خزائن جديدة أُضيفت.
        symbol = self._c.settings.currency_symbol
        day = self._c.day_closing.get_or_open_today()
        acc_id = self._current_account_id()
        summary = self._c.treasury.day_summary(day.id, acc_id)

        self._balance_card.set_value(
            format_currency(self._c.treasury.current_balance(acc_id), symbol)
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

        rows = self._c.treasury.list_for_day(day.id, acc_id)
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
            is_in = row["direction"] == TreasuryDirection.IN.value
            amount_item = QTableWidgetItem(
                ("+ " if is_in else "− ") + format_currency(row["amount"], symbol)
            )
            amount_item.setForeground(
                QColor("#1E8A4C" if is_in else "#D23A2E")
            )
            font = amount_item.font()
            font.setBold(True)
            amount_item.setFont(font)
            self._table.setItem(r, 3, amount_item)
            self._table.setItem(r, 4, QTableWidgetItem(row["notes"] or ""))

    # ── إجراءات ─────────────────────────────────────────────────────────
    def _add(self, direction: str) -> None:
        self._c.navigator.push(
            TreasuryEntryPage(self._c, direction, self._current_account_id())
        )

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


class TreasuryEntryPage(Page):
    def __init__(
        self, container: "Container", direction: str, account_id: int | None = None
    ):
        super().__init__(
            container.navigator, _DIRECTION_AR.get(direction, "حركة") + " من الخزينة"
        )
        self._c = container
        self._direction = direction

        card = Card()
        form = QFormLayout()
        card.layout().addLayout(form)
        self._amount = QDoubleSpinBox()
        self._amount.setRange(0.01, 1_000_000_000)
        self._amount.setDecimals(2)

        self._account = treasury_combo(container, current_id=account_id)

        self._category = QComboBox()
        if direction == TreasuryDirection.IN.value:
            self._category.addItem("إيراد", TreasuryCategory.INCOME.value)
        else:
            self._category.addItem("مصروف", TreasuryCategory.EXPENSE.value)
        self._category.addItem("تسوية", TreasuryCategory.MANUAL.value)

        self._notes = QLineEdit()
        form.addRow(QLabel("الخزنة"), self._account)
        form.addRow(QLabel("المبلغ"), self._amount)
        form.addRow(QLabel("التصنيف"), self._category)
        form.addRow(QLabel("ملاحظات"), self._notes)

        buttons = QHBoxLayout()
        save = QPushButton("حفظ")
        save.clicked.connect(self._save)
        cancel = QPushButton("إلغاء")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.go_back)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        card.layout().addLayout(buttons)

        self.body.addWidget(card)
        self.body.addStretch(1)

    def _save(self) -> None:
        user = self._c.auth.current_user
        try:
            self._c.treasury.add_entry(
                direction=self._direction,
                category=self._category.currentData(),
                amount=self._amount.value(),
                user_id=user.id if user else None,
                notes=self._notes.text().strip() or None,
                treasury_id=self._account.currentData(),
            )
        except TreasuryError as exc:
            QMessageBox.warning(self, "تعذّر الحفظ", str(exc))
            return
        self.go_back()


_KIND_AR = {"cash": "نقدي", "wallet": "محفظة إلكترونية", "bank": "بنك"}


# ── إدارة الخزائن (إضافة/تعديل/تفعيل) ───────────────────────────────────
class TreasuriesManagePage(Page):
    def __init__(self, container: "Container"):
        super().__init__(container.navigator, "إدارة الخزائن")
        self._c = container
        self._can = container.auth.can(Permissions.TREASURY_MANAGE)

        self.body.addWidget(
            muted_label("أضف خزائن متعددة (محفظة فودافون كاش، بنك…) واستخدمها في الفواتير.")
        )

        add_card = Card()
        add_card.layout().addWidget(heading_label("إضافة خزنة جديدة"))
        row = QHBoxLayout()
        self._name = QLineEdit()
        self._name.setPlaceholderText("اسم الخزنة (مثال: فودافون كاش)")
        self._kind = QComboBox()
        for key, lbl in _KIND_AR.items():
            self._kind.addItem(lbl, key)
        add_btn = QPushButton("إضافة")
        add_btn.setEnabled(self._can)
        add_btn.clicked.connect(self._add)
        row.addWidget(QLabel("الاسم"))
        row.addWidget(self._name, stretch=1)
        row.addWidget(QLabel("النوع"))
        row.addWidget(self._kind)
        row.addWidget(add_btn)
        add_card.layout().addLayout(row)
        self.body.addWidget(add_card)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["الخزنة", "النوع", "الرصيد", "الحالة", "إجراءات"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.body.addWidget(self._table, stretch=1)
        self.refresh()

    def refresh(self) -> None:
        symbol = self._c.settings.currency_symbol
        accounts = self._c.treasury.account_balances()
        self._table.setRowCount(len(accounts))
        for r, acc in enumerate(accounts):
            name = acc["name"] + ("  (افتراضية)" if acc["is_default"] else "")
            self._table.setItem(r, 0, QTableWidgetItem(name))
            self._table.setItem(r, 1, QTableWidgetItem(_KIND_AR.get(acc["kind"], acc["kind"])))
            self._table.setItem(r, 2, QTableWidgetItem(format_currency(acc["balance"], symbol)))
            self._table.setItem(
                r, 3, QTableWidgetItem("نشطة" if acc["is_active"] else "موقوفة")
            )
            holder = QWidget()
            hl = QHBoxLayout(holder)
            hl.setContentsMargins(0, 0, 0, 0)
            if not acc["is_default"]:
                toggle = QPushButton("إيقاف" if acc["is_active"] else "تفعيل")
                toggle.setObjectName("Ghost")
                toggle.setEnabled(self._can)
                toggle.clicked.connect(
                    lambda _c, a=acc: self._toggle(a["id"], not a["is_active"])
                )
                hl.addWidget(toggle)
            hl.addStretch(1)
            self._table.setCellWidget(r, 4, holder)

    def _add(self) -> None:
        user = self._c.auth.current_user
        try:
            self._c.treasury.create_account(
                self._name.text(), self._kind.currentData(),
                user.id if user else None,
            )
        except TreasuryError as exc:
            QMessageBox.warning(self, "تعذّر الإضافة", str(exc))
            return
        self._name.clear()
        self.refresh()

    def _toggle(self, treasury_id: int, active: bool) -> None:
        try:
            self._c.treasury.set_account_active(treasury_id, active)
        except TreasuryError as exc:
            QMessageBox.warning(self, "تعذّر", str(exc))
            return
        self.refresh()
