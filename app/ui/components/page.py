"""صفحة أساس بترويسة موحّدة (زر رجوع + عنوان + أزرار إجراءات).

كل الشاشات الكاملة (القوائم، النماذج، الحسابات، الكشوف) ترث منها لتوحيد الشكل
والسلوك. زر الرجوع يظهر فقط للصفحات الفرعية (المدفوعة فوق جذر الوحدة).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
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
        root.setContentsMargins(28, 22, 28, 26)
        root.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(10)
        if show_back and navigator is not None:
            back = QPushButton("رجوع")
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

        # منطقة محتوى الصفحة (تضيف الفئات الفرعية عناصرها هنا).
        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        root.addLayout(self.body, stretch=1)

    def add_action(self, button: QPushButton) -> None:
        self._actions.addWidget(button)

    def set_title(self, title: str) -> None:
        self._title_lbl.setText(title)

    def go_back(self) -> None:
        if self._navigator is not None:
            self._navigator.pop()
