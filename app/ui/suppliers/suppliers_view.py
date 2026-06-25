"""وحدة الموردين — تنقّل بصفحات كاملة:

- ``SuppliersView``: قائمة الموردين (جذر الوحدة).
- ``SupplierFormPage``: نموذج إضافة/تعديل (صفحة كاملة).
- ``SupplierAccountPage``: شاشة حساب المورّد الكاملة (بيانات/رصيد/فواتير شراء/
  دفعات/مرتجعات/سجل حركة/كشف حساب/طباعة).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.constants.permissions import Permissions
from app.core.utils.formatters import format_currency, format_iso_date
from app.domain.entities import Supplier
from app.services.suppliers_service import SuppliersServiceError
from app.ui.components.flow_layout import toolbar
from app.ui.components.page import Page
from app.ui.components.printing import export_pdf, print_html
from app.ui.components.widgets import Card, StatCard, heading_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container


# ── قائمة الموردين (جذر الوحدة) ─────────────────────────────────────────
class SuppliersView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._can_manage = container.auth.can(Permissions.SUPPLIERS_MANAGE)
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 26)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.addWidget(title_label("الموردون"))
        title_row.addStretch(1)
        layout.addLayout(title_row)

        self._search = QLineEdit()
        self._search.setPlaceholderText("بحث بالاسم أو الهاتف…")
        self._search.setMinimumWidth(220)
        self._search.textChanged.connect(self.refresh)

        add_btn = QPushButton("مورّد جديد")
        add_btn.setEnabled(self._can_manage)
        add_btn.clicked.connect(self._add)
        open_btn = QPushButton("فتح الحساب")
        open_btn.clicked.connect(self._open_account)
        del_btn = QPushButton("حذف")
        del_btn.setObjectName("Danger")
        del_btn.setEnabled(self._can_manage)
        del_btn.clicked.connect(self._delete)
        layout.addWidget(toolbar([self._search, add_btn, open_btn, del_btn]))

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["الاسم", "الهاتف", "العنوان", "الرصيد (له)"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.doubleClicked.connect(self._open_account)
        layout.addWidget(self._table)
        hint = QLabel("نقرة مزدوجة على المورّد لفتح حسابه الكامل.")
        hint.setObjectName("Muted")
        layout.addWidget(hint)

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
        self._c.navigator.push(SupplierFormPage(self._c, None))

    def _open_account(self) -> None:
        sid = self._selected_id()
        if sid is None:
            QMessageBox.information(self, "تنبيه", "اختر مورّدًا أولًا.")
            return
        self._c.navigator.push(SupplierAccountPage(self._c, sid))

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


# ── نموذج المورّد (صفحة كاملة) ──────────────────────────────────────────
class SupplierFormPage(Page):
    def __init__(self, container: "Container", supplier: Supplier | None):
        super().__init__(
            container.navigator, "تعديل مورّد" if supplier else "مورّد جديد"
        )
        self._c = container
        self._supplier = supplier

        card = Card()
        form = QFormLayout()
        card.layout().addLayout(form)
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
        cancel.clicked.connect(self.go_back)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        card.layout().addLayout(buttons)

        self.body.addWidget(card)
        self.body.addStretch(1)

    def _save(self) -> None:
        actor = self._c.auth.current_user
        actor_id = actor.id if actor else None
        try:
            if self._supplier is None:
                self._c.suppliers.create(
                    name=self._name.text(), phone=self._phone.text(),
                    address=self._address.text(), actor_id=actor_id,
                )
            else:
                self._c.suppliers.update(
                    self._supplier.id, name=self._name.text(),
                    phone=self._phone.text(), address=self._address.text(),
                    actor_id=actor_id,
                )
        except SuppliersServiceError as exc:
            QMessageBox.warning(self, "تعذّر الحفظ", str(exc))
            return
        self.go_back()


# ── شاشة حساب المورّد الكاملة ────────────────────────────────────────────
class SupplierAccountPage(Page):
    def __init__(self, container: "Container", supplier_id: int):
        super().__init__(container.navigator, "حساب المورّد")
        self._c = container
        self._supplier_id = supplier_id

        edit = QPushButton("تعديل البيانات")
        edit.setObjectName("Ghost")
        edit.setEnabled(container.auth.can(Permissions.SUPPLIERS_MANAGE))
        edit.clicked.connect(self._edit)
        printb = QPushButton("طباعة كشف الحساب")
        printb.clicked.connect(self._print)
        pdfb = QPushButton("تصدير PDF")
        pdfb.setObjectName("Ghost")
        pdfb.clicked.connect(self._export_pdf)
        for b in (edit, printb, pdfb):
            self.add_action(b)

        self._stats_row = QHBoxLayout()
        self.body.addLayout(self._stats_row)
        self._info = Card()
        self.body.addWidget(self._info)

        self._tabs = QTabWidget()
        self._purch_tbl = self._make_table(
            ["#", "التاريخ", "الإجمالي", "المدفوع", "المتبقي"]
        )
        self._pay_tbl = self._make_table(["التاريخ", "المبلغ", "ملاحظات"])
        self._returns_tbl = self._make_table(["التاريخ", "القيمة", "ملاحظات"])
        self._tabs.addTab(self._wrap(self._purch_tbl), "فواتير الشراء")
        self._tabs.addTab(self._wrap(self._pay_tbl), "الدفعات")
        self._tabs.addTab(self._wrap(self._returns_tbl), "المرتجعات")
        self.body.addWidget(self._tabs, stretch=1)

        self.refresh()

    @staticmethod
    def _make_table(headers: list[str]) -> QTableWidget:
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return t

    @staticmethod
    def _wrap(table: QTableWidget) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(table)
        return w

    def _supplier(self) -> Supplier | None:
        return self._c.suppliers.get(self._supplier_id)

    def refresh(self) -> None:
        sup = self._supplier()
        if sup is None:
            self.go_back()
            return
        symbol = self._c.settings.currency_symbol
        self.set_title(f"حساب المورّد — {sup.name}")

        while self._stats_row.count():
            item = self._stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._stats_row.addWidget(
            StatCard("الرصيد الحالي (له)", format_currency(sup.balance, symbol),
                     icon="💼", tone="#E08A3C")
        )

        lay = self._info.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        lay.addWidget(heading_label("بيانات المورّد"))
        lay.addWidget(QLabel(f"الهاتف: {sup.phone or '—'}"))
        lay.addWidget(QLabel(f"العنوان: {sup.address or '—'}"))

        purchases = self._c.suppliers.purchases(self._supplier_id)
        self._purch_tbl.setRowCount(len(purchases))
        for r, row in enumerate(purchases):
            remaining = (row["total"] or 0) - (row["paid"] or 0)
            values = [
                str(row["id"]), format_iso_date(row["date"]),
                format_currency(row["total"] or 0, symbol),
                format_currency(row["paid"] or 0, symbol),
                format_currency(remaining, symbol),
            ]
            for c, v in enumerate(values):
                self._purch_tbl.setItem(r, c, QTableWidgetItem(v))

        payments = self._c.suppliers.payments(self._supplier_id)
        self._pay_tbl.setRowCount(len(payments))
        for r, row in enumerate(payments):
            values = [
                format_iso_date(row["date"]),
                format_currency(row["amount"] or 0, symbol),
                row["notes"] or "",
            ]
            for c, v in enumerate(values):
                self._pay_tbl.setItem(r, c, QTableWidgetItem(v))

        # المرتجعات: ميزة مستقبلية (لا يوجد جدول مرتجعات بعد).
        self._returns_tbl.setRowCount(0)

    def _edit(self) -> None:
        sup = self._supplier()
        if sup:
            self._c.navigator.push(SupplierFormPage(self._c, sup))

    def _statement_html(self) -> str:
        sup = self._supplier()
        symbol = self._c.settings.currency_symbol
        rows = self._c.suppliers.purchases(self._supplier_id)
        body = "".join(
            f"<tr><td>{row['id']}</td><td>{format_iso_date(row['date'])}</td>"
            f"<td>{format_currency(row['total'] or 0, symbol)}</td>"
            f"<td>{format_currency(row['paid'] or 0, symbol)}</td></tr>"
            for row in rows
        ) or "<tr><td colspan='4'>لا توجد فواتير شراء</td></tr>"
        return (
            f"<h2>كشف حساب مورّد: {sup.name}</h2>"
            f"<p>الهاتف: {sup.phone or '—'} | الرصيد الحالي: "
            f"{format_currency(sup.balance, symbol)}</p>"
            "<table><tr><th>فاتورة</th><th>التاريخ</th><th>الإجمالي</th>"
            f"<th>المدفوع</th></tr>{body}</table>"
        )

    def _print(self) -> None:
        print_html(self, self._statement_html(), "كشف حساب المورّد")

    def _export_pdf(self) -> None:
        sup = self._supplier()
        export_pdf(self, self._statement_html(), f"كشف_{sup.name}.pdf")
