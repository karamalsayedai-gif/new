"""النافذة الرئيسية (App Shell): شريط علوي + شريط جانبي + منطقة محتوى كاملة.

تعتمد التنقّل بالصفحات الكاملة عبر ``Navigator``: نقر عنصر في الشريط الجانبي
يعيد تعيين المحتوى لجذر تلك الوحدة، وأي تفاصيل/كشف حساب/سجل حركة يُدفع كصفحة
كاملة فوقه (لا نوافذ منبثقة للشاشات الأساسية).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
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
        self._install_shortcuts()
        if self._items:
            self._open_module(self._items[0].key)

        if self._c.theme is not None:
            self._c.theme.theme_changed.connect(self._on_theme_changed)

    # ── اختصارات لوحة المفاتيح ───────────────────────────────────────────
    def _install_shortcuts(self) -> None:
        def add(seq: str, slot) -> None:
            QShortcut(QKeySequence(seq), self, activated=slot)

        add("Esc", lambda: self._navigator.pop())
        add("Alt+Left", lambda: self._navigator.pop())
        add("F5", self._refresh_current)
        add("Ctrl+F", self._focus_search)
        add("Ctrl+N", self._trigger_new)
        # Alt+1..9 لفتح الوحدات بالترتيب.
        for i in range(1, 10):
            add(f"Alt+{i}", lambda idx=i - 1: self._open_index(idx))

    def _open_index(self, idx: int) -> None:
        if 0 <= idx < len(self._items):
            self._open_module(self._items[idx].key)

    def _refresh_current(self) -> None:
        page = self._navigator.current()
        if page is not None and hasattr(page, "refresh"):
            page.refresh()

    def _focus_search(self) -> None:
        page = self._navigator.current()
        search = getattr(page, "_search", None)
        if search is not None:
            search.setFocus()
            search.selectAll()

    def _trigger_new(self) -> None:
        page = self._navigator.current()
        for name in ("_new", "_add"):
            fn = getattr(page, name, None)
            if callable(fn):
                fn()
                return

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
        layout.setContentsMargins(20, 9, 20, 9)
        layout.setSpacing(12)

        title = QLabel(self._c.settings.showroom_name)
        title.setObjectName("AppTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        # خانة بحث عامة تُمرَّر للشاشة الحالية.
        self._top_search = QLineEdit()
        self._top_search.setObjectName("TopSearch")
        self._top_search.setPlaceholderText("🔍   ابحث…")
        self._top_search.setFixedWidth(280)
        self._top_search.textChanged.connect(self._on_top_search)
        layout.addWidget(self._top_search)

        bell = QPushButton("🔔")
        bell.setObjectName("IconButton")
        bell.setFixedSize(38, 38)
        bell.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(bell)

        user = self._c.auth.current_user
        if user is not None:
            initial = (user.full_name or "?").strip()[:1] or "؟"
            avatar = QLabel(initial)
            avatar.setObjectName("Avatar")
            avatar.setFixedSize(38, 38)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(avatar)
            who = QLabel(f"{user.full_name}\n{user.role_name}")
            who.setObjectName("UserName")
            layout.addWidget(who)
        return bar

    def _on_top_search(self, text: str) -> None:
        page = self._navigator.current()
        search = getattr(page, "_search", None)
        if search is not None and search is not self._top_search:
            search.setText(text)

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

        outer = QVBoxLayout(frame)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(2)

        brand = QLabel(f"🏍️   {AppConfig.APP_NAME_AR}")
        brand.setObjectName("SidebarBrand")
        brand.setWordWrap(True)
        outer.addWidget(brand)

        # منطقة عناصر التنقّل قابلة للتمرير حتى لا تُقصّ على الشاشات القصيرة.
        scroll = QScrollArea()
        scroll.setObjectName("SidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_holder = QWidget()
        layout = QVBoxLayout(nav_holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._nav_buttons.clear()
        for position, item in enumerate(self._items):
            text = f"{item.icon}   {item.label}" if item.icon else item.label
            button = QPushButton(text)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _c, key=item.key: self._open_module(key))
            self._nav_group.addButton(button, position)
            self._nav_buttons[item.key] = button
            layout.addWidget(button)

        layout.addStretch(1)
        scroll.setWidget(nav_holder)
        outer.addWidget(scroll, stretch=1)

        # زر تسجيل الخروج أسفل القائمة (على نمط لوحات التحكم العصرية).
        logout = QPushButton("⏻   تسجيل الخروج")
        logout.setObjectName("SidebarLogout")
        logout.setCursor(Qt.CursorShape.PointingHandCursor)
        logout.clicked.connect(self.logout_requested.emit)
        outer.addWidget(logout)
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
        # تفريغ خانة البحث العامة عند تبديل الوحدة (دون تصفية الشاشة الجديدة).
        if hasattr(self, "_top_search"):
            self._top_search.blockSignals(True)
            self._top_search.clear()
            self._top_search.blockSignals(False)
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
