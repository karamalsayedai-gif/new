"""مكوّنات واجهة مشتركة قابلة لإعادة الاستخدام.

تعتمد على أسماء كائنات دلالية (objectName) يُنسّقها القالب عالميًا، بدلًا من
تنسيقات سطرية متفرّقة داخل كل widget.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def treasury_combo(container, *, current_id: int | None = None) -> QComboBox:
    """قائمة منسدلة بالخزائن النشطة، مع تحديد الخزنة الافتراضية (أو المحددة)."""
    cb = QComboBox()
    accounts = container.treasury.active_accounts()
    target = current_id if current_id is not None else container.treasury.default_account_id()
    for acc in accounts:
        cb.addItem(acc["name"], acc["id"])
        if acc["id"] == target:
            cb.setCurrentIndex(cb.count() - 1)
    return cb

from app.theme.palette import darken, lighten


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
        self.setMinimumHeight(96)
        add_shadow(self, alpha=14)

        tone = tone or "#5B6473"
        soft = _soft(tone)
        brd = lighten(tone, 0.55)
        val_color = darken(tone, 0.16)
        # بطاقة ملوّنة بدرجة باستيل ناعمة (على نمط كروت الملخّص في التقارير).
        self.setStyleSheet(
            f"#StatCard {{ background: {soft}; border: 1px solid {brd};"
            f" border-radius: 16px; }}"
        )

        col = QVBoxLayout(self)
        col.setContentsMargins(18, 16, 18, 16)
        col.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)
        self._label = QLabel(label)
        self._label.setObjectName("StatLabel")
        self._label.setStyleSheet(f"color:{darken(tone, 0.05)}; font-weight:700;")
        top.addWidget(self._label)
        top.addStretch(1)
        if icon:
            chip = QLabel(icon)
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip.setStyleSheet("background: transparent; font-size: 17px;")
            top.addWidget(chip)
        col.addLayout(top)

        self._value = QLabel(value)
        self._value.setObjectName("StatValue")
        self._value.setStyleSheet(f"color:{val_color}; font-weight:800;")
        col.addWidget(self._value)

        self._hint = QLabel(hint)
        self._hint.setObjectName("StatHint")
        self._hint.setStyleSheet(f"color:{darken(tone, 0.02)};")
        self._hint.setVisible(bool(hint))
        col.addWidget(self._hint)
        col.addStretch(1)

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
