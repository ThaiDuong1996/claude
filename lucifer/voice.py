"""Nghe (Speech-to-Text) và nói (Text-to-Speech)."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from typing import Protocol

from .config import Settings

log = logging.getLogger(__name__)


# =====================================================================
# Nghe
# =====================================================================

class Listener(Protocol):
    def listen(self, timeout: float | None = None) -> str | None: ...


class MicListener:
    """Thu âm từ micro bằng SpeechRecognition, rồi nhận dạng bằng Google hoặc Whisper."""

    def __init__(self, settings: Settings):
        import speech_recognition as sr

        self.sr = sr
        self.settings = settings
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.7  # im lặng bao lâu thì coi là hết câu
        self.microphone = sr.Microphone(sample_rate=16000)
        self._whisper = None
        if settings.stt_engine == "whisper":
            from faster_whisper import WhisperModel

            log.info("Đang tải model Whisper '%s' (lần đầu sẽ tải về, hơi lâu)...",
                     settings.whisper_model)
            self._whisper = WhisperModel(settings.whisper_model, device="auto", compute_type="int8")
        with self.microphone as source:
            log.info("Đang đo tiếng ồn nền, giữ im lặng 1 giây...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

    def listen(self, timeout: float | None = None) -> str | None:
        sr = self.sr
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=self.settings.phrase_time_limit
                )
        except sr.WaitTimeoutError:
            return None
        try:
            if self._whisper is not None:
                return self._transcribe_whisper(audio)
            return self.recognizer.recognize_google(audio, language=self.settings.language)
        except sr.UnknownValueError:
            return None  # không nghe rõ
        except sr.RequestError as exc:
            log.error("Lỗi dịch vụ nhận dạng giọng nói: %s", exc)
            time.sleep(1)
            return None

    def _transcribe_whisper(self, audio) -> str | None:
        import numpy as np

        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        lang = self.settings.language.split("-")[0]
        segments, _ = self._whisper.transcribe(samples, language=lang, vad_filter=True)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text or None


class KeyboardListener:
    """Gõ phím thay cho nói - để thử nghiệm khi chưa có micro."""

    def listen(self, timeout: float | None = None) -> str | None:
        try:
            return input("Bạn: ").strip() or None
        except EOFError:
            raise KeyboardInterrupt


# =====================================================================
# Nói
# =====================================================================

class Speaker(Protocol):
    def say(self, text: str) -> None: ...


class SilentSpeaker:
    def say(self, text: str) -> None:
        pass


class Pyttsx3Speaker:
    """Giọng đọc offline của Windows (SAPI5). Cần cài gói giọng tiếng Việt trong
    Settings > Time & Language > Speech nếu muốn đọc tiếng Việt."""

    def __init__(self, settings: Settings):
        import pyttsx3

        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 185)
        for voice in self.engine.getProperty("voices"):
            ident = f"{voice.id} {voice.name}".lower()  # vd "Microsoft An - Vietnamese (Vietnam)"
            if any(key in ident for key in ("vietnam", "vi-vn", "vi_vn")):
                self.engine.setProperty("voice", voice.id)
                break

    def say(self, text: str) -> None:
        self.engine.say(text)
        self.engine.runAndWait()


class EdgeSpeaker:
    """Giọng đọc neural tiếng Việt của Microsoft Edge (cần Internet, miễn phí)."""

    def __init__(self, settings: Settings):
        import edge_tts  # noqa: F401  (kiểm tra đã cài)
        import pygame

        self.voice = settings.tts_voice
        pygame.mixer.init()
        self.pygame = pygame

    async def _synthesize(self, text: str, path: str) -> None:
        import edge_tts

        await edge_tts.Communicate(text, self.voice, rate="+10%").save(path)

    def say(self, text: str) -> None:
        fd, path = tempfile.mkstemp(suffix=".mp3", prefix="lucifer_")
        os.close(fd)
        try:
            asyncio.run(self._synthesize(text, path))
            mixer = self.pygame.mixer
            mixer.music.load(path)
            mixer.music.play()
            while mixer.music.get_busy():
                time.sleep(0.05)
            mixer.music.unload()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


class FallbackSpeaker:
    """Thử lần lượt từng giọng; giọng nào lỗi (vd mất mạng) thì dùng giọng sau."""

    def __init__(self, speakers: list[Speaker]):
        self.speakers = speakers

    def say(self, text: str) -> None:
        for speaker in self.speakers:
            try:
                speaker.say(text)
                return
            except Exception as exc:
                log.warning("%s lỗi: %s", type(speaker).__name__, exc)


def build_speaker(settings: Settings) -> Speaker:
    chain: list[Speaker] = []
    order = {"edge": ["edge", "pyttsx3"], "pyttsx3": ["pyttsx3"], "none": []}
    for name in order.get(settings.tts_engine, ["edge", "pyttsx3"]):
        try:
            chain.append(EdgeSpeaker(settings) if name == "edge" else Pyttsx3Speaker(settings))
        except Exception as exc:
            log.warning("Không khởi tạo được giọng đọc %s: %s", name, exc)
    return FallbackSpeaker(chain) if chain else SilentSpeaker()
