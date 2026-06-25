"""مكوّنات واجهة مشتركة قابلة لإعادة الاستخدام.

تعتمد على أسماء كائنات دلالية (objectName) يُنسّقها القالب عالميًا، بدلًا من
تنسيقات سطرية متفرّقة داخل كل widget.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.theme.palette import lighten


def _soft(hex_color: str) -> str:
    """خلفية باستيل ناعمة مشتقّة من لون الأيقونة (لمربّع الأيقونة في البطاقات)."""
    return lighten(hex_color, 0.82)


def status_pill(text: str, kind: str = "muted") -> QLabel:
    """شارة حالة دائرية ملوّنة (success / warning / danger / muted)."""
    names = {
        "success": "PillSuccess",
        "warning": "PillWarning",
        "danger": "PillDanger",
        "muted": "PillMuted",
    }
    label = QLabel(text)
    label.setObjectName(names.get(kind, "PillMuted"))
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def add_shadow(widget: QWidget, *, blur: int = 22, dy: int = 4, alpha: int = 22) -> None:
    """ظل ناعم خفيف تحت الكروت (إحساس العمق الهادئ في لوحات التحكم العصرية)."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(dy)
    effect.setColor(QColor(17, 24, 39, alpha))
    widget.setGraphicsEffect(effect)


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
        add_shadow(self)

    def layout(self) -> QVBoxLayout:  # type: ignore[override]
        return self._layout


class StatCard(QFrame):
    """بطاقة إحصائية للوحة التحكم: عنوان + قيمة كبيرة + أيقونة ملوّنة اختيارية.

    على نمط لوحات التحكم العصرية: العنوان والقيمة على جهة، وأيقونة داخل مربّع
    بخلفية باستيل ناعمة على الجهة الأخرى.
    """

    def __init__(
        self,
        label: str,
        value: str = "0",
        icon: str = "",
        tone: str = "",
        hint: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setMinimumHeight(104)
        add_shadow(self)

        row = QHBoxLayout(self)
        row.setContentsMargins(20, 18, 20, 18)
        row.setSpacing(14)

        texts = QVBoxLayout()
        texts.setSpacing(6)
        self._label = QLabel(label)
        self._label.setObjectName("StatLabel")
        self._value = QLabel(value)
        self._value.setObjectName("StatValue")
        texts.addWidget(self._label)
        texts.addWidget(self._value)
        self._hint = QLabel(hint)
        self._hint.setObjectName("StatHint")
        self._hint.setVisible(bool(hint))
        texts.addWidget(self._hint)
        texts.addStretch(1)
        row.addLayout(texts)
        row.addStretch(1)

        if icon:
            tone = tone or "#8A90A0"
            chip = QLabel(icon)
            chip.setObjectName("StatChip")
            chip.setFixedSize(52, 52)
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip.setStyleSheet(
                f"background:{_soft(tone)}; color:{tone}; border-radius:14px;"
            )
            row.addWidget(chip, alignment=Qt.AlignmentFlag.AlignTop)

    def set_value(self, value: str) -> None:
        self._value.setText(value)

    def set_hint(self, hint: str) -> None:
        self._hint.setText(hint)
        self._hint.setVisible(bool(hint))


def scroll_area(content: QWidget) -> QScrollArea:
    """يلفّ عنصرًا داخل منطقة تمرير عمودية بلا إطار (لتمرير الصفحات الطويلة)."""
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setWidget(content)
    return sa


def center(widget: QWidget) -> QWidget:
    """يلفّ widget داخل حاوية تجعله في المنتصف."""
    wrapper = QWidget()
    layout = QVBoxLayout(wrapper)
    layout.addStretch(1)
    layout.addWidget(widget, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addStretch(1)
    return wrapper
