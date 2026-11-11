"""Phát hiện từ đánh thức ("Lucifer", "ê PC"...) trong câu đã nhận dạng.

Cách làm: nghe liên tục, chuyển giọng nói thành chữ, rồi tìm từ đánh thức trong
câu. Không cần train model riêng, và người dùng có thể nói liền một hơi:
"Lucifer mở Chrome tìm kiếm thời tiết" -> lệnh = "mở Chrome tìm kiếm thời tiết".

Vì STT có thể nghe "Lucifer" thành "lu xi phơ", "lucifer", "Lu-si-fơ"... nên mỗi
từ đánh thức có nhiều biến thể (viết không dấu, cách nhau bằng khoảng trắng).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .textutil import clean_fragment, normalize, prepare, squash

DEFAULT_WAKE_WORDS: list[str] = [
    # Lucifer và các cách STT hay nghe nhầm
    "lucifer",
    "lucipher",
    "lu cifer",
    "lu xi phe",
    "lu xi pho",
    "lu si phe",
    "lu si pho",
    "lu xi fe",
    "lu si fe",
    "lu xi fer",
    "lu si fer",
    "luxiphe",
    "lusiphe",
    # "Ê PC"
    "e pc",
    "e p c",
    "e pi xi",
    "e bi xi",
    "e pi si",
    "e bi si",
    "hey pc",
    "oi pc",
]


@dataclass(frozen=True)
class WakeResult:
    detected: bool
    command: str = ""


class WakeWordDetector:
    def __init__(self, wake_words: list[str] | None = None):
        words = wake_words or DEFAULT_WAKE_WORDS
        variants = sorted({squash(w) for w in words if squash(w)}, key=len, reverse=True)
        if not variants:
            raise ValueError("Cần ít nhất một từ đánh thức")
        alternatives = "|".join(r"\s+".join(map(re.escape, v.split())) for v in variants)
        self._pattern = re.compile(rf"(?<![a-z0-9])(?:{alternatives})(?![a-z0-9])")

    def detect(self, text: str) -> WakeResult:
        """Tìm từ đánh thức; trả về phần lệnh nói SAU từ đánh thức (giữ dấu)."""
        original = prepare(text)
        match = self._pattern.search(normalize(original))
        if not match:
            return WakeResult(False)
        command = clean_fragment(original[match.end():])
        if not command:
            # "Mở Chrome đi Lucifer" -> lệnh nằm trước từ đánh thức
            before = clean_fragment(original[: match.start()])
            # bỏ các từ gọi như "ê", "này", "hey" đứng trước
            before = re.sub(r"(?i)\b(ê|này|hey|ơi)$", "", before).strip()
            command = clean_fragment(before)
        return WakeResult(True, command)
