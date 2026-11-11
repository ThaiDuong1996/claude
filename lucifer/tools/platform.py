"""Các thao tác hệ thống cấp thấp. Viết cho Windows, có đường lui cho Linux/macOS
để có thể chạy thử/test trên máy khác."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

IS_WINDOWS = sys.platform.startswith("win")

# Mã phím ảo của Windows cho phím media / âm lượng
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3


def _creationflags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if IS_WINDOWS else 0


def start(target: str, *args: str) -> None:
    """Mở một chương trình / file / URL / URI (ms-settings:...).

    Trên Windows dùng lệnh `start` của cmd, nên hiểu được cả tên chương trình đã
    đăng ký trong App Paths như `chrome`, `winword`, `msedge`, `excel`.
    """
    if IS_WINDOWS:
        # Lệnh đi qua cmd.exe nên chặn ký tự đặc biệt để tránh chèn lệnh (&, |, >...)
        if any(c in part for part in (target, *args) for c in '&|<>^"%\r\n'):
            raise ValueError("Tên chương trình chứa ký tự không hợp lệ")
        # Tham số "" đầu tiên là tiêu đề cửa sổ (bắt buộc khi target có dấu cách)
        subprocess.Popen(
            ["cmd", "/c", "start", "", target, *args],
            creationflags=_creationflags(),
            close_fds=True,
        )
        return
    if sys.platform == "darwin":
        cmd = ["open", target, *(["--args", *args] if args else [])]
    elif shutil.which(target):
        cmd = [target, *args]
    else:
        cmd = ["xdg-open", target]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)


def open_path(path: str | Path) -> None:
    path = str(path)
    if IS_WINDOWS:
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        start(path)


def chrome_path() -> str | None:
    """Tìm chrome.exe; trả về None nếu chưa cài."""
    if not IS_WINDOWS:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            found = shutil.which(name)
            if found:
                return found
        return None
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")),
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")),
        Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))),
    ]
    for base in candidates:
        exe = base / "Google" / "Chrome" / "Application" / "chrome.exe"
        if exe.exists():
            return str(exe)
    return shutil.which("chrome")


def open_url(url: str, prefer_chrome: bool = True) -> str:
    """Mở URL, ưu tiên Google Chrome. Trả về tên trình duyệt đã dùng."""
    chrome = chrome_path() if prefer_chrome else None
    if chrome:
        subprocess.Popen([chrome, url], close_fds=True, creationflags=_creationflags())
        return "Google Chrome"
    webbrowser.open(url)
    return "trình duyệt mặc định"


def press_key(vk_code: int, times: int = 1) -> None:
    """Giả lập nhấn phím (âm lượng, media...)."""
    if not IS_WINDOWS:
        raise RuntimeError("Điều khiển phím media hiện chỉ hỗ trợ Windows")
    import ctypes

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    KEYEVENTF_KEYUP = 0x0002
    for _ in range(max(1, times)):
        user32.keybd_event(vk_code, 0, 0, 0)
        user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.02)


def run_quiet(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, creationflags=_creationflags(), timeout=30
    )
