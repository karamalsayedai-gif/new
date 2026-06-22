"""إقلاع التطبيق والتحكم في التنقل بين الشاشات الجذرية.

المسؤوليات:
- إنشاء الحاوية وتهيئة قاعدة البيانات والإعدادات.
- إنشاء ``QApplication`` وضبط اتجاه RTL والخط.
- إنشاء ``ThemeManager`` وتطبيق القالب المحفوظ عالميًا.
- إدارة الانتقال بين: الإعداد الأولي ← تسجيل الدخول ← النافذة الرئيسية.
- نسخة احتياطية تلقائية عند الإقلاع والإغلاق (حسب الإعدادات).
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget

from app.config import AppConfig
from app.core.container import Container
from app.theme.theme_manager import ThemeManager
from app.ui.branding import application_icon, install_fonts
from app.ui.login.login_view import LoginView
from app.ui.setup.setup_view import SetupView
from app.ui.shell.main_window import MainWindow


class Application:
    def __init__(self, argv: list[str]):
        self._argv = argv
        self._window: QWidget | None = None

    def run(self) -> int:
        self._container = Container()
        self._container.initialize()

        self._app = QApplication(self._argv)
        self._app.setApplicationName(AppConfig.APP_NAME)
        self._app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._app.setWindowIcon(application_icon())
        install_fonts(self._app)

        self._theme = ThemeManager(self._app, self._container.settings)
        self._container.theme = self._theme
        self._theme.apply_current()

        self._safe_auto_backup()
        self._app.aboutToQuit.connect(self._on_quit)

        self._show_initial()
        return self._app.exec()

    # ── التنقل الجذري ───────────────────────────────────────────────────
    def _show_initial(self) -> None:
        if not self._container.settings.is_setup_completed:
            self._show_setup()
        else:
            self._show_login()

    def _show_setup(self) -> None:
        view = SetupView(self._container)
        view.completed.connect(lambda _user: self._open_main())
        self._swap(view)

    def _show_login(self) -> None:
        view = LoginView(self._container)
        view.logged_in.connect(lambda _user: self._open_main())
        self._swap(view)

    def _open_main(self) -> None:
        window = MainWindow(self._container)
        window.logout_requested.connect(self._on_logout)
        self._swap(window)

    def _on_logout(self) -> None:
        self._container.auth.logout()
        self._show_login()

    def _swap(self, widget: QWidget) -> None:
        widget.show()
        old = self._window
        self._window = widget
        if old is not None:
            old.close()
            old.deleteLater()

    # ── النسخ الاحتياطي والإغلاق ────────────────────────────────────────
    def _safe_auto_backup(self) -> None:
        try:
            self._container.backup.maybe_run_auto_backup()
        except Exception:  # noqa: BLE001 — النسخ التلقائي لا يجب أن يمنع الإقلاع.
            pass

    def _on_quit(self) -> None:
        self._safe_auto_backup()
        try:
            self._container.backup.run_backup_on_close()
        except Exception:  # noqa: BLE001 — لا يجب أن يمنع الإغلاق.
            pass
        self._container.db.close()
