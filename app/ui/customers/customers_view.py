"""وحدة العملاء — تنقّل بصفحات كاملة:

- ``CustomersView``: قائمة العملاء (جذر الوحدة) + بحث + أزرار تفتح صفحات كاملة.
- ``CustomerFormPage``: نموذج إضافة/تعديل (صفحة كاملة).
- ``CustomerAccountPage``: شاشة حساب العميل الكاملة (بيانات/رصيد/حد ائتماني/
  فواتير/أقساط/مدفوعات/كشف حساب/طباعة).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.constants.permissions import Permissions
from app.core.utils.formatters import format_currency, format_iso_date
from app.domain.entities import Customer
from app.services.customers_service import CustomersServiceError
from app.ui.components.flow_layout import toolbar
from app.ui.components.page import Page
from app.ui.components.printing import export_pdf, print_html
from app.ui.components.widgets import Card, StatCard, heading_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container


# ── قائمة العملاء (جذر الوحدة) ──────────────────────────────────────────
class CustomersView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._can_manage = container.auth.can(Permissions.CUSTOMERS_MANAGE)
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 26)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.addWidget(title_label("العملاء"))
        title_row.addStretch(1)
        layout.addLayout(title_row)

        self._search = QLineEdit()
        self._search.setPlaceholderText("بحث بالاسم أو الهاتف أو الرقم القومي…")
        self._search.setMinimumWidth(240)
        self._search.textChanged.connect(self.refresh)

        add_btn = QPushButton("عميل جديد")
        add_btn.setEnabled(self._can_manage)
        add_btn.clicked.connect(self._add)
        open_btn = QPushButton("فتح الحساب")
        open_btn.clicked.connect(self._open_account)
        del_btn = QPushButton("حذف")
        del_btn.setObjectName("Danger")
        del_btn.setEnabled(self._can_manage)
        del_btn.clicked.connect(self._delete)
        layout.addWidget(toolbar([self._search, add_btn, open_btn, del_btn]))

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["الاسم", "الهاتف", "الرقم القومي", "الرصيد", "الحد الائتماني"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.doubleClicked.connect(self._open_account)
        layout.addWidget(self._table)
        hint = QLabel("نقرة مزدوجة على العميل لفتح حسابه الكامل.")
        hint.setObjectName("Muted")
        layout.addWidget(hint)

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
            self._table.setItem(
                r, 3, QTableWidgetItem(format_currency(cust.balance, symbol))
            )
            self._table.setItem(
                r, 4, QTableWidgetItem(format_currency(cust.credit_limit, symbol))
            )

    def _selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _add(self) -> None:
        self._c.navigator.push(CustomerFormPage(self._c, None))

    def _open_account(self) -> None:
        cid = self._selected_id()
        if cid is None:
            QMessageBox.information(self, "تنبيه", "اختر عميلًا أولًا.")
            return
        self._c.navigator.push(CustomerAccountPage(self._c, cid))

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


# ── نموذج العميل (صفحة كاملة) ───────────────────────────────────────────
class CustomerFormPage(Page):
    def __init__(self, container: "Container", customer: Customer | None):
        title = "تعديل عميل" if customer else "عميل جديد"
        super().__init__(container.navigator, title)
        self._c = container
        self._customer = customer

        card = Card()
        form = QFormLayout()
        card.layout().addLayout(form)

        self._name = QLineEdit(customer.name if customer else "")
        self._phone = QLineEdit(customer.phone if customer else "")
        self._national = QLineEdit(customer.national_id if customer else "")
        self._address = QLineEdit(customer.address if customer else "")
        self._credit = QDoubleSpinBox()
        self._credit.setRange(0, 1_000_000_000)
        self._credit.setDecimals(2)
        self._credit.setValue(customer.credit_limit if customer else 0)

        form.addRow(QLabel("الاسم *"), self._name)
        form.addRow(QLabel("الهاتف"), self._phone)
        form.addRow(QLabel("الرقم القومي"), self._national)
        form.addRow(QLabel("العنوان"), self._address)
        form.addRow(QLabel("الحد الائتماني"), self._credit)

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
            if self._customer is None:
                self._c.customers.create(
                    name=self._name.text(),
                    phone=self._phone.text(),
                    national_id=self._national.text(),
                    address=self._address.text(),
                    credit_limit=self._credit.value(),
                    actor_id=actor_id,
                )
            else:
                self._c.customers.update(
                    self._customer.id,
                    name=self._name.text(),
                    phone=self._phone.text(),
                    national_id=self._national.text(),
                    address=self._address.text(),
                    credit_limit=self._credit.value(),
                    actor_id=actor_id,
                )
        except CustomersServiceError as exc:
            QMessageBox.warning(self, "تعذّر الحفظ", str(exc))
            return
        self.go_back()


# ── شاشة حساب العميل الكاملة ─────────────────────────────────────────────
class CustomerAccountPage(Page):
    def __init__(self, container: "Container", customer_id: int):
        super().__init__(container.navigator, "حساب العميل")
        self._c = container
        self._customer_id = customer_id

        edit = QPushButton("تعديل البيانات")
        edit.setObjectName("Ghost")
        edit.setEnabled(container.auth.can(Permissions.CUSTOMERS_MANAGE))
        edit.clicked.connect(self._edit)
        printb = QPushButton("طباعة كشف الحساب")
        printb.clicked.connect(self._print)
        pdfb = QPushButton("تصدير PDF")
        pdfb.setObjectName("Ghost")
        pdfb.clicked.connect(self._export_pdf)
        self.add_action(edit)
        self.add_action(printb)
        self.add_action(pdfb)

        # بطاقات ملخص
        self._stats_row = QHBoxLayout()
        self.body.addLayout(self._stats_row)

        self._info = Card()
        self.body.addWidget(self._info)

        self._tabs = QTabWidget()
        self._sales_tbl = self._make_table(
            ["#", "النوع", "التاريخ", "الإجمالي", "المدفوع", "المتبقي"]
        )
        self._inst_tbl = self._make_table(
            ["فاتورة", "تاريخ الاستحقاق", "القيمة", "المدفوع", "الحالة"]
        )
        self._pay_tbl = self._make_table(["التاريخ", "المبلغ", "ملاحظات"])
        self._tabs.addTab(self._wrap(self._sales_tbl), "الفواتير")
        self._tabs.addTab(self._wrap(self._inst_tbl), "الأقساط")
        self._tabs.addTab(self._wrap(self._pay_tbl), "المدفوعات")
        self.body.addWidget(self._tabs, stretch=1)

        self.refresh()

    # ── أدوات داخلية ────────────────────────────────────────────────────
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

    def _customer(self) -> Customer | None:
        return self._c.customers.get(self._customer_id)

    # ── التحديث ─────────────────────────────────────────────────────────
    def refresh(self) -> None:
        cust = self._customer()
        if cust is None:
            self.go_back()
            return
        symbol = self._c.settings.currency_symbol
        self.set_title(f"حساب العميل — {cust.name}")

        # بطاقات الملخص
        while self._stats_row.count():
            item = self._stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._stats_row.addWidget(StatCard("الرصيد الحالي", format_currency(cust.balance, symbol)))
        self._stats_row.addWidget(
            StatCard("الحد الائتماني", format_currency(cust.credit_limit, symbol))
        )
        available = cust.credit_limit - cust.balance
        self._stats_row.addWidget(
            StatCard("المتاح من الائتمان", format_currency(available, symbol))
        )

        # بطاقة البيانات
        lay = self._info.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        lay.addWidget(heading_label("بيانات العميل"))
        lay.addWidget(QLabel(f"الهاتف: {cust.phone or '—'}"))
        lay.addWidget(QLabel(f"الرقم القومي: {cust.national_id or '—'}"))
        lay.addWidget(QLabel(f"العنوان: {cust.address or '—'}"))

        self._fill_sales(symbol)
        self._fill_installments(symbol)
        self._fill_payments(symbol)

    def _fill_sales(self, symbol: str) -> None:
        rows = self._c.customers.sales(self._customer_id)
        self._sales_tbl.setRowCount(len(rows))
        for r, row in enumerate(rows):
            remaining = (row["total"] or 0) - (row["paid"] or 0)
            kind = "نقدي" if row["type"] == "cash" else "تقسيط"
            values = [
                str(row["id"]), kind, format_iso_date(row["date"]),
                format_currency(row["total"] or 0, symbol),
                format_currency(row["paid"] or 0, symbol),
                format_currency(remaining, symbol),
            ]
            for c, v in enumerate(values):
                self._sales_tbl.setItem(r, c, QTableWidgetItem(v))

    def _fill_installments(self, symbol: str) -> None:
        rows = self._c.customers.installments(self._customer_id)
        self._inst_tbl.setRowCount(len(rows))
        status_ar = {"pending": "مستحق", "paid": "مدفوع", "late": "متأخر"}
        for r, row in enumerate(rows):
            values = [
                str(row["sale_id"]), format_iso_date(row["due_date"]),
                format_currency(row["amount"] or 0, symbol),
                format_currency(row["paid_amount"] or 0, symbol),
                status_ar.get(row["status"], row["status"]),
            ]
            for c, v in enumerate(values):
                self._inst_tbl.setItem(r, c, QTableWidgetItem(v))

    def _fill_payments(self, symbol: str) -> None:
        rows = self._c.customers.payments(self._customer_id)
        self._pay_tbl.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [
                format_iso_date(row["date"]),
                format_currency(row["amount"] or 0, symbol),
                row["notes"] or "",
            ]
            for c, v in enumerate(values):
                self._pay_tbl.setItem(r, c, QTableWidgetItem(v))

    # ── إجراءات ─────────────────────────────────────────────────────────
    def _edit(self) -> None:
        cust = self._customer()
        if cust:
            self._c.navigator.push(CustomerFormPage(self._c, cust))

    def _statement_html(self) -> str:
        cust = self._customer()
        symbol = self._c.settings.currency_symbol
        rows = self._c.customers.sales(self._customer_id)
        body = "".join(
            f"<tr><td>{row['id']}</td><td>{format_iso_date(row['date'])}</td>"
            f"<td>{format_currency(row['total'] or 0, symbol)}</td>"
            f"<td>{format_currency(row['paid'] or 0, symbol)}</td></tr>"
            for row in rows
        ) or "<tr><td colspan='4'>لا توجد فواتير</td></tr>"
        return (
            f"<h2>كشف حساب: {cust.name}</h2>"
            f"<p>الهاتف: {cust.phone or '—'} | الرصيد الحالي: "
            f"{format_currency(cust.balance, symbol)} | الحد الائتماني: "
            f"{format_currency(cust.credit_limit, symbol)}</p>"
            "<table><tr><th>فاتورة</th><th>التاريخ</th><th>الإجمالي</th>"
            f"<th>المدفوع</th></tr>{body}</table>"
        )

    def _print(self) -> None:
        print_html(self, self._statement_html(), "كشف حساب العميل")

    def _export_pdf(self) -> None:
        cust = self._customer()
        export_pdf(self, self._statement_html(), f"كشف_{cust.name}.pdf")

