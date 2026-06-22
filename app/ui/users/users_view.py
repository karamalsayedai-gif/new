"""شاشة المستخدمين والصلاحيات (تبويبان):

- المستخدمون: عرض/إضافة، تفعيل/تعطيل، إعادة تعيين كلمة المرور.
- الأدوار والصلاحيات: مصفوفة صلاحيات لكل دور (RBAC) قابلة للتعديل والحفظ.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.constants.permission_groups import group_label
from app.core.constants.permissions import Permissions
from app.services.users_service import UsersServiceError
from app.ui.components.page import Page
from app.ui.components.widgets import Card, heading_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container


class UsersView(QTabWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._users_tab = _UsersTab(container)
        self._roles_tab = _RolesTab(container)
        self.addTab(self._users_tab, "المستخدمون")
        self.addTab(self._roles_tab, "الأدوار والصلاحيات")

    def refresh(self) -> None:
        self._users_tab.refresh()
        self._roles_tab.refresh()


# ── تبويب المستخدمين ────────────────────────────────────────────────────
class _UsersTab(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._can_manage = container.auth.can(Permissions.USERS_MANAGE)
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(title_label("المستخدمون"))
        header.addStretch(1)
        add_btn = QPushButton("إضافة مستخدم")
        add_btn.setEnabled(self._can_manage)
        add_btn.clicked.connect(self._add_user)
        toggle_btn = QPushButton("تفعيل / تعطيل")
        toggle_btn.setObjectName("Ghost")
        toggle_btn.setEnabled(self._can_manage)
        toggle_btn.clicked.connect(self._toggle_active)
        reset_btn = QPushButton("تعيين كلمة مرور")
        reset_btn.setObjectName("Ghost")
        reset_btn.setEnabled(self._can_manage)
        reset_btn.clicked.connect(self._reset_password)
        for b in (add_btn, toggle_btn, reset_btn):
            header.addWidget(b)
        layout.addLayout(header)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["المعرّف", "اسم المستخدم", "الاسم الكامل", "الدور", "الحالة"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._table)

    def refresh(self) -> None:
        users = self._c.users.list_users()
        self._table.setRowCount(len(users))
        for r, u in enumerate(users):
            self._table.setItem(r, 0, QTableWidgetItem(str(u.id)))
            self._table.setItem(r, 1, QTableWidgetItem(u.username))
            self._table.setItem(r, 2, QTableWidgetItem(u.full_name))
            self._table.setItem(r, 3, QTableWidgetItem(u.role_name))
            self._table.setItem(
                r, 4, QTableWidgetItem("نشط" if u.is_active else "معطّل")
            )

    def _selected(self):
        row = self._table.currentRow()
        if row < 0:
            return None
        return (
            int(self._table.item(row, 0).text()),
            self._table.item(row, 1).text(),
            self._table.item(row, 4).text() == "نشط",
        )

    def _add_user(self) -> None:
        self._c.navigator.push(UserFormPage(self._c))

    def _toggle_active(self) -> None:
        sel = self._selected()
        if sel is None:
            QMessageBox.information(self, "تنبيه", "اختر مستخدمًا أولًا.")
            return
        user_id, username, is_active = sel
        actor = self._c.auth.current_user
        if actor and actor.id == user_id:
            QMessageBox.warning(self, "غير مسموح", "لا يمكنك تعطيل حسابك الحالي.")
            return
        self._c.users.set_active(
            user_id, not is_active, actor_id=actor.id if actor else None
        )
        self.refresh()

    def _reset_password(self) -> None:
        sel = self._selected()
        if sel is None:
            QMessageBox.information(self, "تنبيه", "اختر مستخدمًا أولًا.")
            return
        user_id, username, _ = sel
        new_pwd, ok = QInputDialog.getText(
            self,
            "تعيين كلمة مرور",
            f"كلمة المرور الجديدة للمستخدم «{username}»:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return
        actor = self._c.auth.current_user
        try:
            self._c.users.reset_password(
                user_id, new_pwd, actor_id=actor.id if actor else None
            )
        except UsersServiceError as exc:
            QMessageBox.warning(self, "تعذّر", str(exc))
            return
        QMessageBox.information(self, "تم", "تم تحديث كلمة المرور.")


# ── تبويب الأدوار والصلاحيات (مصفوفة) ───────────────────────────────────
class _RolesTab(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._can_manage = container.auth.can(Permissions.USERS_MANAGE)
        self._checks: dict[str, QCheckBox] = {}
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(title_label("الأدوار والصلاحيات"))

        top = QHBoxLayout()
        top.addWidget(QLabel("الدور:"))
        self._role_combo = QComboBox()
        self._role_combo.currentIndexChanged.connect(self._load_role_permissions)
        top.addWidget(self._role_combo)
        top.addStretch(1)
        save = QPushButton("حفظ صلاحيات الدور")
        save.setEnabled(self._can_manage)
        save.clicked.connect(self._save)
        top.addWidget(save)
        layout.addLayout(top)

        # مصفوفة الصلاحيات مجمّعة حسب الوحدة داخل منطقة تمرير.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QVBoxLayout(container)
        grid.setSpacing(10)

        groups: "OrderedDict[str, list[str]]" = OrderedDict()
        for code in Permissions.all():
            groups.setdefault(group_label(code), []).append(code)

        for label, codes in groups.items():
            box = QGroupBox(label)
            box_layout = QVBoxLayout(box)
            for code in codes:
                cb = QCheckBox(Permissions.CATALOG[code])
                cb.setEnabled(self._can_manage)
                self._checks[code] = cb
                box_layout.addWidget(cb)
            grid.addWidget(box)
        grid.addStretch(1)

        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

    def refresh(self) -> None:
        roles = self._c.users.list_roles()
        self._role_combo.blockSignals(True)
        self._role_combo.clear()
        for role in roles:
            self._role_combo.addItem(role.name, role.id)
        self._role_combo.blockSignals(False)
        self._load_role_permissions()

    def _load_role_permissions(self) -> None:
        role_id = self._role_combo.currentData()
        if role_id is None:
            return
        granted = self._c.users.role_permissions(role_id)
        for code, cb in self._checks.items():
            cb.setChecked(code in granted)

    def _save(self) -> None:
        role_id = self._role_combo.currentData()
        if role_id is None:
            return
        codes = {code for code, cb in self._checks.items() if cb.isChecked()}
        actor = self._c.auth.current_user
        self._c.users.set_role_permissions(
            role_id, codes, actor_id=actor.id if actor else None
        )
        QMessageBox.information(
            self, "تم", "تم حفظ صلاحيات الدور. تُطبَّق عند تسجيل الدخول التالي للمستخدمين."
        )


# ── نافذة إضافة مستخدم ──────────────────────────────────────────────────
class UserFormPage(Page):
    def __init__(self, container: "Container"):
        super().__init__(container.navigator, "إضافة مستخدم")
        self._c = container

        card = Card()
        form = QFormLayout()
        card.layout().addLayout(form)
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
        cancel.clicked.connect(self.go_back)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        card.layout().addLayout(buttons)
        self.body.addWidget(card)
        self.body.addStretch(1)

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
        self.go_back()
