"""محرّك ألوان خفيف (بدون مكتبات خارجية) لاشتقاق درجات الألوان والتدرّجات.

يُستخدم لبناء توكنز مشتقّة من ألوان القالب الأساسية (hover/dark/light/accent)
ولتطبيق تخصيص ألوان المستخدم (لون أساسي + لون تمييز + درجة فاتح/غامق) فوق
توكنز القالب قبل توليد QSS النهائي. كل الحسابات نقية بايثون.
"""
from __future__ import annotations


def _clamp(v: float) -> int:
    return max(0, min(255, int(round(v))))


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = (value or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        return (0, 0, 0)
    try:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except ValueError:
        return (0, 0, 0)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(_clamp(c) for c in rgb))


def lighten(value: str, amount: float) -> str:
    """تفتيح اللون باتجاه الأبيض بنسبة amount (0..1)."""
    r, g, b = hex_to_rgb(value)
    return rgb_to_hex((r + (255 - r) * amount, g + (255 - g) * amount, b + (255 - b) * amount))


def darken(value: str, amount: float) -> str:
    """تغميق اللون باتجاه الأسود بنسبة amount (0..1)."""
    r, g, b = hex_to_rgb(value)
    return rgb_to_hex((r * (1 - amount), g * (1 - amount), b * (1 - amount)))


def mix(a: str, b: str, t: float) -> str:
    """مزج لونين: t=0 ⇒ a، t=1 ⇒ b."""
    ar, ag, ab = hex_to_rgb(a)
    br, bg, bb = hex_to_rgb(b)
    return rgb_to_hex((ar + (br - ar) * t, ag + (bg - ag) * t, ab + (bb - ab) * t))


def luminance(value: str) -> float:
    r, g, b = hex_to_rgb(value)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def best_on(value: str) -> str:
    """أنسب لون نص (أبيض/داكن) فوق خلفية معطاة لضمان التباين."""
    return "#FFFFFF" if luminance(value) < 0.6 else "#16202E"


def apply_shade(value: str, shade: int) -> str:
    """تطبيق درجة (-100..100): موجب = أفتح، سالب = أغمق."""
    if not shade:
        return value
    amount = min(abs(shade), 100) / 100.0 * 0.45
    return lighten(value, amount) if shade > 0 else darken(value, amount)


def derive_tokens(
    tokens: dict[str, str],
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    """دمج تخصيص المستخدم + اشتقاق التوكنز المطلوبة للتدرّجات والدرجات.

    overrides المدعومة: primary (hex)، accent (hex)، shade (str int -100..100).
    عند ضبط لون أساسي مخصّص يُنشر أثره على الشريط العلوي والجانبي ولون التمييز
    لتعطي إحساسًا واضحًا بتغيّر هوية النظام بالكامل.
    """
    t = dict(tokens)
    overrides = overrides or {}

    custom_primary = (overrides.get("primary") or "").strip()
    custom_accent = (overrides.get("accent") or "").strip()
    try:
        shade = int(overrides.get("shade", "0") or "0")
    except ValueError:
        shade = 0

    if custom_primary:
        primary = apply_shade(custom_primary, shade)
        t["primary"] = primary
        # نشر اللون الأساسي على هوية النظام كاملة.
        t["appbar_bg"] = primary
        t["sidebar_active_bg"] = primary
        t["stat_accent"] = primary
        if not custom_accent:
            t["accent"] = lighten(primary, 0.22)
    elif shade:
        t["primary"] = apply_shade(t.get("primary", "#1565C0"), shade)

    if custom_accent:
        t["accent"] = apply_shade(custom_accent, shade) if shade else custom_accent

    primary = t.get("primary", "#1565C0")
    accent = t.get("accent") or t.get("stat_accent") or lighten(primary, 0.2)
    t["accent"] = accent

    # درجات اللون الأساسي.
    t.setdefault("on_primary", best_on(primary))
    t["primary_hover"] = darken(primary, 0.12)
    t["primary_dark"] = darken(primary, 0.24)
    t["primary_light"] = lighten(primary, 0.20)

    # درجات لون التمييز.
    t["accent_dark"] = darken(accent, 0.18)
    t["accent_soft"] = lighten(accent, 0.30)
    t["on_accent"] = best_on(accent)

    # أطراف التدرّجات للشريط العلوي/الجانبي/الخلفية.
    appbar = t.get("appbar_bg", primary)
    t["appbar_bg2"] = t.get("appbar_bg2") or mix(appbar, accent, 0.45)
    sidebar = t.get("sidebar_bg", darken(primary, 0.35))
    t["sidebar_bg2"] = t.get("sidebar_bg2") or darken(sidebar, 0.22)
    bg = t.get("bg", "#F4F6F9")
    t["bg2"] = t.get("bg2") or mix(bg, accent, 0.05)

    t["stat_accent"] = t.get("stat_accent") or accent

    # توكنز الستايل المينيمال + الزجاجي (Glass).
    is_dark = luminance(bg) < 0.40
    surface = t.get("surface", "#FFFFFF")
    sr, sg, sb = hex_to_rgb(surface)
    # خلفية الكروت شبه شفافة لإحساس الزجاج فوق الخلفية المتدرّجة.
    glass_alpha = 0.55 if is_dark else 0.78
    t["glass_bg"] = f"rgba({sr}, {sg}, {sb}, {glass_alpha})"
    t["glass_border"] = (
        "rgba(255, 255, 255, 0.10)" if is_dark else "rgba(255, 255, 255, 0.75)"
    )
    # خط فاصل رفيع وهادئ للستايل المينيمال.
    t["hairline"] = mix(t.get("border", "#DDDDDD"), bg, 0.35)
    # تظليل خفيف للكروت.
    t["shadow"] = "rgba(0, 0, 0, 0.45)" if is_dark else "rgba(15, 23, 42, 0.12)"
    # حبّة التحديد في القائمة الجانبية (شفافة ناعمة).
    ar, ag, ab = hex_to_rgb(t.get("sidebar_active_bg", primary))
    t["nav_active"] = f"rgba({ar}, {ag}, {ab}, 0.95)"
    t["is_dark"] = "1" if is_dark else "0"
    return t
