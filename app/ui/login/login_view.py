"""شاشة تسجيل الدخول."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.auth_service import AuthError
from app.ui.branding import application_icon
from app.ui.components.widgets import Card, muted_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container
    from app.domain.entities import User


class LoginView(QWidget):
    logged_in = pyqtSignal(object)  # يبعث كائن User عند النجاح

    def __init__(self, container: "Container"):
        super().__init__()
        self._container = container
        self.setWindowTitle("تسجيل الدخول")
        self.setMinimumSize(420, 460)
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.addStretch(1)

        card = Card()
        card.setFixedWidth(420)
        layout = card.layout()

        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = application_icon().pixmap(72, 72)
        if not pix.isNull():
            logo.setPixmap(pix)
            layout.addWidget(logo)

        brand = title_label(self._container.settings.showroom_name)
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = muted_label("نظام إدارة معرض الدراجات النارية")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(14)

        self._username = QLineEdit()
        self._username.setPlaceholderText("اسم المستخدم")
        layout.addWidget(QLabel("اسم المستخدم"))
        layout.addWidget(self._username)

        self._password = QLineEdit()
        self._password.setPlaceholderText("كلمة المرور")
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.returnPressed.connect(self._on_login)
        layout.addWidget(QLabel("كلمة المرور"))
        layout.addWidget(self._password)

        self._error = QLabel("")
        self._error.setObjectName("Danger")
        self._error.setWordWrap(True)
        layout.addWidget(self._error)

        login_btn = QPushButton("دخول")
        login_btn.clicked.connect(self._on_login)
        layout.addWidget(login_btn)

        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        outer.addStretch(1)

    def _on_login(self) -> None:
        self._error.setText("")
        try:
            user = self._container.auth.login(
                self._username.text(), self._password.text()
            )
        except AuthError as exc:
            self._error.setText(str(exc))
            return
        self.logged_in.emit(user)
