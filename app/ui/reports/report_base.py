"""صفحة تقرير أساس: شريط فلاتر (تاريخ من/إلى + إضافات) + جدول + إجماليات +
طباعة/PDF. كل تقرير يرث منها ويملأ الأعمدة والصفوف والإجماليات وHTML الطباعة.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from app.ui.components.page import Page
from app.ui.components.printing import export_pdf, print_html
from app.ui.components.widgets import Card

if TYPE_CHECKING:
    from app.core.container import Container


class ReportPage(Page):
    def __init__(self, container: "Container", title: str, *, show_dates: bool = True):
        super().__init__(container.navigator, title)
        self._c = container
        self._report_title = title
        self._html = ""

        printb = QPushButton("طباعة")
        printb.clicked.connect(self._print)
        pdfb = QPushButton("تصدير PDF")
        pdfb.setObjectName("Ghost")
        pdfb.clicked.connect(self._pdf)
        self.add_action(printb)
        self.add_action(pdfb)

        bar = Card()
        frow = QHBoxLayout()
        bar.layout().addLayout(frow)
        today = QDate.currentDate()
        self._from = QDateEdit()
        self._from.setCalendarPopup(True)
        self._from.setDate(QDate(today.year(), today.month(), 1))
        self._to = QDateEdit()
        self._to.setCalendarPopup(True)
        self._to.setDate(today)
        if show_dates:
            frow.addWidget(QLabel("من"))
            frow.addWidget(self._from)
            frow.addWidget(QLabel("إلى"))
            frow.addWidget(self._to)
        self.extra_filters = QHBoxLayout()
        frow.addLayout(self.extra_filters)
        run = QPushButton("تشغيل التقرير")
        run.clicked.connect(self.run)
        frow.addWidget(run)
        frow.addStretch(1)
        self.body.addWidget(bar)

        self._totals = QLabel("")
        self._totals.setObjectName("Heading")
        self._totals.setWordWrap(True)
        self.body.addWidget(self._totals)

        self._table = QTableWidget(0, 0)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.body.addWidget(self._table, stretch=1)

    # ── أدوات للفئات الفرعية ────────────────────────────────────────────
    @property
    def dfrom(self) -> str:
        return self._from.date().toString("yyyy-MM-dd")

    @property
    def dto(self) -> str:
        return self._to.date().toString("yyyy-MM-dd")

    def set_columns(self, headers: list[str]) -> None:
        self._table.setColumnCount(len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

    def fill(self, rows: list[list[str]]) -> None:
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self._table.setItem(r, c, QTableWidgetItem(str(val)))

    def set_totals(self, text: str) -> None:
        self._totals.setText(text)

    def build_html(self, headers: list[str], rows: list[list[str]], summary: str) -> None:
        head = "".join(f"<th>{h}</th>" for h in headers)
        body = "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows
        )
        self._html = (
            f"<h2>{self._c.settings.showroom_name} — {self._report_title}</h2>"
            f"<p>{summary}</p>"
            f"<table><tr>{head}</tr>{body}</table>"
        )

    # ── طباعة/تصدير ─────────────────────────────────────────────────────
    def _print(self) -> None:
        if not self._html:
            self.run()
        print_html(self, self._html, self._report_title)

    def _pdf(self) -> None:
        if not self._html:
            self.run()
        export_pdf(self, self._html, f"{self._report_title}.pdf")

    # تُنفَّذ في الفئات الفرعية.
    def run(self) -> None:  # noqa: D401
        raise NotImplementedError
