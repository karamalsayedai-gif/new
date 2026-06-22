"""النافذة الرئيسية (App Shell): شريط علوي + شريط جانبي + منطقة محتوى متبدّلة.

تُبنى عناصر التنقل من سجل التنقل وتُفلتر حسب صلاحيات المستخدم. موضع الشريط
الجانبي وعرضه يُقرآن من تلميحات القالب الحالي، وتُعاد البناية عند تبديل القالب.
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
from app.ui.shell.navigation import NavItem, build_nav_items

if TYPE_CHECKING:
    from app.core.container import Container


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self.setWindowTitle(AppConfig.APP_NAME_AR)
        self.resize(1180, 740)

        self._stack = QStackedWidget()
        self._key_to_index: dict[str, int] = {}
        self._nav_buttons: list[QPushButton] = []
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)

        self._items = [
            item
            for item in build_nav_items()
            if item.permission is None or self._c.auth.can(item.permission)
        ]

        self._build_layout()

        # إعادة ترتيب الشريط الجانبي عند تبديل القالب (قد يتغيّر موضعه).
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

        # بناء الصفحات في الـ Stack.
        for item in self._items:
            page = item.factory(self._c)
            index = self._stack.addWidget(page)
            self._key_to_index[item.key] = index

        if self._nav_buttons:
            self._nav_buttons[0].setChecked(True)
            self._stack.setCurrentIndex(0)

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
            who = QLabel(f"{user.full_name} ({user.role_name})")
            layout.addWidget(who)

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
            layout.addWidget(self._stack, stretch=1)
        else:
            layout.addWidget(self._stack, stretch=1)
            layout.addWidget(sidebar)
        return body

    def _build_sidebar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Sidebar")
        width = int(self._c.theme.layout_hint("sidebar_width", 240)) if self._c.theme else 240
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
            button.clicked.connect(
                lambda _checked, key=item.key: self._navigate(key)
            )
            self._nav_group.addButton(button, position)
            self._nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch(1)
        return frame

    # ── التنقل ──────────────────────────────────────────────────────────
    def _navigate(self, key: str) -> None:
        index = self._key_to_index.get(key)
        if index is None:
            return
        self._stack.setCurrentIndex(index)
        page = self._stack.widget(index)
        # تحديث الصفحة عند الدخول إن دعمت ذلك.
        if hasattr(page, "refresh"):
            page.refresh()

    def _on_theme_changed(self, _theme_id: str) -> None:
        # إعادة بناء التخطيط لاحترام موضع/عرض الشريط الجانبي للقالب الجديد.
        current_index = self._stack.currentIndex()
        self._stack = QStackedWidget()
        self._key_to_index.clear()
        self._nav_buttons.clear()
        for button in self._nav_group.buttons():
            self._nav_group.removeButton(button)
        self._build_layout()
        if 0 <= current_index < self._stack.count():
            self._stack.setCurrentIndex(current_index)
            if current_index < len(self._nav_buttons):
                self._nav_buttons[current_index].setChecked(True)
