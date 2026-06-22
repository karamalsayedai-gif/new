"""النافذة الرئيسية (App Shell): شريط علوي + شريط جانبي + منطقة محتوى كاملة.

تعتمد التنقّل بالصفحات الكاملة عبر ``Navigator``: نقر عنصر في الشريط الجانبي
يعيد تعيين المحتوى لجذر تلك الوحدة، وأي تفاصيل/كشف حساب/سجل حركة يُدفع كصفحة
كاملة فوقه (لا نوافذ منبثقة للشاشات الأساسية).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.ui.shell.navigation import build_nav_items
from app.ui.shell.navigator import Navigator

if TYPE_CHECKING:
    from app.core.container import Container


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self.setWindowTitle(AppConfig.APP_NAME_AR)
        self.resize(1180, 740)

        self._content = QStackedWidget()
        self._navigator = Navigator(self._content)
        self._c.navigator = self._navigator

        self._nav_buttons: dict[str, QPushButton] = {}
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._current_key: str | None = None

        self._items = [
            item
            for item in build_nav_items()
            if item.permission is None or self._c.auth.can(item.permission)
        ]

        self._build_layout()
        if self._items:
            self._open_module(self._items[0].key)

        if self._c.theme is not None:
            self._c.theme.theme_changed.connect(self._on_theme_changed)

    # ── البناء ──────────────────────────────────────────────────────────
    def _build_layout(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_appbar())
        root.addWidget(self._build_body(), stretch=1)
        self.setCentralWidget(central)

    def _build_appbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("AppBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 10, 18, 10)

        title = QLabel(self._c.settings.showroom_name)
        title.setObjectName("AppTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        user = self._c.auth.current_user
        if user is not None:
            layout.addWidget(QLabel(f"{user.full_name} ({user.role_name})"))

        logout = QPushButton("خروج")
        logout.setObjectName("Ghost")
        logout.clicked.connect(self.logout_requested.emit)
        layout.addWidget(logout)
        return bar

    def _build_body(self) -> QWidget:
        body = QWidget()
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = self._build_sidebar()
        sidebar_on_right = (
            self._c.theme.layout_hint("sidebar", "right") == "right"
            if self._c.theme
            else True
        )
        # في واجهة RTL: أول عنصر في التخطيط الأفقي يظهر على اليمين.
        if sidebar_on_right:
            layout.addWidget(sidebar)
            layout.addWidget(self._content, stretch=1)
        else:
            layout.addWidget(self._content, stretch=1)
            layout.addWidget(sidebar)
        return body

    def _build_sidebar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Sidebar")
        width = (
            int(self._c.theme.layout_hint("sidebar_width", 240))
            if self._c.theme
            else 240
        )
        frame.setFixedWidth(width)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        brand = QLabel(AppConfig.APP_NAME_AR)
        brand.setObjectName("SidebarBrand")
        brand.setWordWrap(True)
        layout.addWidget(brand)

        self._nav_buttons.clear()
        for position, item in enumerate(self._items):
            button = QPushButton(item.label)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _c, key=item.key: self._open_module(key))
            self._nav_group.addButton(button, position)
            self._nav_buttons[item.key] = button
            layout.addWidget(button)

        layout.addStretch(1)
        return frame

    # ── التنقل بين الوحدات ──────────────────────────────────────────────
    def _open_module(self, key: str) -> None:
        item = next((it for it in self._items if it.key == key), None)
        if item is None:
            return
        self._current_key = key
        button = self._nav_buttons.get(key)
        if button is not None:
            button.setChecked(True)
        # جذر جديد للوحدة (يُعاد بناؤه ببيانات حديثة) ويمسح أي صفحات تفاصيل.
        self._navigator.reset_to(item.factory(self._c))

    def _on_theme_changed(self, _theme_id: str) -> None:
        # إعادة بناء الهيكل لاحترام موضع/عرض الشريط الجانبي للقالب الجديد.
        self._content = QStackedWidget()
        self._navigator = Navigator(self._content)
        self._c.navigator = self._navigator
        for button in list(self._nav_group.buttons()):
            self._nav_group.removeButton(button)
        self._build_layout()
        self._open_module(self._current_key or (self._items[0].key if self._items else ""))
