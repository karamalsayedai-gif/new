"""تحميل قالب منظَّم وبناء QSS النهائي عبر استبدال الرموز (tokens).

كل قالب مجلد يحتوي ملفات منفصلة:
    manifest.json    → الهوية (id, name, mode) وتلميحات التخطيط (layout)
    colors.json      → رموز الألوان
    metrics.json     → رموز المقاسات (نصف القطر، التباعد، الكثافة)
    typography.json  → رموز الخطوط والأحجام
    main.qss         → قالب QSS يستخدم ``$token``

تُدمج كل رموز ملفات JSON ثم تُستبدل في main.qss عبر ``string.Template`` (صيغة
``$token`` لا تتعارض مع أقواس QSS).
"""
from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import Any

from app.theme import palette

MANIFEST = "manifest.json"
COLORS = "colors.json"
METRICS = "metrics.json"
TYPOGRAPHY = "typography.json"
MAIN_QSS = "main.qss"


class ThemeData:
    def __init__(self, manifest: dict[str, Any], tokens: dict[str, str], qss: str):
        self.id: str = manifest.get("id", "")
        self.name: str = manifest.get("name", self.id)
        self.mode: str = manifest.get("mode", "light")
        self.layout: dict[str, Any] = manifest.get("layout", {})
        self.tokens = tokens
        self.qss = qss


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def collect_tokens(theme_dir: Path) -> dict[str, str]:
    """دمج رموز الألوان والمقاسات والخطوط في قاموس واحد مسطّح."""
    tokens: dict[str, str] = {}
    for filename in (COLORS, METRICS, TYPOGRAPHY):
        data = _read_json(theme_dir / filename)
        # نقبل إما قاموسًا مسطّحًا أو مفتاح "tokens".
        flat = data.get("tokens", data)
        for key, value in flat.items():
            tokens[key] = str(value)
    return tokens


def load_theme(
    theme_dir: Path,
    overrides: dict[str, str] | None = None,
) -> ThemeData:
    manifest = _read_json(theme_dir / MANIFEST)
    tokens = collect_tokens(theme_dir)
    # دمج تخصيص ألوان المستخدم واشتقاق الدرجات/التدرّجات.
    tokens = palette.derive_tokens(tokens, overrides)
    qss_raw = (theme_dir / MAIN_QSS).read_text(encoding="utf-8") if (
        theme_dir / MAIN_QSS
    ).exists() else ""
    qss = Template(qss_raw).safe_substitute(tokens)
    return ThemeData(manifest, tokens, qss)


def read_manifest(theme_dir: Path) -> dict[str, Any]:
    return _read_json(theme_dir / MANIFEST)
