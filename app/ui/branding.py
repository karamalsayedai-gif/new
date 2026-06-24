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
    """يحمّل الخطوط المضمّنة ويضبط الخط الافتراضي (Tajawal أولًا).

    يعيد اسم العائلة المستخدمة. القوالب تضع "Tajawal" أولًا في عائلة الخط.
    """
    fonts_dir = resource_path("app", "assets", "fonts")
    families: list[str] = []
    if fonts_dir.exists():
        for ttf in sorted(fonts_dir.glob("*.ttf")):
            font_id = QFontDatabase.addApplicationFont(str(ttf))
            if font_id != -1:
                families.extend(QFontDatabase.applicationFontFamilies(font_id))

    # نفضّل Tajawal، ثم Cairo، ثم أي عائلة مُحمَّلة، وإلا خط النظام.
    preferred = next(
        (f for f in families if "Tajawal" in f),
        next((f for f in families if "Cairo" in f), families[0] if families else "Segoe UI"),
    )
    font = QFont(preferred)
    font.setPointSize(10)
    app.setFont(font)
    return preferred
