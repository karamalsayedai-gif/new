"""تحميل هوية التطبيق (الأيقونة + خط Cairo) بمسارات آمنة للتغليف.

- الأيقونة من app/assets/icons/app.ico عبر resource_path (يعمل بعد PyInstaller).
- خطوط Cairo (إن وُجدت ملفاتها في app/assets/fonts) تُحمَّل في وقت التشغيل عبر
  QFontDatabase؛ القوالب تضع "Cairo" أولًا في عائلة الخط فتستخدمه عند توفّره
  وتسقط تلقائيًا إلى Segoe UI/Tahoma عند غيابه.
"""
from __future__ import annotations

from PyQt6.QtGui import QFont, QFontDatabase, QIcon
from PyQt6.QtWidgets import QApplication

from app.config import resource_path


def application_icon() -> QIcon:
    path = resource_path("app", "assets", "icons", "app.ico")
    return QIcon(str(path)) if path.exists() else QIcon()


def install_fonts(app: QApplication) -> str:
    """يحمّل خطوط Cairo إن وُجدت ويضبط الخط الافتراضي. يعيد اسم العائلة المستخدمة."""
    fonts_dir = resource_path("app", "assets", "fonts")
    loaded_family: str | None = None
    if fonts_dir.exists():
        for ttf in sorted(fonts_dir.glob("*.ttf")):
            font_id = QFontDatabase.addApplicationFont(str(ttf))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families and loaded_family is None:
                    loaded_family = families[0]

    family = loaded_family or "Segoe UI"
    font = QFont(family)
    font.setPointSize(10)
    app.setFont(font)
    return family
