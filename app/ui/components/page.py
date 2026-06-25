"""صفحة أساس بترويسة موحّدة (زر رجوع + عنوان + أزرار إجراءات) + محتوى قابل للتمرير.

كل الشاشات الكاملة (القوائم، النماذج، الحسابات، الكشوف) ترث منها لتوحيد الشكل
والسلوك. منطقة المحتوى (``self.body``) داخل QScrollArea فتُمرَّر تلقائيًا عند
طول المحتوى. زر الرجوع يظهر فقط للصفحات الفرعية.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from app.ui.shell.navigator import Navigator


class Page(QWidget):
    def __init__(
        self,
        navigator: "Navigator | None",
        title: str,
        *,
        show_back: bool = True,
    ):
        super().__init__()
        self._navigator = navigator
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 26)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(10)
        if show_back and navigator is not None:
            back = QPushButton("◄ رجوع")
            back.setObjectName("Ghost")
            back.clicked.connect(navigator.pop)
            header.addWidget(back)

        self._title_lbl = QLabel(title)
        self._title_lbl.setObjectName("Title")
        header.addWidget(self._title_lbl)
        header.addStretch(1)

        self._actions = QHBoxLayout()
        self._actions.setSpacing(8)
        header.addLayout(self._actions)
        root.addLayout(header)

        # منطقة محتوى قابلة للتمرير.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.body = QVBoxLayout(content)
        self.body.setContentsMargins(2, 2, 2, 2)
        self.body.setSpacing(12)
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

    def add_action(self, button: QPushButton) -> None:
        self._actions.addWidget(button)

    def set_title(self, title: str) -> None:
        self._title_lbl.setText(title)

    def go_back(self) -> None:
        if self._navigator is not None:
            self._navigator.pop()
