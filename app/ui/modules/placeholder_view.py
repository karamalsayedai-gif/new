"""صفحة عنصر نائب للوحدات التي ستُبنى في المرحلة 3."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from app.ui.components.widgets import muted_label, title_label


class PlaceholderView(QWidget):
    def __init__(self, title: str, note: str = "هذه الوحدة قيد التطوير (المرحلة 3)."):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.addWidget(title_label(title))
        layout.addWidget(muted_label(note))
        layout.addStretch(1)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
