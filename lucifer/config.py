"""Cấu hình, đọc từ biến môi trường hoặc file `.env` ở thư mục chạy chương trình."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .wakeword import DEFAULT_WAKE_WORDS

try:  # python-dotenv là tuỳ chọn
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class Settings:
    assistant_name: str = field(default_factory=lambda: _env("LUCIFER_NAME", "Lucifer"))
    wake_words: list[str] = field(
        default_factory=lambda: _env_list("LUCIFER_WAKE_WORDS", DEFAULT_WAKE_WORDS)
    )
    # Sau khi được gọi, giữ trạng thái "thức" bao lâu (giây) để nói tiếp không cần gọi tên
    follow_up_seconds: float = field(default_factory=lambda: _env_float("LUCIFER_FOLLOW_UP", 15))

    # Bộ não: "auto" (Claude nếu có API key, không thì luật offline), "claude", "rules"
    brain: str = field(default_factory=lambda: _env("LUCIFER_BRAIN", "auto"))
    model: str = field(default_factory=lambda: _env("LUCIFER_MODEL", "claude-opus-5-5"))
    effort: str = field(default_factory=lambda: _env("LUCIFER_EFFORT", "low"))
    # Hội thoại tự reset sau bấy nhiêu giây im lặng
    session_idle_seconds: float = field(
        default_factory=lambda: _env_float("LUCIFER_SESSION_IDLE", 600)
    )

    # Nhận dạng giọng nói: "google" (online, miễn phí, tiếng Việt tốt) hoặc "whisper" (offline)
    stt_engine: str = field(default_factory=lambda: _env("LUCIFER_STT", "google"))
    language: str = field(default_factory=lambda: _env("LUCIFER_LANGUAGE", "vi-VN"))
    whisper_model: str = field(default_factory=lambda: _env("LUCIFER_WHISPER_MODEL", "small"))
    phrase_time_limit: float = field(
        default_factory=lambda: _env_float("LUCIFER_PHRASE_LIMIT", 8)
    )

    # Giọng đọc: "edge" (online, giọng Việt tự nhiên), "pyttsx3" (offline), "none"
    tts_engine: str = field(default_factory=lambda: _env("LUCIFER_TTS", "edge"))
    tts_voice: str = field(default_factory=lambda: _env("LUCIFER_VOICE", "vi-VN-NamMinhNeural"))

    log_file: str = field(default_factory=lambda: _env("LUCIFER_LOG", "lucifer.log"))

    def resolved_brain(self) -> str:
        if self.brain in ("claude", "rules"):
            return self.brain
        has_key = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))
        return "claude" if has_key else "rules"
