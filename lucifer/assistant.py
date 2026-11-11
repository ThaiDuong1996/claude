"""Vòng lặp chính: nghe -> phát hiện từ đánh thức -> hiểu lệnh -> thực thi -> trả lời."""

from __future__ import annotations

import logging
import random
import re
import time

from .brain import Brain
from .config import Settings
from .textutil import prepare, squash
from .voice import Listener, Speaker
from .wakeword import WakeWordDetector

log = logging.getLogger(__name__)

ACKS = ["Vâng, tôi đây.", "Sếp cần gì ạ?", "Tôi nghe đây, thưa sếp."]

# So khớp trên chữ CÓ DẤU vì "đúng" và "dừng" bỏ dấu đều thành "dung"
NO_PATTERN = re.compile(r"\b(không|thôi|huỷ|hủy|dừng|đừng|chưa|no|cancel)\b")
YES_PATTERN = re.compile(r"\b(có|ok|oke|okay|đồng ý|chắc|yes|làm đi|đúng|được|ừ|ừm|uh|um)\b")
# Dự phòng khi câu trả lời không dấu (chỉ các từ không gây nhầm lẫn)
NO_PLAIN = re.compile(r"\b(khong|thoi|huy|no)\b")
YES_PLAIN = re.compile(r"\b(co|ok|oke|okay|dong y|chac chan|yes)\b")
EXIT_PATTERN = re.compile(r"\b(thoat chuong trinh|tat tro ly|tat (lucifer|lu xi phe)|exit|quit)\b")
SLEEP_PATTERN = re.compile(r"^(tam biet|nghi di|di ngu di|ngu di|bye|goodbye)$")
RESET_PATTERN = re.compile(r"\b(quen (het )?di|cuoc tro chuyen moi|bat dau lai)\b")


def is_yes(answer: str) -> bool:
    accented = prepare(answer).lower()
    plain = squash(answer)
    if NO_PATTERN.search(accented) or NO_PLAIN.search(plain):
        return False
    return bool(YES_PATTERN.search(accented) or YES_PLAIN.search(plain))


def beep() -> None:
    try:
        import winsound

        winsound.Beep(880, 120)
    except (ImportError, RuntimeError):
        pass


class Assistant:
    def __init__(
        self,
        settings: Settings,
        listener: Listener,
        speaker: Speaker,
        brain: Brain,
        require_wake: bool = True,
        echo_heard: bool = True,
    ):
        self.settings = settings
        self.listener = listener
        self.speaker = speaker
        self.brain = brain
        self.wake = WakeWordDetector(settings.wake_words)
        self.require_wake = require_wake
        self.echo_heard = echo_heard
        self.awake_until = 0.0

    # ----- nói / xác nhận -----
    def say(self, text: str) -> None:
        print(f"{self.settings.assistant_name}: {text}", flush=True)
        self.speaker.say(text)

    def confirm(self, question: str) -> bool:
        self.say(question + " Nói có hoặc không.")
        for _ in range(2):
            answer = self.listener.listen(timeout=8)
            if answer:
                if self.echo_heard:
                    print(f"Bạn: {answer}", flush=True)
                ok = is_yes(answer)
                log.info("Xác nhận '%s' -> %s", answer, ok)
                return ok
        self.say("Không nghe thấy trả lời, tôi huỷ thao tác.")
        return False

    @property
    def awake(self) -> bool:
        return not self.require_wake or time.monotonic() < self.awake_until

    def _stay_awake(self) -> None:
        self.awake_until = time.monotonic() + self.settings.follow_up_seconds

    # ----- xử lý một câu -----
    def process(self, text: str) -> bool:
        """Xử lý một câu nghe được. Trả về False nếu cần thoát chương trình."""
        result = self.wake.detect(text)
        if result.detected:
            command = result.command
        elif self.awake:
            command = text.strip()
        else:
            log.debug("Bỏ qua (chưa gọi tên): %s", text)
            return True

        if self.echo_heard:
            print(f"Bạn: {text}", flush=True)

        if not command:
            beep()
            self.say(random.choice(ACKS))
            self._stay_awake()
            return True

        key = squash(command)
        if EXIT_PATTERN.search(key):
            self.say("Tạm biệt sếp. Lucifer xin phép nghỉ.")
            return False
        if SLEEP_PATTERN.match(key):
            self.say("Vâng, khi nào cần sếp cứ gọi tôi.")
            self.awake_until = 0.0
            return True
        if RESET_PATTERN.search(key):
            self.brain.reset()
            self.say("Đã xoá cuộc trò chuyện, mình bắt đầu lại nhé.")
            self._stay_awake()
            return True

        started = time.monotonic()
        try:
            self.brain.handle(command, self.say, self.confirm)
        except Exception:
            log.exception("Lỗi khi xử lý lệnh")
            self.say("Xin lỗi sếp, có lỗi xảy ra khi xử lý lệnh này.")
        log.info("Xử lý '%s' mất %.1fs", command, time.monotonic() - started)
        self._stay_awake()
        return True

    # ----- vòng lặp -----
    def run(self) -> None:
        name = self.settings.assistant_name
        if self.require_wake:
            print(f"[{name} đang chạy. Gọi '{name}' hoặc 'Ê PC' kèm lệnh. Ctrl+C để thoát.]")
        self.say(f"{name} đã sẵn sàng, thưa sếp.")
        was_awake = self.awake
        try:
            while True:
                if was_awake and not self.awake:
                    print(f"[Đang chờ gọi tên {name}...]", flush=True)
                was_awake = self.awake
                text = self.listener.listen(timeout=5)
                if text and not self.process(text):
                    break
        except KeyboardInterrupt:
            print()
            self.say("Tạm biệt sếp.")
