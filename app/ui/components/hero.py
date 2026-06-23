"""بانر هندسي مرسوم (QPainter) لإضافة هوية بصرية عصرية «2027».

يرسم تدرّجًا لونيًا مع أشكال هندسية (دوائر/مضلّعات/خطوط قطرية شبه شفافة) بألوان
القالب الحالي، وفوقها عنوان ووصف. يُعاد بناؤه عند تبديل القالب فيقرأ ألوانًا جديدة.
لا يعتمد على صور خارجية — كله رسم متجهي خفيف.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPolygonF,
)
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from app.core.container import Container


def _color(token: str, fallback: str) -> QColor:
    c = QColor(token) if token else QColor(fallback)
    return c if c.isValid() else QColor(fallback)


class HeroBanner(QWidget):
    """شريط ترحيبي هندسي بعنوان ووصف وقيمة بارزة اختيارية."""

    def __init__(
        self,
        container: "Container",
        title: str,
        subtitle: str = "",
        badge: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._c = container
        self._title = title
        self._subtitle = subtitle
        self._badge = badge
        self.setMinimumHeight(140)
        self.setMaximumHeight(168)

    def set_texts(self, title: str, subtitle: str = "", badge: str = "") -> None:
        self._title = title
        self._subtitle = subtitle
        self._badge = badge
        self.update()

    def _tok(self, name: str, fallback: str) -> QColor:
        theme = self._c.theme
        value = theme.token(name) if theme is not None else ""
        return _color(value, fallback)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        rect = QRectF(0, 0, w, h)
        radius = 20.0

        primary = self._tok("primary", "#1D4ED8")
        accent = self._tok("accent", "#06B6D4")
        dark = self._tok("primary_dark", "#163FA8")
        on_primary = self._tok("on_primary", "#FFFFFF")

        # مسار مقصوص بزوايا دائرية للبطاقة كلها.
        clip = QPainterPath()
        clip.addRoundedRect(rect, radius, radius)
        p.setClipPath(clip)

        # تدرّج خلفي قطري.
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, dark)
        grad.setColorAt(0.55, primary)
        grad.setColorAt(1.0, accent)
        p.fillRect(rect, QBrush(grad))

        # أشكال هندسية شبه شفافة (دوائر + مضلّع + خطوط قطرية).
        light = QColor(255, 255, 255)
        light.setAlpha(28)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(light)
        p.drawEllipse(QPointF(w - 70, h - 30), 120, 120)
        faint = QColor(255, 255, 255, 18)
        p.setBrush(faint)
        p.drawEllipse(QPointF(w - 150, 20), 80, 80)

        tri = QPolygonF(
            [QPointF(w - 260, h), QPointF(w - 120, h - 90), QPointF(w - 120, h)]
        )
        p.setBrush(QColor(255, 255, 255, 14))
        p.drawPolygon(tri)

        # خطوط قطرية رفيعة.
        line = QColor(255, 255, 255, 22)
        p.setPen(line)
        for i in range(6):
            x = w - 320 + i * 26
            p.drawLine(int(x), h, int(x + 70), h - 70)

        # النصوص (نلتزم اتجاه RTL: المحاذاة لليمين).
        p.setClipping(False)
        margin = 26
        text_rect = QRectF(margin, 0, w - margin * 2, h)

        p.setPen(on_primary)
        title_font = QFont(self.font())
        title_font.setPointSize(max(self.font().pointSize(), 11) + 9)
        title_font.setWeight(QFont.Weight.Black)
        p.setFont(title_font)
        p.drawText(
            text_rect.adjusted(0, 26, 0, 0),
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop),
            self._title,
        )

        if self._subtitle:
            sub_color = QColor(on_primary)
            sub_color.setAlpha(220)
            p.setPen(sub_color)
            sub_font = QFont(self.font())
            sub_font.setPointSize(max(self.font().pointSize(), 10) + 1)
            p.setFont(sub_font)
            p.drawText(
                text_rect.adjusted(0, 70, 0, 0),
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop),
                self._subtitle,
            )

        if self._badge:
            badge_font = QFont(self.font())
            badge_font.setPointSize(max(self.font().pointSize(), 10) + 6)
            badge_font.setWeight(QFont.Weight.Black)
            p.setFont(badge_font)
            p.setPen(on_primary)
            p.drawText(
                QRectF(margin, 0, w - margin * 2, h - 18),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom),
                self._badge,
            )
        p.end()
