"""تجزئة كلمات المرور باستخدام PBKDF2-HMAC-SHA256 من مكتبة hashlib القياسية.

اختير هذا الأسلوب لأنه لا يتطلب أي حزمة خارجية، وآمن وقابل للترقية لاحقًا لأن
الصيغة المخزّنة تحمل معرّف الخوارزمية وعدد التكرارات والمِلح.

الصيغة المخزّنة: ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``
"""
from __future__ import annotations

import hashlib
import hmac
import os

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(password: str, iterations: int = _ITERATIONS) -> str:
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{_ALGO}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iter_str, salt_hex, hash_hex = stored.split("$")
    except ValueError:
        return False
    if algo != _ALGO:
        return False
    try:
        iterations = int(iter_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    # مقارنة بزمن ثابت لتفادي هجمات التوقيت.
    return hmac.compare_digest(expected, actual)
