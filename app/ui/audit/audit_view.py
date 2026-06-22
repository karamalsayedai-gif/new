"""شاشة سجل التدقيق — كاملة، إدارية.

فلاتر: نطاق تاريخ من/إلى + المستخدم + الوحدة + العملية + بحث نصي.
جدول نتائج + لوحة تفاصيل داخل الصفحة (لا popup) + تصدير PDF و CSV على النتائج
المفلترة فقط. محكومة بصلاحية AUDIT_VIEW.
"""
from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
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

from app.core.constants.audit_labels import (
    OPERATION_CATEGORIES,
    action_label,
    entity_label,
    operation_category,
)
from app.core.utils.formatters import format_iso_datetime
from app.ui.components.printing import export_pdf
from app.ui.components.widgets import Card, heading_label, muted_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container

_HEADERS = ["التاريخ والوقت", "المستخدم", "الوحدة", "العملية", "الحدث", "التفاصيل"]


class AuditView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._rows: list = []  # نتائج البحث الحالية (المفلترة)
        self._build()
        self.refresh()

    # ── البناء ──────────────────────────────────────────────────────────
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 26)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(title_label("سجل التدقيق"))
        header.addStretch(1)
        pdf = QPushButton("تصدير PDF")
        pdf.clicked.connect(self._export_pdf)
        csv_btn = QPushButton("تصدير CSV")
        csv_btn.setObjectName("Ghost")
        csv_btn.clicked.connect(self._export_csv)
        header.addWidget(pdf)
        header.addWidget(csv_btn)
        layout.addLayout(header)

        layout.addWidget(self._filters_card())

        body = QHBoxLayout()
        self._table = QTableWidget(0, len(_HEADERS))
        self._table.setHorizontalHeaderLabels(_HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.currentCellChanged.connect(lambda *_: self._show_details())
        body.addWidget(self._table, stretch=3)

        self._details = Card()
        self._details.setFixedWidth(320)
        self._details.layout().addWidget(heading_label("تفاصيل الحدث"))
        self._details_body = QVBoxLayout()
        self._details.layout().addLayout(self._details_body)
        self._details.layout().addStretch(1)
        body.addWidget(self._details, stretch=1)
        layout.addLayout(body, stretch=1)

        self._count = muted_label("")
        layout.addWidget(self._count)

    def _filters_card(self) -> Card:
        card = Card()
        row1 = QHBoxLayout()
        today = QDate.currentDate()
        self._from = QDateEdit()
        self._from.setCalendarPopup(True)
        self._from.setDate(today.addMonths(-1))
        self._to = QDateEdit()
        self._to.setCalendarPopup(True)
        self._to.setDate(today)
        row1.addWidget(QLabel("من"))
        row1.addWidget(self._from)
        row1.addWidget(QLabel("إلى"))
        row1.addWidget(self._to)

        self._user = QComboBox()
        self._user.addItem("كل المستخدمين", None)
        for u in self._c.users.list_users():
            self._user.addItem(u.username, u.id)
        row1.addWidget(QLabel("المستخدم"))
        row1.addWidget(self._user)

        self._entity = QComboBox()
        self._entity.addItem("كل الوحدات", None)
        for ent in self._c.audit.entities():
            self._entity.addItem(entity_label(ent), ent)
        row1.addWidget(QLabel("الوحدة"))
        row1.addWidget(self._entity)
        row1.addStretch(1)
        card.layout().addLayout(row1)

        row2 = QHBoxLayout()
        self._operation = QComboBox()
        self._operation.addItem("كل العمليات", None)
        for cat in OPERATION_CATEGORIES:
            self._operation.addItem(cat, cat)
        row2.addWidget(QLabel("العملية"))
        row2.addWidget(self._operation)

        self._text = QLineEdit()
        self._text.setPlaceholderText("بحث نصي في الحدث/التفاصيل/المستخدم…")
        self._text.returnPressed.connect(self.refresh)
        row2.addWidget(self._text, stretch=1)

        run = QPushButton("تطبيق الفلاتر")
        run.clicked.connect(self.refresh)
        reset = QPushButton("مسح")
        reset.setObjectName("Ghost")
        reset.clicked.connect(self._reset)
        row2.addWidget(run)
        row2.addWidget(reset)
        card.layout().addLayout(row2)
        return card

    # ── البيانات ────────────────────────────────────────────────────────
    def refresh(self) -> None:
        rows = self._c.audit.search(
            date_from=self._from.date().toString("yyyy-MM-dd"),
            date_to=self._to.date().toString("yyyy-MM-dd"),
            user_id=self._user.currentData(),
            entity=self._entity.currentData(),
            text=self._text.text(),
        )
        # فلتر العملية (تصنيف مشتق) يُطبَّق بعد الجلب.
        op = self._operation.currentData()
        if op:
            rows = [r for r in rows if operation_category(r["action"]) == op]
        self._rows = rows

        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self._table.setItem(r, 0, QTableWidgetItem(format_iso_datetime(row["created_at"])))
            self._table.setItem(r, 1, QTableWidgetItem(row["username"] or "—"))
            self._table.setItem(r, 2, QTableWidgetItem(entity_label(row["entity"])))
            self._table.setItem(r, 3, QTableWidgetItem(operation_category(row["action"])))
            self._table.setItem(r, 4, QTableWidgetItem(action_label(row["action"])))
            self._table.setItem(r, 5, QTableWidgetItem(row["details"] or ""))
        self._count.setText(f"عدد النتائج: {len(rows)}")
        self._show_details()

    def _reset(self) -> None:
        self._user.setCurrentIndex(0)
        self._entity.setCurrentIndex(0)
        self._operation.setCurrentIndex(0)
        self._text.clear()
        self._from.setDate(QDate.currentDate().addMonths(-1))
        self._to.setDate(QDate.currentDate())
        self.refresh()

    def _show_details(self) -> None:
        while self._details_body.count():
            item = self._details_body.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        row_idx = self._table.currentRow()
        if row_idx < 0 or row_idx >= len(self._rows):
            self._details_body.addWidget(muted_label("اختر سطرًا لعرض التفاصيل."))
            return
        row = self._rows[row_idx]
        fields = [
            ("المعرّف", str(row["id"])),
            ("التاريخ والوقت", format_iso_datetime(row["created_at"])),
            ("المستخدم", row["username"] or "—"),
            ("الوحدة", entity_label(row["entity"])),
            ("العملية", operation_category(row["action"])),
            ("الحدث", action_label(row["action"])),
            ("كود الحدث", row["action"]),
            ("معرّف العنصر", str(row["entity_id"]) if row["entity_id"] else "—"),
            ("التفاصيل", row["details"] or "—"),
        ]
        for label, value in fields:
            lbl = QLabel(f"{label}: {value}")
            lbl.setWordWrap(True)
            self._details_body.addWidget(lbl)

    # ── التصدير (على النتائج المفلترة فقط) ──────────────────────────────
    def _export_rows(self) -> list[list[str]]:
        return [
            [
                format_iso_datetime(r["created_at"]), r["username"] or "—",
                entity_label(r["entity"]), operation_category(r["action"]),
                action_label(r["action"]), r["details"] or "",
            ]
            for r in self._rows
        ]

    def _export_pdf(self) -> None:
        rows = self._export_rows()
        if not rows:
            QMessageBox.information(self, "تنبيه", "لا توجد نتائج للتصدير.")
            return
        head = "".join(f"<th>{h}</th>" for h in _HEADERS)
        body = "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows
        )
        html = (
            f"<h2>{self._c.settings.showroom_name} — سجل التدقيق</h2>"
            f"<p>عدد النتائج: {len(rows)}</p>"
            f"<table><tr>{head}</tr>{body}</table>"
        )
        export_pdf(self, html, "سجل_التدقيق.pdf")

    def _export_csv(self) -> None:
        rows = self._export_rows()
        if not rows:
            QMessageBox.information(self, "تنبيه", "لا توجد نتائج للتصدير.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "تصدير CSV", "audit_log.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(_HEADERS)
                writer.writerows(rows)
        except OSError as exc:
            QMessageBox.critical(self, "خطأ", f"تعذّر حفظ الملف: {exc}")
            return
        QMessageBox.information(self, "تم", f"تم تصدير {len(rows)} سطرًا إلى:\n{path}")
