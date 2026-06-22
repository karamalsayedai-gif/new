"""شاشة الإعداد لأول مرة: اسم المعرض + إنشاء حساب المدير."""
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

from app.core.constants.setting_keys import SettingKeys
from app.services.auth_service import AuthError
from app.ui.components.widgets import Card, muted_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container


class SetupView(QWidget):
    completed = pyqtSignal(object)  # يبعث كائن User (المدير) عند الإتمام

    def __init__(self, container: "Container"):
        super().__init__()
        self._container = container
        self.setWindowTitle("الإعداد الأولي")
        self.setMinimumSize(460, 560)
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 30, 40, 30)
        outer.addStretch(1)

        card = Card()
        layout = card.layout()
        layout.addWidget(title_label("مرحبًا بك 👋"))
        layout.addWidget(muted_label("لنُجهّز نظامك: بيانات المعرض وحساب المدير."))
        layout.addSpacing(8)

        self._showroom = QLineEdit()
        self._showroom.setPlaceholderText("اسم المعرض")
        layout.addWidget(QLabel("اسم المعرض"))
        layout.addWidget(self._showroom)

        self._full_name = QLineEdit()
        self._full_name.setPlaceholderText("الاسم الكامل للمدير")
        layout.addWidget(QLabel("اسم المدير"))
        layout.addWidget(self._full_name)

        self._username = QLineEdit()
        self._username.setPlaceholderText("اسم المستخدم للدخول")
        layout.addWidget(QLabel("اسم المستخدم"))
        layout.addWidget(self._username)

        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(QLabel("كلمة المرور"))
        layout.addWidget(self._password)

        self._confirm = QLineEdit()
        self._confirm.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(QLabel("تأكيد كلمة المرور"))
        layout.addWidget(self._confirm)

        self._error = QLabel("")
        self._error.setObjectName("Danger")
        self._error.setWordWrap(True)
        layout.addWidget(self._error)

        btn = QPushButton("إنشاء وبدء الاستخدام")
        btn.clicked.connect(self._on_submit)
        layout.addWidget(btn)

        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        outer.addStretch(1)

    def _on_submit(self) -> None:
        self._error.setText("")
        showroom = self._showroom.text().strip()
        full_name = self._full_name.text().strip()
        username = self._username.text().strip()
        password = self._password.text()

        if not showroom or not full_name or not username or not password:
            self._error.setText("جميع الحقول مطلوبة.")
            return
        if len(password) < 4:
            self._error.setText("كلمة المرور قصيرة جدًا (4 أحرف على الأقل).")
            return
        if password != self._confirm.text():
            self._error.setText("كلمتا المرور غير متطابقتين.")
            return

        try:
            user = self._container.auth.create_first_admin(
                username, full_name, password
            )
        except AuthError as exc:
            self._error.setText(str(exc))
            return

        self._container.settings.set(SettingKeys.SHOWROOM_NAME, showroom)
        self._container.settings.mark_setup_completed()
        self.completed.emit(user)
