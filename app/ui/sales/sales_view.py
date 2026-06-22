"""وحدة المبيعات — صفحات كاملة:

- ``SalesView``: قائمة فواتير البيع (جذر الوحدة) + بحث + تصفية بحالة الدفع.
- ``SaleFormPage``: إنشاء فاتورة بيع وترحيلها (نقدي/آجل/جزئي).
- ``SaleDetailPage``: تفاصيل الفاتورة + طباعة.

الترحيل يربط: المخزون (صرف) + الخزينة (المقبوض) + حساب العميل (المتبقّي) +
التدقيق، ضمن اليوم المفتوح فقط.
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
from app.services.sales_service import SalesServiceError
from app.ui.components.page import Page
from app.ui.components.printing import print_html
from app.ui.components.widgets import Card, StatCard, heading_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container


# ── قائمة المبيعات (جذر الوحدة) ─────────────────────────────────────────
class SalesView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._can_create = container.auth.can(Permissions.SALES_CASH_CREATE)
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 26)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(title_label("المبيعات"))
        header.addStretch(1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("بحث باسم العميل أو رقم الفاتورة…")
        self._search.setFixedWidth(240)
        self._search.textChanged.connect(self.refresh)
        header.addWidget(self._search)
        self._status = QComboBox()
        self._status.addItem("كل الحالات", "")
        self._status.addItem("مدفوعة", "مدفوعة")
        self._status.addItem("آجل", "آجل")
        self._status.addItem("جزئي", "جزئي")
        self._status.currentIndexChanged.connect(self.refresh)
        header.addWidget(self._status)

        new_btn = QPushButton("فاتورة بيع جديدة")
        new_btn.setEnabled(self._can_create)
        new_btn.clicked.connect(self._new)
        open_btn = QPushButton("عرض الفاتورة")
        open_btn.clicked.connect(self._open)
        del_btn = QPushButton("حذف")
        del_btn.setObjectName("Danger")
        del_btn.setEnabled(self._can_create)
        del_btn.clicked.connect(self._delete)
        for b in (new_btn, open_btn, del_btn):
            header.addWidget(b)
        layout.addLayout(header)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["#", "العميل", "التاريخ", "الإجمالي", "المقبوض", "الحالة"]
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
        status_filter = self._status.currentData()
        sales = [
            s for s in self._c.sales.list(self._search.text())
            if not status_filter or s.payment_status == status_filter
        ]
        self._table.setRowCount(len(sales))
        for r, s in enumerate(sales):
            id_item = QTableWidgetItem(s.display_no)
            id_item.setData(Qt.ItemDataRole.UserRole, s.id)
            self._table.setItem(r, 0, id_item)
            self._table.setItem(r, 1, QTableWidgetItem(s.customer_name or "نقدي"))
            self._table.setItem(r, 2, QTableWidgetItem(format_iso_date(s.date)))
            self._table.setItem(r, 3, QTableWidgetItem(format_currency(s.total, symbol)))
            self._table.setItem(r, 4, QTableWidgetItem(format_currency(s.paid, symbol)))
            self._table.setItem(r, 5, QTableWidgetItem(s.payment_status))

    def _selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _new(self) -> None:
        self._c.navigator.push(SaleFormPage(self._c))

    def _open(self) -> None:
        sid = self._selected_id()
        if sid is None:
            QMessageBox.information(self, "تنبيه", "اختر فاتورة أولًا.")
            return
        self._c.navigator.push(SaleDetailPage(self._c, sid))

    def _delete(self) -> None:
        sid = self._selected_id()
        if sid is None:
            QMessageBox.information(self, "تنبيه", "اختر فاتورة أولًا.")
            return
        if (
            QMessageBox.question(
                self, "تأكيد",
                "حذف الفاتورة سيعكس المخزون والخزينة وحساب العميل. متابعة؟",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        actor = self._c.auth.current_user
        try:
            self._c.sales.delete_sale(sid, actor_id=actor.id if actor else None)
        except SalesServiceError as exc:
            QMessageBox.warning(self, "تعذّر الحذف", str(exc))
            return
        self.refresh()


# ── فاتورة بيع جديدة (صفحة كاملة) ───────────────────────────────────────
class SaleFormPage(Page):
    def __init__(self, container: "Container"):
        super().__init__(container.navigator, "فاتورة بيع جديدة")
        self._c = container
        self._lines: list[dict] = []

        head = Card()
        form = QFormLayout()
        head.layout().addLayout(form)
        self._customer = QComboBox()
        self._customer.addItem("بدون عميل (نقدي)", None)
        for cust in self._c.customers.list():
            self._customer.addItem(cust.name, cust.id)
        self._notes = QLineEdit()
        form.addRow(QLabel("العميل"), self._customer)
        form.addRow(QLabel("ملاحظات"), self._notes)
        self.body.addWidget(head)

        builder = Card()
        builder.layout().addWidget(heading_label("أصناف الفاتورة"))
        line_row = QHBoxLayout()
        self._item = QComboBox()
        self._items_by_id: dict[int, object] = {}
        for it in self._c.inventory.list(status="active"):
            self._item.addItem(f"{it.name} ({it.unit}) — متاح {it.quantity:g}", it.id)
            self._items_by_id[it.id] = it
        self._item.currentIndexChanged.connect(self._prefill_price)
        self._qty = QDoubleSpinBox()
        self._qty.setRange(0.01, 1_000_000_000)
        self._qty.setDecimals(2)
        self._qty.setValue(1)
        self._price = QDoubleSpinBox()
        self._price.setRange(0, 1_000_000_000)
        self._price.setDecimals(2)
        add_line = QPushButton("إضافة صنف")
        add_line.clicked.connect(self._add_line)
        for w in (
            QLabel("الصنف"), self._item, QLabel("الكمية"), self._qty,
            QLabel("السعر"), self._price, add_line,
        ):
            line_row.addWidget(w)
        builder.layout().addLayout(line_row)

        self._lines_table = QTableWidget(0, 5)
        self._lines_table.setHorizontalHeaderLabels(
            ["الصنف", "الكمية", "السعر", "الإجمالي", ""]
        )
        self._lines_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._lines_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        builder.layout().addWidget(self._lines_table)
        self.body.addWidget(builder, stretch=1)

        footer = Card()
        fform = QFormLayout()
        footer.layout().addLayout(fform)
        self._discount = QDoubleSpinBox()
        self._discount.setRange(0, 1_000_000_000)
        self._discount.setDecimals(2)
        self._discount.valueChanged.connect(self._recompute)
        self._total_lbl = QLabel("0")
        self._total_lbl.setObjectName("Heading")
        self._payment = QComboBox()
        self._payment.addItem("كاش (مدفوع كامل)", "cash")
        self._payment.addItem("آجل (على الحساب)", "credit")
        self._payment.addItem("جزئي", "partial")
        self._payment.currentIndexChanged.connect(self._on_payment_change)
        self._paid = QDoubleSpinBox()
        self._paid.setRange(0, 1_000_000_000)
        self._paid.setDecimals(2)
        self._paid.setEnabled(False)
        fform.addRow(QLabel("الخصم"), self._discount)
        fform.addRow(QLabel("الإجمالي بعد الخصم"), self._total_lbl)
        fform.addRow(QLabel("نوع الدفع"), self._payment)
        fform.addRow(QLabel("المقبوض (للجزئي)"), self._paid)
        save = QPushButton("حفظ وترحيل")
        save.setEnabled(self._c.auth.can(Permissions.SALES_CASH_CREATE))
        save.clicked.connect(self._save)
        footer.layout().addWidget(save)
        self.body.addWidget(footer)

        self._prefill_price()

    # ── البنّاء ─────────────────────────────────────────────────────────
    def _prefill_price(self) -> None:
        item_id = self._item.currentData()
        item = self._items_by_id.get(item_id) if item_id is not None else None
        if item is not None:
            self._price.setValue(item.sale_price)

    def _add_line(self) -> None:
        item_id = self._item.currentData()
        if item_id is None:
            QMessageBox.information(self, "تنبيه", "لا توجد أصناف نشطة.")
            return
        item = self._items_by_id[item_id]
        self._lines.append(
            {
                "item_id": item_id,
                "description": item.name,
                "quantity": self._qty.value(),
                "unit_price": self._price.value(),
            }
        )
        self._rebuild_lines()

    def _rebuild_lines(self) -> None:
        symbol = self._c.settings.currency_symbol
        self._lines_table.setRowCount(len(self._lines))
        for r, ln in enumerate(self._lines):
            total = ln["quantity"] * ln["unit_price"]
            self._lines_table.setItem(r, 0, QTableWidgetItem(ln["description"]))
            self._lines_table.setItem(r, 1, QTableWidgetItem(str(ln["quantity"])))
            self._lines_table.setItem(
                r, 2, QTableWidgetItem(format_currency(ln["unit_price"], symbol))
            )
            self._lines_table.setItem(
                r, 3, QTableWidgetItem(format_currency(total, symbol))
            )
            remove = QPushButton("حذف")
            remove.clicked.connect(lambda _c, i=r: self._remove_line(i))
            self._lines_table.setCellWidget(r, 4, remove)
        self._recompute()

    def _remove_line(self, index: int) -> None:
        if 0 <= index < len(self._lines):
            self._lines.pop(index)
            self._rebuild_lines()

    def _gross(self) -> float:
        return sum(ln["quantity"] * ln["unit_price"] for ln in self._lines)

    def _total(self) -> float:
        return max(self._gross() - self._discount.value(), 0)

    def _recompute(self) -> None:
        symbol = self._c.settings.currency_symbol
        total = self._total()
        self._total_lbl.setText(format_currency(total, symbol))
        if self._payment.currentData() == "partial":
            self._paid.setMaximum(total)

    def _on_payment_change(self) -> None:
        mode = self._payment.currentData()
        self._paid.setEnabled(mode == "partial")
        if mode == "partial":
            self._paid.setMaximum(self._total())

    def _save(self) -> None:
        total = self._total()
        mode = self._payment.currentData()
        if mode == "cash":
            paid = total
        elif mode == "credit":
            paid = 0.0
        else:
            paid = self._paid.value()

        actor = self._c.auth.current_user
        try:
            self._c.sales.create_sale(
                customer_id=self._customer.currentData(),
                lines=self._lines,
                discount=self._discount.value(),
                paid=paid,
                notes=self._notes.text().strip() or None,
                actor_id=actor.id if actor else None,
            )
        except SalesServiceError as exc:
            QMessageBox.warning(self, "تعذّر الترحيل", str(exc))
            return
        QMessageBox.information(self, "تم", "تم ترحيل فاتورة البيع.")
        self.go_back()


# ── تفاصيل فاتورة البيع (صفحة كاملة) ────────────────────────────────────
class SaleDetailPage(Page):
    def __init__(self, container: "Container", sale_id: int):
        super().__init__(container.navigator, "تفاصيل فاتورة البيع")
        self._c = container
        self._sale_id = sale_id

        printb = QPushButton("طباعة")
        printb.clicked.connect(self._print)
        self.add_action(printb)

        self._stats = QHBoxLayout()
        self.body.addLayout(self._stats)
        self._info = Card()
        self.body.addWidget(self._info)
        self._items_table = QTableWidget(0, 4)
        self._items_table.setHorizontalHeaderLabels(
            ["الصنف", "الكمية", "السعر", "الإجمالي"]
        )
        self._items_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.body.addWidget(self._items_table, stretch=1)
        self.refresh()

    def refresh(self) -> None:
        sale = self._c.sales.get(self._sale_id)
        if sale is None:
            self.go_back()
            return
        symbol = self._c.settings.currency_symbol
        self.set_title(f"فاتورة بيع {sale.display_no} — {sale.customer_name or 'نقدي'}")

        while self._stats.count():
            item = self._stats.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._stats.addWidget(StatCard("الإجمالي", format_currency(sale.total, symbol)))
        self._stats.addWidget(StatCard("المقبوض", format_currency(sale.paid, symbol)))
        self._stats.addWidget(StatCard("المتبقّي", format_currency(sale.remaining, symbol)))
        self._stats.addWidget(StatCard("الحالة", sale.payment_status))

        lay = self._info.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        lay.addWidget(heading_label("بيانات الفاتورة"))
        lay.addWidget(QLabel(f"العميل: {sale.customer_name or 'نقدي'}"))
        lay.addWidget(QLabel(f"التاريخ: {format_iso_date(sale.date)}"))
        lay.addWidget(QLabel(f"الخصم: {format_currency(sale.discount, symbol)}"))
        lay.addWidget(QLabel(f"ملاحظات: {sale.notes or '—'}"))

        items = self._c.sales.items(self._sale_id)
        self._items_table.setRowCount(len(items))
        for r, it in enumerate(items):
            self._items_table.setItem(r, 0, QTableWidgetItem(it.description))
            self._items_table.setItem(r, 1, QTableWidgetItem(str(it.quantity)))
            self._items_table.setItem(
                r, 2, QTableWidgetItem(format_currency(it.unit_price, symbol))
            )
            self._items_table.setItem(
                r, 3, QTableWidgetItem(format_currency(it.line_total, symbol))
            )

    def _print(self) -> None:
        sale = self._c.sales.get(self._sale_id)
        symbol = self._c.settings.currency_symbol
        items = self._c.sales.items(self._sale_id)
        rows = "".join(
            f"<tr><td>{it.description}</td><td>{it.quantity}</td>"
            f"<td>{format_currency(it.unit_price, symbol)}</td>"
            f"<td>{format_currency(it.line_total, symbol)}</td></tr>"
            for it in items
        )
        html = (
            f"<h2>{self._c.settings.showroom_name} — فاتورة بيع {sale.display_no}</h2>"
            f"<p>العميل: {sale.customer_name or 'نقدي'} | التاريخ: "
            f"{format_iso_date(sale.date)}</p>"
            "<table><tr><th>الصنف</th><th>الكمية</th><th>السعر</th>"
            f"<th>الإجمالي</th></tr>{rows}</table>"
            f"<p>الخصم: {format_currency(sale.discount, symbol)} | "
            f"الإجمالي: {format_currency(sale.total, symbol)} | "
            f"المقبوض: {format_currency(sale.paid, symbol)} | "
            f"المتبقّي: {format_currency(sale.remaining, symbol)} "
            f"({sale.payment_status})</p>"
        )
        print_html(self, html, "طباعة فاتورة بيع")
