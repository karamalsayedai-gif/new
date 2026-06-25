"""وحدة التقسيط — صفحات كاملة:

- ``InstallmentsView``: قائمة عقود التقسيط (جذر الوحدة).
- ``InstallmentFormPage``: إنشاء عقد تقسيط (عميل + أصناف + مقدّم + أشهر + فائدة).
- ``InstallmentDetailPage``: تفاصيل العقد + جدول الأقساط + التحصيلات + طباعة.
- ``CollectPage``: تحصيل قسط (توزيع تلقائي على الأقدم).
- ``ArrearsPage``: المتأخرات لكل عميل + المستحق اليوم.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.constants.permissions import Permissions
from app.core.utils.formatters import format_currency, format_iso_date
from app.services.customers_service import CustomersServiceError
from app.services.installments_service import InstallmentsServiceError
from app.ui.components.flow_layout import toolbar
from app.ui.components.page import Page
from app.ui.components.printing import build_invoice_html, export_pdf, print_html
from app.ui.components.widgets import (
    Card,
    StatCard,
    heading_label,
    title_label,
    treasury_combo,
)

if TYPE_CHECKING:
    from app.core.container import Container

_PLAN_STATUS_AR = {"active": "نشط", "completed": "مكتمل", "defaulted": "متعثّر"}


def _inst_status(ins, today: str) -> str:
    if ins.remaining <= 0:
        return "مدفوع"
    if ins.is_overdue(today):
        return f"متأخر ({ins.days_late(today)} يوم)"
    if ins.paid_amount > 0:
        return "جزئي"
    return "مستحق"


# ── قائمة عقود التقسيط (جذر الوحدة) ─────────────────────────────────────
class InstallmentsView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._can_create = container.auth.can(Permissions.SALES_INSTALLMENT_CREATE)
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 26)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.addWidget(title_label("التقسيط"))
        title_row.addStretch(1)
        layout.addLayout(title_row)

        self._search = QLineEdit()
        self._search.setPlaceholderText("بحث باسم العميل…")
        self._search.setMinimumWidth(200)
        self._search.textChanged.connect(self.refresh)

        new_btn = QPushButton("عقد تقسيط جديد")
        new_btn.setEnabled(self._can_create)
        new_btn.clicked.connect(lambda: self._c.navigator.push(InstallmentFormPage(self._c)))
        open_btn = QPushButton("عرض التفاصيل")
        open_btn.clicked.connect(self._open)
        arrears_btn = QPushButton("المتأخرات")
        arrears_btn.setObjectName("Ghost")
        arrears_btn.clicked.connect(lambda: self._c.navigator.push(ArrearsPage(self._c)))
        layout.addWidget(toolbar([self._search, new_btn, open_btn, arrears_btn]))

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["#", "العميل", "التاريخ", "إجمالي الأقساط", "المدفوع", "المتبقّي", "الحالة"]
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
        plans = self._c.installments.list_plans(self._search.text())
        self._table.setRowCount(len(plans))
        for r, p in enumerate(plans):
            paid = self._c.installments.plan_paid(p.id)
            remaining = p.total_amount - paid
            id_item = QTableWidgetItem(str(p.id))
            id_item.setData(Qt.ItemDataRole.UserRole, p.id)
            self._table.setItem(r, 0, id_item)
            self._table.setItem(r, 1, QTableWidgetItem(p.customer_name))
            self._table.setItem(r, 2, QTableWidgetItem(format_iso_date(p.sale_date)))
            self._table.setItem(r, 3, QTableWidgetItem(format_currency(p.total_amount, symbol)))
            self._table.setItem(r, 4, QTableWidgetItem(format_currency(paid, symbol)))
            self._table.setItem(r, 5, QTableWidgetItem(format_currency(remaining, symbol)))
            self._table.setItem(
                r, 6, QTableWidgetItem(_PLAN_STATUS_AR.get(p.status, p.status))
            )

    def _open(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "تنبيه", "اختر عقدًا أولًا.")
            return
        plan_id = int(self._table.item(row, 0).data(Qt.ItemDataRole.UserRole))
        self._c.navigator.push(InstallmentDetailPage(self._c, plan_id))


# ── عقد تقسيط جديد ──────────────────────────────────────────────────────
class InstallmentFormPage(Page):
    def __init__(self, container: "Container"):
        super().__init__(container.navigator, "عقد تقسيط جديد")
        self._c = container
        self._lines: list[dict] = []

        head = Card()
        form = QFormLayout()
        head.layout().addLayout(form)
        # العميل: قابل للكتابة المباشرة — اكتب اسمًا جديدًا أو اختر موجودًا.
        self._customer = QComboBox()
        self._customer.setEditable(True)
        self._customer.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._customer.addItem("", None)
        for cust in self._c.customers.list():
            self._customer.addItem(cust.name, cust.id)
        self._customer.setCurrentIndex(0)
        self._customer.lineEdit().setPlaceholderText(
            "اكتب اسم العميل مباشرة أو اختر من القائمة"
        )
        self._notes = QLineEdit()
        form.addRow(QLabel("العميل *"), self._customer)
        form.addRow(QLabel("ملاحظات العقد"), self._notes)
        self.body.addWidget(head)

        builder = Card()
        builder.layout().addWidget(heading_label("الأصناف المباعة"))
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

        terms = Card()
        tform = QFormLayout()
        terms.layout().addLayout(tform)
        self._down = QDoubleSpinBox()
        self._down.setRange(0, 1_000_000_000)
        self._down.setDecimals(2)
        self._down.valueChanged.connect(self._recompute)
        self._months = QSpinBox()
        self._months.setRange(1, 240)
        self._months.setValue(6)
        self._months.valueChanged.connect(self._recompute)
        self._interest = QDoubleSpinBox()
        self._interest.setRange(0, 1_000_000_000)
        self._interest.setDecimals(2)
        self._interest.valueChanged.connect(self._recompute)
        self._dist = QComboBox()
        self._dist.addItem("موزّعة بالتساوي على الأقساط", "even")
        self._first_due = QDateEdit()
        self._first_due.setCalendarPopup(True)
        self._first_due.setDate(QDate.currentDate().addMonths(1))
        self._summary = QLabel("")
        self._summary.setObjectName("Heading")
        self._treasury = treasury_combo(self._c)
        tform.addRow(QLabel("المقدّم"), self._down)
        tform.addRow(QLabel("مقدّم يروح لأي خزنة"), self._treasury)
        tform.addRow(QLabel("عدد الأقساط (أشهر)"), self._months)
        tform.addRow(QLabel("قيمة الفائدة"), self._interest)
        tform.addRow(QLabel("طريقة توزيع الفائدة"), self._dist)
        tform.addRow(QLabel("تاريخ أول قسط"), self._first_due)
        tform.addRow(QLabel("الملخّص"), self._summary)
        save = QPushButton("إنشاء العقد وترحيله")
        save.setEnabled(self._c.auth.can(Permissions.SALES_INSTALLMENT_CREATE))
        save.clicked.connect(self._save)
        terms.layout().addWidget(save)
        self.body.addWidget(terms)

        self._prefill_price()
        self._recompute()

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
            {"item_id": item_id, "description": item.name,
             "quantity": self._qty.value(), "unit_price": self._price.value()}
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

    def _recompute(self) -> None:
        symbol = self._c.settings.currency_symbol
        goods = sum(ln["quantity"] * ln["unit_price"] for ln in self._lines)
        financed = max(goods - self._down.value(), 0)
        schedule_total = financed + self._interest.value()
        months = self._months.value()
        per = schedule_total / months if months else 0
        self._summary.setText(
            f"إجمالي الأصناف {format_currency(goods, symbol)} | المموّل "
            f"{format_currency(financed, symbol)} | إجمالي الأقساط "
            f"{format_currency(schedule_total, symbol)} | قيمة القسط "
            f"{format_currency(per, symbol)}"
        )

    def _save(self) -> None:
        actor = self._c.auth.current_user
        actor_id = actor.id if actor else None
        try:
            # العميل: يُنشأ تلقائيًا إن كُتب اسم جديد.
            cust_text = self._customer.currentText().strip()
            if not cust_text:
                QMessageBox.information(self, "تنبيه", "اكتب اسم العميل أو اختره.")
                return
            customer_id = self._c.customers.get_or_create_by_name(cust_text, actor_id)
            self._c.installments.create_plan(
                customer_id=customer_id,
                lines=self._lines,
                down_payment=self._down.value(),
                months=self._months.value(),
                interest=self._interest.value(),
                first_due_date=self._first_due.date().toString("yyyy-MM-dd"),
                notes=self._notes.text().strip() or None,
                actor_id=actor_id,
                treasury_id=self._treasury.currentData(),
            )
        except (InstallmentsServiceError, CustomersServiceError) as exc:
            QMessageBox.warning(self, "تعذّر الإنشاء", str(exc))
            return
        QMessageBox.information(self, "تم", "تم إنشاء عقد التقسيط وترحيله.")
        self.go_back()


# ── تفاصيل عقد التقسيط ───────────────────────────────────────────────────
class InstallmentDetailPage(Page):
    def __init__(self, container: "Container", plan_id: int):
        super().__init__(container.navigator, "تفاصيل عقد التقسيط")
        self._c = container
        self._plan_id = plan_id

        collect = QPushButton("تحصيل قسط")
        collect.setEnabled(container.auth.can(Permissions.INSTALLMENTS_COLLECT))
        collect.clicked.connect(self._collect)
        printb = QPushButton("طباعة الجدول")
        printb.clicked.connect(self._print)
        pdfb = QPushButton("تصدير PDF")
        pdfb.setObjectName("Ghost")
        pdfb.clicked.connect(self._pdf)
        for b in (collect, printb, pdfb):
            self.add_action(b)

        self._stats = QHBoxLayout()
        self.body.addLayout(self._stats)
        self._info = Card()
        self.body.addWidget(self._info)
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["#", "الاستحقاق", "القيمة", "أصل", "فائدة", "المدفوع", "الحالة"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.body.addWidget(self._table, stretch=1)
        self.refresh()

    def refresh(self) -> None:
        plan = self._c.installments.get_plan(self._plan_id)
        if plan is None:
            self.go_back()
            return
        symbol = self._c.settings.currency_symbol
        today = self._c.installments.today_key()
        self.set_title(f"عقد تقسيط #{plan.id} — {plan.customer_name}")

        paid = self._c.installments.plan_paid(self._plan_id)
        remaining = plan.total_amount - paid
        installments = self._c.installments.installments(self._plan_id)
        overdue = sum(i.remaining for i in installments if i.is_overdue(today))

        while self._stats.count():
            item = self._stats.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for label, val, icon, tone in (
            ("المقدّم", plan.down_payment, "💵", "#2BB3A3"),
            ("إجمالي الأقساط", plan.total_amount, "🧾", "#4E63C7"),
            ("المدفوع", paid, "✅", "#2E9E5B"),
            ("المتبقّي", remaining, "⏳", "#E08A3C"),
            ("المتأخر", overdue, "⏰", "#E0584F"),
        ):
            self._stats.addWidget(
                StatCard(label, format_currency(val, symbol), icon=icon, tone=tone)
            )

        lay = self._info.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        lay.addWidget(heading_label("بيانات العقد"))
        lay.addWidget(QLabel(f"العميل: {plan.customer_name}"))
        lay.addWidget(QLabel(f"فاتورة البيع #: {plan.sale_id} | التاريخ: {format_iso_date(plan.sale_date)}"))
        lay.addWidget(QLabel(
            f"عدد الأقساط: {plan.months} | الحالة: "
            f"{_PLAN_STATUS_AR.get(plan.status, plan.status)}"
        ))

        self._table.setRowCount(len(installments))
        for r, ins in enumerate(installments):
            self._table.setItem(r, 0, QTableWidgetItem(str(ins.number)))
            self._table.setItem(r, 1, QTableWidgetItem(format_iso_date(ins.due_date)))
            self._table.setItem(r, 2, QTableWidgetItem(format_currency(ins.amount, symbol)))
            self._table.setItem(r, 3, QTableWidgetItem(format_currency(ins.principal, symbol)))
            self._table.setItem(r, 4, QTableWidgetItem(format_currency(ins.interest, symbol)))
            self._table.setItem(r, 5, QTableWidgetItem(format_currency(ins.paid_amount, symbol)))
            self._table.setItem(r, 6, QTableWidgetItem(_inst_status(ins, today)))

    def _collect(self) -> None:
        self._c.navigator.push(CollectPage(self._c, self._plan_id))

    def _schedule_html(self) -> str:
        plan = self._c.installments.get_plan(self._plan_id)
        symbol = self._c.settings.currency_symbol
        today = self._c.installments.today_key()
        rows = "".join(
            f"<tr><td>{i.number}</td><td>{format_iso_date(i.due_date)}</td>"
            f"<td>{format_currency(i.amount, symbol)}</td>"
            f"<td>{format_currency(i.paid_amount, symbol)}</td>"
            f"<td>{_inst_status(i, today)}</td></tr>"
            for i in self._c.installments.installments(self._plan_id)
        )
        paid = self._c.installments.plan_paid(self._plan_id)
        return (
            f"<p>العميل: {plan.customer_name} | المقدّم: "
            f"{format_currency(plan.down_payment, symbol)} | إجمالي الأقساط: "
            f"{format_currency(plan.total_amount, symbol)} | المدفوع: "
            f"{format_currency(paid, symbol)} | المتبقّي: "
            f"{format_currency(plan.total_amount - paid, symbol)}</p>"
            "<table><tr><th>#</th><th>الاستحقاق</th><th>القيمة</th><th>المدفوع</th>"
            f"<th>الحالة</th></tr>{rows}</table>"
        )

    def _print(self) -> None:
        print_html(self, build_invoice_html(self._c, f"عقد تقسيط #{self._plan_id}", self._schedule_html()), "جدول الأقساط")

    def _pdf(self) -> None:
        plan = self._c.installments.get_plan(self._plan_id)
        export_pdf(self, build_invoice_html(self._c, f"عقد تقسيط #{self._plan_id}", self._schedule_html()), f"تقسيط_{plan.customer_name}.pdf")


# ── تحصيل قسط ───────────────────────────────────────────────────────────
class CollectPage(Page):
    def __init__(self, container: "Container", plan_id: int):
        super().__init__(container.navigator, "تحصيل قسط")
        self._c = container
        self._plan_id = plan_id

        plan = container.installments.get_plan(plan_id)
        symbol = container.settings.currency_symbol
        paid = container.installments.plan_paid(plan_id)
        remaining = plan.total_amount - paid

        card = Card()
        form = QFormLayout()
        card.layout().addLayout(form)
        form.addRow(QLabel("العميل"), QLabel(plan.customer_name))
        form.addRow(QLabel("المتبقّي على العقد"), QLabel(format_currency(remaining, symbol)))
        self._amount = QDoubleSpinBox()
        self._amount.setRange(0.01, max(remaining, 0.01))
        self._amount.setDecimals(2)
        self._amount.setValue(min(remaining, self._next_due_value()))
        self._treasury = treasury_combo(container)
        form.addRow(QLabel("مبلغ التحصيل"), self._amount)
        form.addRow(QLabel("يروح لأي خزنة"), self._treasury)
        card.layout().addWidget(
            QLabel("يُوزَّع المبلغ تلقائيًا على الأقساط الأقدم فالأحدث.")
        )
        buttons = QHBoxLayout()
        save = QPushButton("تحصيل")
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

    def _next_due_value(self) -> float:
        for ins in self._c.installments.installments(self._plan_id):
            if ins.remaining > 0:
                return ins.remaining
        return 0.01

    def _save(self) -> None:
        actor = self._c.auth.current_user
        try:
            collected = self._c.installments.collect(
                self._plan_id, self._amount.value(),
                actor_id=actor.id if actor else None,
                treasury_id=self._treasury.currentData(),
            )
        except InstallmentsServiceError as exc:
            QMessageBox.warning(self, "تعذّر التحصيل", str(exc))
            return
        symbol = self._c.settings.currency_symbol
        QMessageBox.information(
            self, "تم", f"تم تحصيل {format_currency(collected, symbol)}."
        )
        self.go_back()


# ── المتأخرات ───────────────────────────────────────────────────────────
class ArrearsPage(Page):
    def __init__(self, container: "Container"):
        super().__init__(container.navigator, "المتأخرات")
        self._c = container

        self.body.addWidget(heading_label("متأخرات العملاء"))
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["العميل", "عدد الأقساط المتأخرة", "إجمالي المتأخر", "أقدم استحقاق",
             "أيام التأخير", ""]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.body.addWidget(self._table, stretch=1)

        self.body.addWidget(heading_label("مستحق اليوم"))
        self._today_table = QTableWidget(0, 4)
        self._today_table.setHorizontalHeaderLabels(
            ["العميل", "قسط #", "القيمة", "المتبقّي"]
        )
        self._today_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._today_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.body.addWidget(self._today_table, stretch=1)

        self.refresh()

    def refresh(self) -> None:
        symbol = self._c.settings.currency_symbol
        today = self._c.installments.today_key()

        rows = self._c.installments.overdue_by_customer()
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self._table.setItem(r, 0, QTableWidgetItem(row["customer_name"]))
            self._table.setItem(r, 1, QTableWidgetItem(str(row["overdue_count"])))
            self._table.setItem(
                r, 2, QTableWidgetItem(format_currency(row["overdue_amount"], symbol))
            )
            self._table.setItem(r, 3, QTableWidgetItem(format_iso_date(row["oldest_due"])))
            from datetime import date as _d
            try:
                days = (_d.fromisoformat(today) - _d.fromisoformat(row["oldest_due"])).days
            except (ValueError, TypeError):
                days = 0
            self._table.setItem(r, 4, QTableWidgetItem(str(max(days, 0))))
            open_btn = QPushButton("فتح حساب العميل")
            cid = row["customer_id"]
            open_btn.clicked.connect(lambda _c, i=cid: self._open_customer(i))
            self._table.setCellWidget(r, 5, open_btn)

        due = self._c.installments.due_today()
        self._today_table.setRowCount(len(due))
        for r, row in enumerate(due):
            remaining = (row["amount"] or 0) - (row["paid_amount"] or 0)
            self._today_table.setItem(r, 0, QTableWidgetItem(row["customer_name"] or ""))
            self._today_table.setItem(r, 1, QTableWidgetItem(str(row["number"])))
            self._today_table.setItem(
                r, 2, QTableWidgetItem(format_currency(row["amount"] or 0, symbol))
            )
            self._today_table.setItem(
                r, 3, QTableWidgetItem(format_currency(remaining, symbol))
            )

    def _open_customer(self, customer_id: int) -> None:
        from app.ui.customers.customers_view import CustomerAccountPage

        self._c.navigator.push(CustomerAccountPage(self._c, customer_id))
