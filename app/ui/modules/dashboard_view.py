"""لوحة التحكم: بطاقات إحصائية سريعة + حالة اليوم."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QGridLayout,
    QVBoxLayout,
    QWidget,
)

from app.core.utils.formatters import format_currency
from app.domain.enums import DayStatus
from app.ui.components.widgets import StatCard, muted_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container


class DashboardView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._container = container
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        user = self._container.auth.current_user
        name = user.full_name if user else ""
        layout.addWidget(title_label(f"لوحة التحكم — أهلًا {name}"))
        layout.addWidget(muted_label(self._container.settings.showroom_name))

        grid = QGridLayout()
        grid.setSpacing(16)
        self._balance = StatCard("رصيد الصندوق")
        self._day_status = StatCard("حالة اليوم")
        self._expected_cash = StatCard("النقد المتوقع")
        self._opening = StatCard("رصيد الافتتاح")
        grid.addWidget(self._balance, 0, 0)
        grid.addWidget(self._day_status, 0, 1)
        grid.addWidget(self._expected_cash, 0, 2)
        grid.addWidget(self._opening, 0, 3)
        layout.addLayout(grid)
        layout.addStretch(1)

    def refresh(self) -> None:
        day = self._container.day_closing.get_or_open_today()
        symbol = self._container.settings.currency_symbol
        status_ar = "مفتوح" if day.status == DayStatus.OPEN.value else "مُقفل"
        self._balance.set_value(
            format_currency(self._container.treasury.current_balance(), symbol)
        )
        self._day_status.set_value(status_ar)
        expected = self._container.day_closing.compute_expected_cash(day)
        self._expected_cash.set_value(format_currency(expected, symbol))
        self._opening.set_value(format_currency(day.opening_balance, symbol))
