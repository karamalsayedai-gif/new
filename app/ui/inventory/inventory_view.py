"""شاشة المخزون: بحث/تصفية + جدول مع تمييز النقص + تعريف الأصناف + حركة المخزون."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
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
from app.core.utils.formatters import format_currency, format_number
from app.domain.entities import InventoryItem
from app.domain.enums import ItemStatus, StockDirection
from app.services.inventory_service import InventoryServiceError
from app.ui.components.widgets import title_label

if TYPE_CHECKING:
    from app.core.container import Container

_STATUS_AR = {"active": "نشط", "inactive": "موقوف"}
_DIR_AR = {"in": "إضافة", "out": "صرف"}


def _fmt_time(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%Y/%m/%d %H:%M")
    except (ValueError, TypeError):
        return iso or ""


class InventoryView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._can_manage = container.auth.can(Permissions.INVENTORY_MANAGE)
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(title_label("المخزون"))
        header.addStretch(1)
        add_btn = QPushButton("صنف جديد")
        add_btn.setEnabled(self._can_manage)
        add_btn.clicked.connect(self._add)
        edit_btn = QPushButton("تعديل")
        edit_btn.setObjectName("Ghost")
        edit_btn.setEnabled(self._can_manage)
        edit_btn.clicked.connect(self._edit)
        stock_btn = QPushButton("حركة مخزون")
        stock_btn.setEnabled(self._can_manage)
        stock_btn.clicked.connect(self._adjust)
        moves_btn = QPushButton("سجل الحركة")
        moves_btn.setObjectName("Ghost")
        moves_btn.clicked.connect(self._movements)
        del_btn = QPushButton("حذف")
        del_btn.setObjectName("Danger")
        del_btn.setEnabled(self._can_manage)
        del_btn.clicked.connect(self._delete)
        for b in (add_btn, edit_btn, stock_btn, moves_btn, del_btn):
            header.addWidget(b)
        layout.addLayout(header)

        # شريط التصفية
        filters = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("بحث بالاسم أو الفئة…")
        self._search.textChanged.connect(self.refresh)
        filters.addWidget(self._search, stretch=2)

        self._category = QComboBox()
        self._category.currentIndexChanged.connect(self.refresh)
        filters.addWidget(QLabel("الفئة:"))
        filters.addWidget(self._category, stretch=1)

        self._status = QComboBox()
        self._status.addItem("الكل", "")
        self._status.addItem("نشط", ItemStatus.ACTIVE.value)
        self._status.addItem("موقوف", ItemStatus.INACTIVE.value)
        self._status.currentIndexChanged.connect(self.refresh)
        filters.addWidget(QLabel("الحالة:"))
        filters.addWidget(self._status)

        self._only_low = QCheckBox("النواقص فقط")
        self._only_low.stateChanged.connect(self.refresh)
        filters.addWidget(self._only_low)
        layout.addLayout(filters)

        self._alert = QLabel("")
        self._alert.setObjectName("Danger")
        layout.addWidget(self._alert)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["الصنف", "الفئة", "الوحدة", "المتاح", "الحد الأدنى", "سعر البيع", "الحالة"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.doubleClicked.connect(self._edit)
        layout.addWidget(self._table)

    # ── البيانات ────────────────────────────────────────────────────────
    def refresh(self) -> None:
        # تحديث قائمة الفئات مع الحفاظ على الاختيار.
        current_cat = self._category.currentData()
        self._category.blockSignals(True)
        self._category.clear()
        self._category.addItem("الكل", "")
        for cat in self._c.inventory.categories():
            self._category.addItem(cat, cat)
        idx = self._category.findData(current_cat)
        self._category.setCurrentIndex(idx if idx >= 0 else 0)
        self._category.blockSignals(False)

        symbol = self._c.settings.currency_symbol
        items = self._c.inventory.list(
            search=self._search.text(),
            category=self._category.currentData() or "",
            status=self._status.currentData() or "",
            only_low=self._only_low.isChecked(),
        )
        self._table.setRowCount(len(items))
        for r, it in enumerate(items):
            name_item = QTableWidgetItem(it.name)
            name_item.setData(Qt.ItemDataRole.UserRole, it.id)
            self._table.setItem(r, 0, name_item)
            self._table.setItem(r, 1, QTableWidgetItem(it.category))
            self._table.setItem(r, 2, QTableWidgetItem(it.unit))
            self._table.setItem(r, 3, QTableWidgetItem(format_number(it.quantity)))
            self._table.setItem(r, 4, QTableWidgetItem(format_number(it.min_stock)))
            self._table.setItem(
                r, 5, QTableWidgetItem(format_currency(it.sale_price, symbol))
            )
            self._table.setItem(
                r, 6, QTableWidgetItem(_STATUS_AR.get(it.status, it.status))
            )
            if it.is_low:
                for col in range(7):
                    cell = self._table.item(r, col)
                    if cell:
                        cell.setBackground(QColor(255, 235, 235))

        low_count = len(self._c.inventory.low_stock())
        self._alert.setText(
            f"⚠ يوجد {low_count} صنف تحت الحد الأدنى للمخزون." if low_count else ""
        )

    def _selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item else None

    # ── إجراءات ─────────────────────────────────────────────────────────
    def _add(self) -> None:
        if _ItemDialog(self._c, None, self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit(self) -> None:
        iid = self._selected_id()
        if iid is None:
            QMessageBox.information(self, "تنبيه", "اختر صنفًا أولًا.")
            return
        item = self._c.inventory.get(iid)
        if item and _ItemDialog(self._c, item, self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _adjust(self) -> None:
        iid = self._selected_id()
        if iid is None:
            QMessageBox.information(self, "تنبيه", "اختر صنفًا أولًا.")
            return
        item = self._c.inventory.get(iid)
        if item and _StockDialog(self._c, item, self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _movements(self) -> None:
        iid = self._selected_id()
        if iid is None:
            QMessageBox.information(self, "تنبيه", "اختر صنفًا أولًا.")
            return
        item = self._c.inventory.get(iid)
        if item:
            _MovementsDialog(self._c, item, self).exec()

    def _delete(self) -> None:
        iid = self._selected_id()
        if iid is None:
            QMessageBox.information(self, "تنبيه", "اختر صنفًا أولًا.")
            return
        if (
            QMessageBox.question(self, "تأكيد", "حذف هذا الصنف؟")
            != QMessageBox.StandardButton.Yes
        ):
            return
        actor = self._c.auth.current_user
        try:
            self._c.inventory.delete(iid, actor_id=actor.id if actor else None)
        except InventoryServiceError as exc:
            QMessageBox.warning(self, "تعذّر الحذف", str(exc))
            return
        self.refresh()


class _ItemDialog(QDialog):
    def __init__(
        self, container: "Container", item: InventoryItem | None, parent: QWidget
    ):
        super().__init__(parent)
        self._c = container
        self._item = item
        self.setWindowTitle("تعديل صنف" if item else "صنف جديد")
        self.setMinimumWidth(400)

        form = QFormLayout(self)
        self._name = QLineEdit(item.name if item else "")
        self._category = QLineEdit(item.category if item else "")
        self._unit = QLineEdit(item.unit if item else "قطعة")
        self._min = self._spin(item.min_stock if item else 0)
        self._cost = self._spin(item.unit_cost if item else 0)
        self._price = self._spin(item.sale_price if item else 0)
        self._status = QComboBox()
        self._status.addItem("نشط", ItemStatus.ACTIVE.value)
        self._status.addItem("موقوف", ItemStatus.INACTIVE.value)
        if item:
            i = self._status.findData(item.status)
            self._status.setCurrentIndex(i if i >= 0 else 0)

        form.addRow(QLabel("اسم الصنف *"), self._name)
        form.addRow(QLabel("الفئة"), self._category)
        form.addRow(QLabel("وحدة القياس"), self._unit)

        # الكمية الافتتاحية تُحدَّد فقط عند الإنشاء (بعدها عبر حركة المخزون).
        if item is None:
            self._qty = self._spin(0)
            form.addRow(QLabel("الكمية الافتتاحية"), self._qty)
        else:
            self._qty = None

        form.addRow(QLabel("الحد الأدنى للمخزون"), self._min)
        form.addRow(QLabel("تكلفة الشراء"), self._cost)
        form.addRow(QLabel("سعر البيع"), self._price)
        form.addRow(QLabel("الحالة"), self._status)

        buttons = QHBoxLayout()
        save = QPushButton("حفظ")
        save.clicked.connect(self._save)
        cancel = QPushButton("إلغاء")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        form.addRow(buttons)

    @staticmethod
    def _spin(value: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(0, 1_000_000_000)
        s.setDecimals(2)
        s.setValue(value)
        return s

    def _save(self) -> None:
        actor = self._c.auth.current_user
        actor_id = actor.id if actor else None
        try:
            if self._item is None:
                self._c.inventory.create(
                    name=self._name.text(),
                    category=self._category.text(),
                    unit=self._unit.text(),
                    quantity=self._qty.value() if self._qty else 0,
                    min_stock=self._min.value(),
                    unit_cost=self._cost.value(),
                    sale_price=self._price.value(),
                    status=self._status.currentData(),
                    actor_id=actor_id,
                )
            else:
                self._c.inventory.update(
                    self._item.id,
                    name=self._name.text(),
                    category=self._category.text(),
                    unit=self._unit.text(),
                    min_stock=self._min.value(),
                    unit_cost=self._cost.value(),
                    sale_price=self._price.value(),
                    status=self._status.currentData(),
                    actor_id=actor_id,
                )
        except InventoryServiceError as exc:
            QMessageBox.warning(self, "تعذّر الحفظ", str(exc))
            return
        self.accept()


class _StockDialog(QDialog):
    def __init__(self, container: "Container", item: InventoryItem, parent: QWidget):
        super().__init__(parent)
        self._c = container
        self._item = item
        self.setWindowTitle(f"حركة مخزون — {item.name}")
        self.setMinimumWidth(360)

        form = QFormLayout(self)
        form.addRow(QLabel("المتاح حاليًا"), QLabel(format_number(item.quantity)))
        self._direction = QComboBox()
        self._direction.addItem("إضافة للمخزون", StockDirection.IN.value)
        self._direction.addItem("صرف من المخزون", StockDirection.OUT.value)
        self._qty = QDoubleSpinBox()
        self._qty.setRange(0.01, 1_000_000_000)
        self._qty.setDecimals(2)
        self._reason = QLineEdit()
        form.addRow(QLabel("نوع الحركة"), self._direction)
        form.addRow(QLabel("الكمية"), self._qty)
        form.addRow(QLabel("السبب"), self._reason)

        buttons = QHBoxLayout()
        save = QPushButton("تنفيذ")
        save.clicked.connect(self._save)
        cancel = QPushButton("إلغاء")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        form.addRow(buttons)

    def _save(self) -> None:
        actor = self._c.auth.current_user
        try:
            self._c.inventory.adjust_stock(
                self._item.id,
                self._direction.currentData(),
                self._qty.value(),
                self._reason.text().strip() or None,
                actor_id=actor.id if actor else None,
            )
        except InventoryServiceError as exc:
            QMessageBox.warning(self, "تعذّر التنفيذ", str(exc))
            return
        self.accept()


class _MovementsDialog(QDialog):
    def __init__(self, container: "Container", item: InventoryItem, parent: QWidget):
        super().__init__(parent)
        self._c = container
        self.setWindowTitle(f"سجل حركة — {item.name}")
        self.setMinimumSize(520, 420)

        layout = QVBoxLayout(self)
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["التاريخ", "النوع", "الكمية", "السبب"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        rows = self._c.inventory.movements(item.id)
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(_fmt_time(row["created_at"])))
            table.setItem(
                r, 1, QTableWidgetItem(_DIR_AR.get(row["direction"], row["direction"]))
            )
            table.setItem(r, 2, QTableWidgetItem(format_number(row["quantity"])))
            table.setItem(r, 3, QTableWidgetItem(row["reason"] or ""))
        layout.addWidget(table)

        close = QPushButton("إغلاق")
        close.setObjectName("Ghost")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
