"""FlowLayout: تخطيط يلتفّ تلقائيًا للسطر التالي عند ضيق العرض.

يحلّ مشكلة «شريط الخانات/الأزرار» الذي كان يُقصّ عند تضييق النافذة: بدل صفّ أفقي
ثابت، تنتقل العناصر الزائدة لسطر جديد تلقائيًا. مبني على مثال Qt الرسمي ومكيّف
لـ PyQt6 مع دعم اتجاه RTL.
"""
from __future__ import annotations

from PyQt6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PyQt6.QtWidgets import QLayout, QLayoutItem, QSizePolicy, QWidget


class FlowLayout(QLayout):
    def __init__(
        self,
        parent: QWidget | None = None,
        margin: int = 0,
        h_spacing: int = 8,
        v_spacing: int = 8,
    ):
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h_space = h_spacing
        self._v_space = v_spacing
        self.setContentsMargins(QMargins(margin, margin, margin, margin))

    def __del__(self):
        while self._items:
            self._items.pop()

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(), margins.top() + margins.bottom()
        )
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective = rect.adjusted(
            margins.left(), margins.top(), -margins.right(), -margins.bottom()
        )
        # RTL: نبدأ من اليمين ونتجه لليسار.
        right = effective.right()
        x = right
        y = effective.y()
        line_height = 0

        for item in self._items:
            hint = item.sizeHint()
            next_x = x - hint.width()
            if next_x < effective.x() and line_height > 0:
                x = right
                y = y + line_height + self._v_space
                next_x = x - hint.width()
                line_height = 0
            if not test_only:
                item.setGeometry(
                    QRect(QPoint(next_x, y), hint)
                )
            x = next_x - self._h_space
            line_height = max(line_height, hint.height())

        return y + line_height - rect.y() + margins.bottom()


def toolbar(widgets: list[QWidget]) -> QWidget:
    """حاوية أدوات تلتفّ تلقائيًا (لا تُقصّ عناصرها عند ضيق العرض)."""
    holder = QWidget()
    holder.setObjectName("Toolbar")
    layout = FlowLayout(holder, margin=0, h_spacing=8, v_spacing=8)
    for w in widgets:
        layout.addWidget(w)
    holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    return holder
