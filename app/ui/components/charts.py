"""عنصر رسم مخطط أعمدة بسيط عبر QPainter (بلا أي اعتماديات خارجية).

يتكيّف مع لون القالب الحالي (highlight) ويعرض القيم والعناوين. يُستخدم في تقرير
الملخص البياني.
"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QWidget


class BarChart(QWidget):
    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._title = title
        self._data: list[tuple[str, float]] = []
        self.setMinimumHeight(220)

    def set_data(self, data: list[tuple[str, float]]) -> None:
        self._data = data
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        text_color = self.palette().text().color()
        bar_color = self.palette().highlight().color()
        muted = QColor(text_color)
        muted.setAlpha(150)

        # العنوان
        painter.setPen(text_color)
        title_font = QFont(self.font())
        base_pt = title_font.pointSize()
        if base_pt <= 0:
            base_pt = 10
        title_font.setBold(True)
        title_font.setPointSize(base_pt + 1)
        painter.setFont(title_font)
        painter.drawText(
            QRectF(0, 4, w, 24), Qt.AlignmentFlag.AlignCenter, self._title
        )

        painter.setFont(self.font())
        top = 34
        bottom = h - 28
        left = 10
        right = w - 10
        if not self._data:
            painter.setPen(muted)
            painter.drawText(
                QRectF(0, top, w, bottom - top),
                Qt.AlignmentFlag.AlignCenter, "لا توجد بيانات",
            )
            painter.end()
            return

        max_val = max((v for _, v in self._data), default=0) or 1
        n = len(self._data)
        gap = 12
        avail = (right - left) - gap * (n + 1)
        bw = max(avail / n, 6)
        x = left + gap
        for label, value in self._data:
            bh = (bottom - top) * (value / max_val) if max_val else 0
            rect = QRectF(x, bottom - bh, bw, bh)
            painter.fillRect(rect, bar_color)
            # القيمة فوق العمود
            painter.setPen(text_color)
            painter.drawText(
                QRectF(x - 6, bottom - bh - 18, bw + 12, 16),
                Qt.AlignmentFlag.AlignCenter, _fmt(value),
            )
            # التسمية أسفل العمود
            painter.setPen(muted)
            painter.drawText(
                QRectF(x - 6, bottom + 4, bw + 12, 20),
                Qt.AlignmentFlag.AlignCenter, label,
            )
            x += bw + gap
        painter.end()


def _fmt(v: float) -> str:
    if v >= 1000:
        return f"{v/1000:.1f}k"
    return f"{v:.0f}"
