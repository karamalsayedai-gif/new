"""صفحات المرتجعات الكاملة (بيع/شراء).

تعرض بنود الفاتورة الأصلية مع حقل كمية إرجاع لكل بند (محدود بالمتاح) + مبلغ
مُعاد نقدًا، ثم تُرحّل المرتجع (يعكس المخزون والخزينة والحساب).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

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
    QWidget,
)

from app.core.utils.formatters import format_currency, format_number
from app.services.returns_service import ReturnsServiceError
from app.ui.components.page import Page
from app.ui.components.widgets import Card, heading_label

if TYPE_CHECKING:
    from app.core.container import Container


class _ReturnPageBase(Page):
    def __init__(self, container: "Container", title: str):
        super().__init__(container.navigator, title)
        self._c = container
        self._rows: list[dict] = []  # {item_id, description, unit_price, spin}

        info = Card()
        self._info_lay = info.layout()
        self.body.addWidget(info)
        self._info_lay.addWidget(heading_label(self._header_text()))

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["الصنف", "في الفاتورة", "أُرجع سابقًا", "متاح للإرجاع", "كمية الإرجاع"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.body.addWidget(self._table, stretch=1)

        footer = Card()
        fform = QFormLayout()
        footer.layout().addLayout(fform)
        self._refund = QDoubleSpinBox()
        self._refund.setRange(0, 1_000_000_000)
        self._refund.setDecimals(2)
        self._notes = QLineEdit()
        fform.addRow(QLabel("المبلغ المُعاد نقدًا"), self._refund)
        fform.addRow(QLabel("ملاحظات"), self._notes)
        post = QPushButton("ترحيل المرتجع")
        post.clicked.connect(self._post)
        footer.layout().addWidget(post)
        self.body.addWidget(footer)

        self._load()

    # تُنفَّذ في الفئات الفرعية:
    def _header_text(self) -> str: raise NotImplementedError
    def _source_lines(self) -> list[dict]: raise NotImplementedError
    def _do_post(self, lines, refund, notes): raise NotImplementedError

    def _load(self) -> None:
        lines = self._source_lines()
        self._table.setRowCount(len(lines))
        self._rows = []
        symbol = self._c.settings.currency_symbol
        for r, ln in enumerate(lines):
            available = ln["available"]
            self._table.setItem(r, 0, QTableWidgetItem(ln["description"]))
            self._table.setItem(r, 1, QTableWidgetItem(format_number(ln["sold"])))
            self._table.setItem(r, 2, QTableWidgetItem(format_number(ln["returned"])))
            self._table.setItem(r, 3, QTableWidgetItem(format_number(available)))
            spin = QDoubleSpinBox()
            spin.setRange(0, max(available, 0))
            spin.setDecimals(2)
            self._table.setCellWidget(r, 4, spin)
            self._rows.append({
                "item_id": ln["item_id"], "description": ln["description"],
                "unit_price": ln["unit_price"], "spin": spin,
            })

    def _collect(self) -> list[dict]:
        out = []
        for row in self._rows:
            qty = row["spin"].value()
            if qty > 0:
                out.append({
                    "item_id": row["item_id"], "description": row["description"],
                    "quantity": qty, "unit_price": row["unit_price"],
                })
        return out

    def _post(self) -> None:
        lines = self._collect()
        if not lines:
            QMessageBox.information(self, "تنبيه", "حدّد كمية إرجاع لبند واحد على الأقل.")
            return
        actor = self._c.auth.current_user
        try:
            self._do_post(lines, self._refund.value(),
                          self._notes.text().strip() or None,
                          actor.id if actor else None)
        except ReturnsServiceError as exc:
            QMessageBox.warning(self, "تعذّر الترحيل", str(exc))
            return
        QMessageBox.information(self, "تم", "تم ترحيل المرتجع.")
        self.go_back()


class SaleReturnPage(_ReturnPageBase):
    def __init__(self, container: "Container", sale_id: int):
        self._sale_id = sale_id
        super().__init__(container, "مرتجع مبيعات")

    def _header_text(self) -> str:
        sale = self._c.sales.get(self._sale_id)
        return f"مرتجع للفاتورة {sale.display_no} — {sale.customer_name or 'نقدي'}"

    def _source_lines(self) -> list[dict]:
        already = self._c.returns_repo.returned_qty("sale", self._sale_id)
        lines = []
        for it in self._c.sales.items(self._sale_id):
            if it.item_id is None:
                continue
            ret = already.get(it.item_id, 0)
            lines.append({
                "item_id": it.item_id, "description": it.description,
                "unit_price": it.unit_price, "sold": it.quantity, "returned": ret,
                "available": it.quantity - ret,
            })
        return lines

    def _do_post(self, lines, refund, notes, actor_id):
        self._c.returns.create_sale_return(
            sale_id=self._sale_id, lines=lines, refund=refund, notes=notes,
            actor_id=actor_id,
        )


class PurchaseReturnPage(_ReturnPageBase):
    def __init__(self, container: "Container", purchase_id: int):
        self._purchase_id = purchase_id
        super().__init__(container, "مرتجع مشتريات")

    def _header_text(self) -> str:
        p = self._c.purchases.get(self._purchase_id)
        return f"مرتجع للفاتورة {p.display_no} — {p.supplier_name}"

    def _source_lines(self) -> list[dict]:
        already = self._c.returns_repo.returned_qty("purchase", self._purchase_id)
        lines = []
        for it in self._c.purchases.items(self._purchase_id):
            if it.item_id is None:
                continue
            ret = already.get(it.item_id, 0)
            lines.append({
                "item_id": it.item_id, "description": it.description,
                "unit_price": it.unit_cost, "sold": it.quantity, "returned": ret,
                "available": it.quantity - ret,
            })
        return lines

    def _do_post(self, lines, refund, notes, actor_id):
        self._c.returns.create_purchase_return(
            purchase_id=self._purchase_id, lines=lines, refund=refund, notes=notes,
            actor_id=actor_id,
        )
