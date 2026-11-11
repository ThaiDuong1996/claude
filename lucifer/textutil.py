"""Tiện ích xử lý văn bản tiếng Việt.

`normalize()` bỏ dấu, viết thường và thay ký tự không phải chữ/số bằng khoảng
trắng, nhưng GIỮ NGUYÊN ĐỘ DÀI chuỗi (mỗi ký tự gốc -> đúng 1 ký tự). Nhờ vậy
có thể so khớp regex trên chuỗi đã chuẩn hoá rồi cắt lại đúng đoạn tương ứng
trong chuỗi gốc (còn dấu) để dùng làm từ khoá tìm kiếm, tên ứng dụng...
"""

from __future__ import annotations

import re
import unicodedata


def _fold_char(ch: str) -> str:
    if ch in "đĐ":
        return "d"
    lowered = ch.lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    base = "".join(c for c in decomposed if not unicodedata.combining(c))
    if not base:
        return " "
    base = base[0]
    return base if base.isalnum() else " "


def prepare(text: str) -> str:
    """Chuẩn hoá Unicode về dạng NFC (dấu dựng sẵn) để ánh xạ 1-1 hoạt động."""
    return unicodedata.normalize("NFC", text or "")


def normalize(text: str) -> str:
    """Bỏ dấu + viết thường, giữ nguyên độ dài so với `prepare(text)`."""
    return "".join(_fold_char(c) for c in prepare(text))


def squash(text: str) -> str:
    """Bỏ dấu, viết thường và gộp khoảng trắng (không giữ độ dài)."""
    return re.sub(r"\s+", " ", normalize(text)).strip()


def clean_fragment(text: str) -> str:
    """Cắt khoảng trắng và dấu câu thừa ở hai đầu một đoạn trích."""
    return text.strip(" \t\r\n,.;:!?-–—\"'“”")
