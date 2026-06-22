"""مكوّنات واجهة مشتركة قابلة لإعادة الاستخدام.

تعتمد على أسماء كائنات دلالية (objectName) يُنسّقها القالب عالميًا، بدلًا من
تنسيقات سطرية متفرّقة داخل كل widget.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


def title_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Title")
    return label


def heading_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Heading")
    return label


def muted_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Muted")
    return label


class Card(QFrame):
    """بطاقة محتوى عامة (يُنسّقها القالب عبر #Card)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(10)

    def layout(self) -> QVBoxLayout:  # type: ignore[override]
        return self._layout


class StatCard(QFrame):
    """بطاقة إحصائية للوحة التحكم: قيمة كبيرة + عنوان."""

    def __init__(self, label: str, value: str = "0", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(6)

        self._value = QLabel(value)
        self._value.setObjectName("StatValue")
        self._label = QLabel(label)
        self._label.setObjectName("StatLabel")

        layout.addWidget(self._value)
        layout.addWidget(self._label)
        layout.addStretch(1)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


def center(widget: QWidget) -> QWidget:
    """يلفّ widget داخل حاوية تجعله في المنتصف."""
    wrapper = QWidget()
    layout = QVBoxLayout(wrapper)
    layout.addStretch(1)
    layout.addWidget(widget, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addStretch(1)
    return wrapper
