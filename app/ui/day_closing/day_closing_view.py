"""شاشة الإقفال اليومي: تسوية النقد المتوقع مع المعدول وقفل اليوم."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.constants.permissions import Permissions
from app.core.utils.formatters import format_currency
from app.domain.enums import DayStatus
from app.services.day_closing_service import DayClosingError
from app.ui.components.widgets import Card, heading_label, muted_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container


class DayClosingView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        layout.addWidget(title_label("الإقفال اليومي"))

        self._card = Card()
        lay = self._card.layout()
        self._status_lbl = heading_label("")
        self._opening_lbl = QLabel("")
        self._expected_lbl = QLabel("")
        lay.addWidget(self._status_lbl)
        lay.addWidget(self._opening_lbl)
        lay.addWidget(self._expected_lbl)

        lay.addWidget(QLabel("النقد الفعلي المعدود"))
        self._counted = QDoubleSpinBox()
        self._counted.setRange(0, 1_000_000_000)
        self._counted.setDecimals(2)
        lay.addWidget(self._counted)

        lay.addWidget(QLabel("ملاحظات"))
        self._notes = QPlainTextEdit()
        self._notes.setFixedHeight(70)
        lay.addWidget(self._notes)

        self._close_btn = QPushButton("إقفال اليوم وقفله")
        self._close_btn.clicked.connect(self._close_day)
        lay.addWidget(self._close_btn)

        self._reopen_btn = QPushButton("إعادة فتح اليوم")
        self._reopen_btn.setObjectName("Danger")
        self._reopen_btn.clicked.connect(self._reopen_day)
        lay.addWidget(self._reopen_btn)

        self._result = muted_label("")
        self._result.setWordWrap(True)
        lay.addWidget(self._result)

        layout.addWidget(self._card)
        layout.addStretch(1)

    def refresh(self) -> None:
        day = self._c.day_closing.get_or_open_today()
        symbol = self._c.settings.currency_symbol
        expected = self._c.day_closing.compute_expected_cash(day)
        is_open = day.status == DayStatus.OPEN.value

        self._status_lbl.setText(
            f"اليوم: {day.business_date} — الحالة: "
            + ("مفتوح" if is_open else "مُقفل")
        )
        self._opening_lbl.setText(
            "رصيد الافتتاح: " + format_currency(day.opening_balance, symbol)
        )
        self._expected_lbl.setText(
            "النقد المتوقع: " + format_currency(expected, symbol)
        )

        can_close = is_open and self._c.auth.can(Permissions.DAY_CLOSE)
        can_reopen = (not is_open) and self._c.auth.can(Permissions.DAY_REOPEN)
        self._close_btn.setEnabled(can_close)
        self._counted.setEnabled(can_close)
        self._notes.setEnabled(can_close)
        self._reopen_btn.setVisible(not is_open)
        self._reopen_btn.setEnabled(can_reopen)

        if not is_open and day.difference is not None:
            self._result.setText(
                "المعدول: " + format_currency(day.counted_cash or 0, symbol)
                + " — الفرق: " + format_currency(day.difference, symbol)
            )
        else:
            self._result.setText("")

    def _close_day(self) -> None:
        user = self._c.auth.current_user
        if user is None:
            return
        confirm = QMessageBox.question(
            self, "تأكيد الإقفال", "بعد الإقفال لا يمكن تعديل عمليات هذا اليوم. متابعة؟"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            day = self._c.day_closing.close_day(
                counted_cash=self._counted.value(),
                closed_by=user.id,
                notes=self._notes.toPlainText().strip() or None,
            )
        except DayClosingError as exc:
            QMessageBox.warning(self, "تعذّر الإقفال", str(exc))
            return
        symbol = self._c.settings.currency_symbol
        QMessageBox.information(
            self,
            "تم الإقفال",
            "تم إقفال اليوم.\nالفرق: "
            + format_currency(day.difference or 0, symbol),
        )
        self.refresh()

    def _reopen_day(self) -> None:
        user = self._c.auth.current_user
        if user is None:
            return
        day = self._c.day_closing.get_or_open_today()
        self._c.day_closing.reopen_day(day.id, user.id)
        self.refresh()
