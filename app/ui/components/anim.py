"""حركات ناعمة (QPropertyAnimation) لإضافة إحساس حيّ للواجهة.

PyQt6 لا يدعم انتقالات CSS، فالحركات تُنفَّذ برمجيًا. نستخدم تأثير شفافية مؤقتًا
أثناء ظهور الصفحة ثم نزيله حتى لا يتعارض مع تأثيرات الظل في البطاقات.

مهم: الحركة مؤمّنة بحيث لا تترك الصفحة شفافة/مخفية أبدًا — هناك مؤقّت أمان يضمن
العودة لوضوح كامل حتى لو انقطعت الحركة لأي سبب.
"""
from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QTimer
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget

# نحتفظ بمراجع للحركات الجارية حتى لا يجمعها مُجمِّع المهملات قبل انتهائها.
_running: dict[int, QPropertyAnimation] = {}


def fade_in(widget: QWidget, duration: int = 180) -> None:
    """ظهور تدريجي للعنصر (شفافية 0 ← 1) مع ضمان الوضوح الكامل بعد الانتهاء."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    effect.setOpacity(0.0)

    key = id(widget)
    cleaned = {"done": False}

    def _restore() -> None:
        if cleaned["done"]:
            return
        cleaned["done"] = True
        # إزالة تأثير الشفافية حتى تعمل ظلال البطاقات بشكل طبيعي بعد الظهور.
        try:
            widget.setGraphicsEffect(None)
        except RuntimeError:
            pass
        _running.pop(key, None)

    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.finished.connect(_restore)
    _running[key] = anim
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    # شبكة أمان: مهما حدث، الصفحة تعود واضحة تمامًا بعد فترة قصيرة.
    QTimer.singleShot(duration + 120, _restore)
