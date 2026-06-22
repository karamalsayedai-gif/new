"""وحدة المشتريات — صفحات كاملة:

- ``PurchasesView``: قائمة فواتير الشراء (جذر الوحدة).
- ``PurchaseFormPage``: إنشاء فاتورة شراء وترحيلها (صفحة كاملة).
- ``PurchaseDetailPage``: تفاصيل الفاتورة + طباعة (صفحة كاملة).

الترحيل يربط: المخزون (دخول) + الخزينة (صرف المدفوع) + رصيد المورّد + التدقيق،
ويُمنع على يوم مُقفل.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
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
from app.core.utils.formatters import format_currency, format_iso_date
from app.services.purchases_service import PurchasesServiceError
from app.ui.components.page import Page
from app.ui.components.printing import print_html
from app.ui.components.widgets import Card, StatCard, heading_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container


# ── قائمة المشتريات (جذر الوحدة) ────────────────────────────────────────
class PurchasesView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._can_manage = container.auth.can(Permissions.PURCHASES_MANAGE)
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 26)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(title_label("المشتريات"))
        header.addStretch(1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("بحث باسم المورّد…")
        self._search.setFixedWidth(240)
        self._search.textChanged.connect(self.refresh)
        header.addWidget(self._search)

        new_btn = QPushButton("فاتورة شراء جديدة")
        new_btn.setEnabled(self._can_manage)
        new_btn.clicked.connect(self._new)
        open_btn = QPushButton("عرض الفاتورة")
        open_btn.clicked.connect(self._open)
        del_btn = QPushButton("حذف")
        del_btn.setObjectName("Danger")
        del_btn.setEnabled(self._can_manage)
        del_btn.clicked.connect(self._delete)
        for b in (new_btn, open_btn, del_btn):
            header.addWidget(b)
        layout.addLayout(header)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["#", "المورّد", "التاريخ", "الإجمالي", "المدفوع", "المتبقّي"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.doubleClicked.connect(self._open)
        layout.addWidget(self._table)

    def refresh(self) -> None:
        symbol = self._c.settings.currency_symbol
        purchases = self._c.purchases.list(self._search.text())
        self._table.setRowCount(len(purchases))
        for r, p in enumerate(purchases):
            id_item = QTableWidgetItem(p.display_no)
            id_item.setData(Qt.ItemDataRole.UserRole, p.id)
            self._table.setItem(r, 0, id_item)
            self._table.setItem(r, 1, QTableWidgetItem(p.supplier_name))
            self._table.setItem(r, 2, QTableWidgetItem(format_iso_date(p.date)))
            self._table.setItem(r, 3, QTableWidgetItem(format_currency(p.total, symbol)))
            self._table.setItem(r, 4, QTableWidgetItem(format_currency(p.paid, symbol)))
            self._table.setItem(
                r, 5, QTableWidgetItem(format_currency(p.remaining, symbol))
            )

    def _selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _new(self) -> None:
        self._c.navigator.push(PurchaseFormPage(self._c))

    def _open(self) -> None:
        pid = self._selected_id()
        if pid is None:
            QMessageBox.information(self, "تنبيه", "اختر فاتورة أولًا.")
            return
        self._c.navigator.push(PurchaseDetailPage(self._c, pid))

    def _delete(self) -> None:
        pid = self._selected_id()
        if pid is None:
            QMessageBox.information(self, "تنبيه", "اختر فاتورة أولًا.")
            return
        if (
            QMessageBox.question(
                self, "تأكيد",
                "حذف الفاتورة سيعكس المخزون والخزينة ورصيد المورّد. متابعة؟",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        actor = self._c.auth.current_user
        try:
            self._c.purchases.delete_purchase(pid, actor_id=actor.id if actor else None)
        except PurchasesServiceError as exc:
            QMessageBox.warning(self, "تعذّر الحذف", str(exc))
            return
        self.refresh()


# ── فاتورة شراء جديدة (صفحة كاملة) ──────────────────────────────────────
class PurchaseFormPage(Page):
    def __init__(self, container: "Container"):
        super().__init__(container.navigator, "فاتورة شراء جديدة")
        self._c = container
        self._lines: list[dict] = []

        # بيانات الفاتورة
        head = Card()
        form = QFormLayout()
        head.layout().addLayout(form)
        self._supplier = QComboBox()
        for sup in self._c.suppliers.list():
            self._supplier.addItem(sup.name, sup.id)
        self._notes = QLineEdit()
        form.addRow(QLabel("المورّد *"), self._supplier)
        form.addRow(QLabel("ملاحظات"), self._notes)
        self.body.addWidget(head)

        # بنّاء البنود
        builder = Card()
        builder.layout().addWidget(heading_label("بنود الفاتورة"))
        line_row = QHBoxLayout()
        self._item = QComboBox()
        self._items_by_id: dict[int, object] = {}
        for it in self._c.inventory.list(status="active"):
            self._item.addItem(f"{it.name} ({it.unit})", it.id)
            self._items_by_id[it.id] = it
        self._item.currentIndexChanged.connect(self._prefill_cost)
        self._qty = QDoubleSpinBox()
        self._qty.setRange(0.01, 1_000_000_000)
        self._qty.setDecimals(2)
        self._qty.setValue(1)
        self._cost = QDoubleSpinBox()
        self._cost.setRange(0, 1_000_000_000)
        self._cost.setDecimals(2)
        add_line = QPushButton("إضافة بند")
        add_line.clicked.connect(self._add_line)
        for w in (
            QLabel("الصنف"), self._item, QLabel("الكمية"), self._qty,
            QLabel("التكلفة"), self._cost, add_line,
        ):
            line_row.addWidget(w)
        builder.layout().addLayout(line_row)

        self._lines_table = QTableWidget(0, 5)
        self._lines_table.setHorizontalHeaderLabels(
            ["الصنف", "الكمية", "التكلفة", "الإجمالي", ""]
        )
        self._lines_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._lines_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        builder.layout().addWidget(self._lines_table)
        self.body.addWidget(builder, stretch=1)

        # الإجمالي والدفع
        footer = Card()
        fform = QFormLayout()
        footer.layout().addLayout(fform)
        self._total_lbl = QLabel("0")
        self._total_lbl.setObjectName("Heading")
        self._paid = QDoubleSpinBox()
        self._paid.setRange(0, 1_000_000_000)
        self._paid.setDecimals(2)
        fform.addRow(QLabel("إجمالي الفاتورة"), self._total_lbl)
        fform.addRow(QLabel("المدفوع الآن (نقدًا)"), self._paid)
        save = QPushButton("حفظ وترحيل")
        save.setEnabled(self._c.auth.can(Permissions.PURCHASES_MANAGE))
        save.clicked.connect(self._save)
        footer.layout().addWidget(save)
        self.body.addWidget(footer)

        self._prefill_cost()

    def _prefill_cost(self) -> None:
        item_id = self._item.currentData()
        item = self._items_by_id.get(item_id) if item_id is not None else None
        if item is not None:
            self._cost.setValue(item.unit_cost)

    def _add_line(self) -> None:
        item_id = self._item.currentData()
        if item_id is None:
            QMessageBox.information(self, "تنبيه", "لا توجد أصناف. أضف أصنافًا أولًا.")
            return
        item = self._items_by_id[item_id]
        line = {
            "item_id": item_id,
            "description": item.name,
            "quantity": self._qty.value(),
            "unit_cost": self._cost.value(),
        }
        self._lines.append(line)
        self._rebuild_lines()

    def _rebuild_lines(self) -> None:
        symbol = self._c.settings.currency_symbol
        self._lines_table.setRowCount(len(self._lines))
        for r, ln in enumerate(self._lines):
            total = ln["quantity"] * ln["unit_cost"]
            self._lines_table.setItem(r, 0, QTableWidgetItem(ln["description"]))
            self._lines_table.setItem(r, 1, QTableWidgetItem(str(ln["quantity"])))
            self._lines_table.setItem(
                r, 2, QTableWidgetItem(format_currency(ln["unit_cost"], symbol))
            )
            self._lines_table.setItem(
                r, 3, QTableWidgetItem(format_currency(total, symbol))
            )
            remove = QPushButton("حذف")
            remove.clicked.connect(lambda _c, i=r: self._remove_line(i))
            self._lines_table.setCellWidget(r, 4, remove)
        grand = sum(ln["quantity"] * ln["unit_cost"] for ln in self._lines)
        self._total_lbl.setText(format_currency(grand, symbol))

    def _remove_line(self, index: int) -> None:
        if 0 <= index < len(self._lines):
            self._lines.pop(index)
            self._rebuild_lines()

    def _save(self) -> None:
        actor = self._c.auth.current_user
        try:
            self._c.purchases.create_purchase(
                supplier_id=self._supplier.currentData(),
                lines=self._lines,
                paid=self._paid.value(),
                notes=self._notes.text().strip() or None,
                actor_id=actor.id if actor else None,
            )
        except PurchasesServiceError as exc:
            QMessageBox.warning(self, "تعذّر الترحيل", str(exc))
            return
        QMessageBox.information(self, "تم", "تم ترحيل فاتورة الشراء.")
        self.go_back()


# ── تفاصيل فاتورة الشراء (صفحة كاملة) ───────────────────────────────────
class PurchaseDetailPage(Page):
    def __init__(self, container: "Container", purchase_id: int):
        super().__init__(container.navigator, "تفاصيل فاتورة الشراء")
        self._c = container
        self._purchase_id = purchase_id

        printb = QPushButton("طباعة")
        printb.clicked.connect(self._print)
        self.add_action(printb)

        self._stats = QHBoxLayout()
        self.body.addLayout(self._stats)
        self._info = Card()
        self.body.addWidget(self._info)
        self._items_table = QTableWidget(0, 4)
        self._items_table.setHorizontalHeaderLabels(
            ["الصنف", "الكمية", "التكلفة", "الإجمالي"]
        )
        self._items_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.body.addWidget(self._items_table, stretch=1)

        self.refresh()

    def refresh(self) -> None:
        purchase = self._c.purchases.get(self._purchase_id)
        if purchase is None:
            self.go_back()
            return
        symbol = self._c.settings.currency_symbol
        self.set_title(f"فاتورة شراء {purchase.display_no} — {purchase.supplier_name}")

        while self._stats.count():
            item = self._stats.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._stats.addWidget(StatCard("الإجمالي", format_currency(purchase.total, symbol)))
        self._stats.addWidget(StatCard("المدفوع", format_currency(purchase.paid, symbol)))
        self._stats.addWidget(
            StatCard("المتبقّي", format_currency(purchase.remaining, symbol))
        )

        lay = self._info.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        lay.addWidget(heading_label("بيانات الفاتورة"))
        lay.addWidget(QLabel(f"المورّد: {purchase.supplier_name}"))
        lay.addWidget(QLabel(f"التاريخ: {format_iso_date(purchase.date)}"))
        lay.addWidget(QLabel(f"ملاحظات: {purchase.notes or '—'}"))

        items = self._c.purchases.items(self._purchase_id)
        self._items_table.setRowCount(len(items))
        for r, it in enumerate(items):
            self._items_table.setItem(r, 0, QTableWidgetItem(it.description))
            self._items_table.setItem(r, 1, QTableWidgetItem(str(it.quantity)))
            self._items_table.setItem(
                r, 2, QTableWidgetItem(format_currency(it.unit_cost, symbol))
            )
            self._items_table.setItem(
                r, 3, QTableWidgetItem(format_currency(it.line_total, symbol))
            )

    def _print(self) -> None:
        purchase = self._c.purchases.get(self._purchase_id)
        symbol = self._c.settings.currency_symbol
        items = self._c.purchases.items(self._purchase_id)
        rows = "".join(
            f"<tr><td>{it.description}</td><td>{it.quantity}</td>"
            f"<td>{format_currency(it.unit_cost, symbol)}</td>"
            f"<td>{format_currency(it.line_total, symbol)}</td></tr>"
            for it in items
        )
        html = (
            f"<h2>فاتورة شراء {purchase.display_no}</h2>"
            f"<p>المورّد: {purchase.supplier_name} | التاريخ: "
            f"{format_iso_date(purchase.date)}</p>"
            "<table><tr><th>الصنف</th><th>الكمية</th><th>التكلفة</th>"
            f"<th>الإجمالي</th></tr>{rows}</table>"
            f"<p>الإجمالي: {format_currency(purchase.total, symbol)} | "
            f"المدفوع: {format_currency(purchase.paid, symbol)} | "
            f"المتبقّي: {format_currency(purchase.remaining, symbol)}</p>"
        )
        print_html(self, html, "طباعة فاتورة شراء")
