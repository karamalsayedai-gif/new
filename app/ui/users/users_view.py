"""شاشة المستخدمين: عرض القائمة وإضافة مستخدم جديد (أساس المرحلة 2)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.constants.permissions import Permissions
from app.services.users_service import UsersServiceError
from app.ui.components.widgets import title_label

if TYPE_CHECKING:
    from app.core.container import Container


class UsersView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.addWidget(title_label("المستخدمون والصلاحيات"))
        header.addStretch(1)
        add_btn = QPushButton("إضافة مستخدم")
        add_btn.setEnabled(self._c.auth.can(Permissions.USERS_MANAGE))
        add_btn.clicked.connect(self._add_user)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["المعرّف", "اسم المستخدم", "الاسم الكامل", "الدور"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

    def refresh(self) -> None:
        users = self._c.users.list_users()
        self._table.setRowCount(len(users))
        for row, user in enumerate(users):
            self._table.setItem(row, 0, QTableWidgetItem(str(user.id)))
            self._table.setItem(row, 1, QTableWidgetItem(user.username))
            self._table.setItem(row, 2, QTableWidgetItem(user.full_name))
            self._table.setItem(row, 3, QTableWidgetItem(user.role_name))

    def _add_user(self) -> None:
        dialog = _AddUserDialog(self._c, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()


class _AddUserDialog(QDialog):
    def __init__(self, container: "Container", parent: QWidget):
        super().__init__(parent)
        self._c = container
        self.setWindowTitle("إضافة مستخدم")
        self.setMinimumWidth(360)

        form = QFormLayout(self)
        self._username = QLineEdit()
        self._full_name = QLineEdit()
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._role = QComboBox()
        for role in self._c.users.list_roles():
            self._role.addItem(role.name, role.id)

        form.addRow(QLabel("اسم المستخدم"), self._username)
        form.addRow(QLabel("الاسم الكامل"), self._full_name)
        form.addRow(QLabel("كلمة المرور"), self._password)
        form.addRow(QLabel("الدور"), self._role)

        buttons = QHBoxLayout()
        save = QPushButton("حفظ")
        save.clicked.connect(self._save)
        cancel = QPushButton("إلغاء")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        form.addRow(buttons)

    def _save(self) -> None:
        actor = self._c.auth.current_user
        try:
            self._c.users.create_user(
                username=self._username.text(),
                full_name=self._full_name.text(),
                password=self._password.text(),
                role_id=self._role.currentData(),
                actor_id=actor.id if actor else None,
            )
        except UsersServiceError as exc:
            QMessageBox.warning(self, "تعذّر الحفظ", str(exc))
            return
        self.accept()
