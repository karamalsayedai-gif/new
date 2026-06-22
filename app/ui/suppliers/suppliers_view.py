"""شاشة الموردين: بحث + جدول + إضافة/تعديل/حذف."""
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
from app.domain.entities import Supplier
from app.services.suppliers_service import SuppliersServiceError
from app.ui.components.widgets import title_label

if TYPE_CHECKING:
    from app.core.container import Container


class SuppliersView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._can_manage = container.auth.can(Permissions.SUPPLIERS_MANAGE)
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(title_label("الموردون"))
        header.addStretch(1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("بحث بالاسم أو الهاتف…")
        self._search.setFixedWidth(260)
        self._search.textChanged.connect(self.refresh)
        header.addWidget(self._search)

        add_btn = QPushButton("إضافة مورّد")
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

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["الاسم", "الهاتف", "العنوان", "الرصيد (له)"]
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
        suppliers = self._c.suppliers.list(self._search.text())
        self._table.setRowCount(len(suppliers))
        for r, sup in enumerate(suppliers):
            name_item = QTableWidgetItem(sup.name)
            name_item.setData(Qt.ItemDataRole.UserRole, sup.id)
            self._table.setItem(r, 0, name_item)
            self._table.setItem(r, 1, QTableWidgetItem(sup.phone))
            self._table.setItem(r, 2, QTableWidgetItem(sup.address))
            self._table.setItem(
                r, 3, QTableWidgetItem(format_currency(sup.balance, symbol))
            )

    def _selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _add(self) -> None:
        if _SupplierDialog(self._c, None, self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit(self) -> None:
        sid = self._selected_id()
        if sid is None:
            QMessageBox.information(self, "تنبيه", "اختر مورّدًا أولًا.")
            return
        supplier = self._c.suppliers.get(sid)
        if supplier is None:
            return
        if _SupplierDialog(self._c, supplier, self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _delete(self) -> None:
        sid = self._selected_id()
        if sid is None:
            QMessageBox.information(self, "تنبيه", "اختر مورّدًا أولًا.")
            return
        if (
            QMessageBox.question(self, "تأكيد", "حذف هذا المورّد؟")
            != QMessageBox.StandardButton.Yes
        ):
            return
        actor = self._c.auth.current_user
        try:
            self._c.suppliers.delete(sid, actor_id=actor.id if actor else None)
        except SuppliersServiceError as exc:
            QMessageBox.warning(self, "تعذّر الحذف", str(exc))
            return
        self.refresh()


class _SupplierDialog(QDialog):
    def __init__(
        self, container: "Container", supplier: Supplier | None, parent: QWidget
    ):
        super().__init__(parent)
        self._c = container
        self._supplier = supplier
        self.setWindowTitle("تعديل مورّد" if supplier else "إضافة مورّد")
        self.setMinimumWidth(380)

        form = QFormLayout(self)
        self._name = QLineEdit(supplier.name if supplier else "")
        self._phone = QLineEdit(supplier.phone if supplier else "")
        self._address = QLineEdit(supplier.address if supplier else "")

        form.addRow(QLabel("الاسم *"), self._name)
        form.addRow(QLabel("الهاتف"), self._phone)
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
            if self._supplier is None:
                self._c.suppliers.create(
                    name=self._name.text(),
                    phone=self._phone.text(),
                    address=self._address.text(),
                    actor_id=actor_id,
                )
            else:
                self._c.suppliers.update(
                    self._supplier.id,
                    name=self._name.text(),
                    phone=self._phone.text(),
                    address=self._address.text(),
                    actor_id=actor_id,
                )
        except SuppliersServiceError as exc:
            QMessageBox.warning(self, "تعذّر الحفظ", str(exc))
            return
        self.accept()
