"""شاشة العملاء: بحث + جدول + إضافة/تعديل/حذف."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
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
from app.domain.entities import Customer
from app.services.customers_service import CustomersServiceError
from app.ui.components.widgets import title_label

if TYPE_CHECKING:
    from app.core.container import Container


class CustomersView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._can_manage = container.auth.can(Permissions.CUSTOMERS_MANAGE)
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(title_label("العملاء"))
        header.addStretch(1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("بحث بالاسم أو الهاتف أو الرقم القومي…")
        self._search.setFixedWidth(280)
        self._search.textChanged.connect(self.refresh)
        header.addWidget(self._search)

        add_btn = QPushButton("إضافة عميل")
        add_btn.setEnabled(self._can_manage)
        add_btn.clicked.connect(self._add)
        edit_btn = QPushButton("تعديل")
        edit_btn.setObjectName("Ghost")
        edit_btn.setEnabled(self._can_manage)
        edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("حذف")
        del_btn.setObjectName("Danger")
        del_btn.setEnabled(self._can_manage)
        del_btn.clicked.connect(self._delete)
        for b in (add_btn, edit_btn, del_btn):
            header.addWidget(b)
        layout.addLayout(header)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["الاسم", "الهاتف", "الرقم القومي", "العنوان", "الرصيد"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.doubleClicked.connect(self._edit)
        layout.addWidget(self._table)

    def refresh(self) -> None:
        symbol = self._c.settings.currency_symbol
        customers = self._c.customers.list(self._search.text())
        self._table.setRowCount(len(customers))
        for r, cust in enumerate(customers):
            name_item = QTableWidgetItem(cust.name)
            name_item.setData(Qt.ItemDataRole.UserRole, cust.id)
            self._table.setItem(r, 0, name_item)
            self._table.setItem(r, 1, QTableWidgetItem(cust.phone))
            self._table.setItem(r, 2, QTableWidgetItem(cust.national_id))
            self._table.setItem(r, 3, QTableWidgetItem(cust.address))
            self._table.setItem(
                r, 4, QTableWidgetItem(format_currency(cust.balance, symbol))
            )

    def _selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _add(self) -> None:
        if _CustomerDialog(self._c, None, self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit(self) -> None:
        cid = self._selected_id()
        if cid is None:
            QMessageBox.information(self, "تنبيه", "اختر عميلًا أولًا.")
            return
        customer = self._c.customers.get(cid)
        if customer is None:
            return
        if _CustomerDialog(self._c, customer, self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _delete(self) -> None:
        cid = self._selected_id()
        if cid is None:
            QMessageBox.information(self, "تنبيه", "اختر عميلًا أولًا.")
            return
        if (
            QMessageBox.question(self, "تأكيد", "حذف هذا العميل؟")
            != QMessageBox.StandardButton.Yes
        ):
            return
        actor = self._c.auth.current_user
        try:
            self._c.customers.delete(cid, actor_id=actor.id if actor else None)
        except CustomersServiceError as exc:
            QMessageBox.warning(self, "تعذّر الحذف", str(exc))
            return
        self.refresh()


class _CustomerDialog(QDialog):
    def __init__(
        self, container: "Container", customer: Customer | None, parent: QWidget
    ):
        super().__init__(parent)
        self._c = container
        self._customer = customer
        self.setWindowTitle("تعديل عميل" if customer else "إضافة عميل")
        self.setMinimumWidth(380)

        form = QFormLayout(self)
        self._name = QLineEdit(customer.name if customer else "")
        self._phone = QLineEdit(customer.phone if customer else "")
        self._national = QLineEdit(customer.national_id if customer else "")
        self._address = QLineEdit(customer.address if customer else "")

        form.addRow(QLabel("الاسم *"), self._name)
        form.addRow(QLabel("الهاتف"), self._phone)
        form.addRow(QLabel("الرقم القومي"), self._national)
        form.addRow(QLabel("العنوان"), self._address)

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
        actor = self._c.auth.current_user
        actor_id = actor.id if actor else None
        try:
            if self._customer is None:
                self._c.customers.create(
                    name=self._name.text(),
                    phone=self._phone.text(),
                    national_id=self._national.text(),
                    address=self._address.text(),
                    actor_id=actor_id,
                )
            else:
                self._c.customers.update(
                    self._customer.id,
                    name=self._name.text(),
                    phone=self._phone.text(),
                    national_id=self._national.text(),
                    address=self._address.text(),
                    actor_id=actor_id,
                )
        except CustomersServiceError as exc:
            QMessageBox.warning(self, "تعذّر الحفظ", str(exc))
            return
        self.accept()
