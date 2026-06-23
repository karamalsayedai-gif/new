"""مدير التنقّل بين الصفحات الكاملة داخل منطقة محتوى التطبيق.

يعتمد مبدأ "صفحة كاملة لكل شيء": لا نوافذ منبثقة للشاشات الأساسية. أي تفاصيل
أو كشف حساب أو سجل حركة يُدفع كصفحة كاملة فوق المكدّس، مع زر رجوع.

- ``reset_to``: استبدال كامل المكدّس بجذر وحدة جديد (عند تبديل الوحدة من الشريط).
- ``push``: دفع صفحة تفاصيل فوق الحالية.
- ``pop``: الرجوع للصفحة السابقة (وتحديثها إن دعمت refresh).
"""
from __future__ import annotations

from PyQt6.QtWidgets import QStackedWidget, QWidget


class Navigator:
    def __init__(self, stack: QStackedWidget):
        self._stack = stack
        self._pages: list[QWidget] = []

    @property
    def depth(self) -> int:
        return len(self._pages)

    def current(self) -> QWidget | None:
        return self._pages[-1] if self._pages else None

    def can_go_back(self) -> bool:
        return len(self._pages) > 1

    def reset_to(self, widget: QWidget) -> None:
        """مسح المكدّس بالكامل وعرض جذر جديد."""
        while self._pages:
            old = self._pages.pop()
            self._stack.removeWidget(old)
            old.deleteLater()
        self._pages.append(widget)
        self._stack.addWidget(widget)
        self._stack.setCurrentWidget(widget)

    def push(self, widget: QWidget) -> None:
        self._pages.append(widget)
        self._stack.addWidget(widget)
        self._stack.setCurrentWidget(widget)

    def pop(self) -> None:
        if len(self._pages) <= 1:
            return
        top = self._pages.pop()
        self._stack.removeWidget(top)
        top.deleteLater()
        current = self._pages[-1]
        self._stack.setCurrentWidget(current)
        refresh = getattr(current, "refresh", None)
        if callable(refresh):
            refresh()
