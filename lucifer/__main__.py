"""Chạy: python -m lucifer [--text] [--brain rules|claude] [--stt google|whisper] ..."""

from __future__ import annotations

import argparse
import logging
import sys

from .assistant import Assistant
from .brain import build_brain
from .config import Settings
from .tools import build_registry


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="lucifer", description="Trợ lý giọng nói điều khiển máy tính")
    p.add_argument("--text", action="store_true", help="gõ phím thay vì nói (không cần micro)")
    p.add_argument("--brain", choices=["auto", "claude", "rules"], help="bộ não sử dụng")
    p.add_argument("--stt", choices=["google", "whisper"], help="bộ nhận dạng giọng nói")
    p.add_argument("--tts", choices=["edge", "pyttsx3", "none"], help="giọng đọc")
    p.add_argument("--no-wake", action="store_true", help="không cần gọi tên, nghe mọi câu là lệnh")
    p.add_argument("--list-tools", action="store_true", help="liệt kê các lệnh (tool) rồi thoát")
    p.add_argument("--debug", action="store_true", help="in log chi tiết")
    return p.parse_args(argv)


def setup_logging(settings: Settings, debug: bool) -> None:
    handlers: list[logging.Handler] = [logging.FileHandler(settings.log_file, encoding="utf-8")]
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if debug else logging.WARNING)
    handlers.append(console)
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass

    args = parse_args(argv)
    settings = Settings()
    if args.brain:
        settings.brain = args.brain
    if args.stt:
        settings.stt_engine = args.stt
    if args.tts:
        settings.tts_engine = args.tts
    setup_logging(settings, args.debug)

    registry = build_registry()
    if args.list_tools:
        for tool in registry.tools.values():
            print(f"- {tool.name}: {tool.description}")
        return 0

    from .voice import KeyboardListener, MicListener, build_speaker

    if args.text:
        listener = KeyboardListener()
    else:
        try:
            listener = MicListener(settings)
        except ImportError as exc:
            print(f"Thiếu thư viện thu âm ({exc}). Cài: pip install SpeechRecognition pyaudio\n"
                  "Hoặc chạy chế độ gõ phím: python -m lucifer --text", file=sys.stderr)
            return 1
        except OSError as exc:
            print(f"Không mở được micro: {exc}\nKiểm tra micro trong Windows Sound Settings, "
                  "hoặc chạy: python -m lucifer --text", file=sys.stderr)
            return 1

    speaker = build_speaker(settings)
    brain = build_brain(settings, registry)
    mode = "Claude AI" if settings.resolved_brain() == "claude" else "offline (bộ luật)"
    print(f"[Bộ não: {mode}]")

    assistant = Assistant(
        settings, listener, speaker, brain,
        require_wake=not (args.text or args.no_wake),
        echo_heard=not args.text,
    )
    assistant.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
