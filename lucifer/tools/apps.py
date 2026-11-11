"""Mở / đóng ứng dụng và thư mục."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Callable

from ..textutil import squash
from . import platform as plat
from .base import Tool, ToolRegistry

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class KnownApp:
    title: str
    target: str  # truyền cho lệnh `start` của Windows
    processes: tuple[str, ...] = ()
    aliases: tuple[str, ...] = field(default_factory=tuple)


KNOWN_APPS: list[KnownApp] = [
    KnownApp("Google Chrome", "chrome", ("chrome.exe",),
             ("chrome", "google chrome", "gu gô chrome", "crom", "trình duyệt chrome", "trình duyệt")),
    KnownApp("Microsoft Edge", "msedge", ("msedge.exe",), ("edge", "microsoft edge")),
    KnownApp("Firefox", "firefox", ("firefox.exe",), ("firefox", "fire fox")),
    KnownApp("Notepad", "notepad", ("notepad.exe",), ("notepad", "note pad", "sổ ghi chép", "ghi chú")),
    KnownApp("Máy tính (Calculator)", "calc", ("CalculatorApp.exe", "calc.exe"),
             ("calculator", "calc", "máy tính", "máy tính bỏ túi", "máy tính cầm tay")),
    KnownApp("File Explorer", "explorer", (),  # không bao giờ đóng explorer.exe
             ("file explorer", "explorer", "quản lý file", "quản lý tệp", "this pc", "my computer")),
    KnownApp("Command Prompt", "cmd", ("cmd.exe",), ("cmd", "command prompt", "dấu nhắc lệnh")),
    KnownApp("PowerShell", "powershell", ("powershell.exe",), ("powershell", "power shell")),
    KnownApp("Windows Terminal", "wt", ("WindowsTerminal.exe",), ("terminal", "windows terminal")),
    KnownApp("Paint", "mspaint", ("mspaint.exe",), ("paint", "ms paint", "vẽ")),
    KnownApp("Task Manager", "taskmgr", ("Taskmgr.exe",),
             ("task manager", "quản lý tác vụ", "trình quản lý tác vụ")),
    KnownApp("Cài đặt Windows", "ms-settings:", ("SystemSettings.exe",),
             ("settings", "cài đặt", "thiết lập", "setting")),
    KnownApp("Control Panel", "control", (), ("control panel", "bảng điều khiển")),
    KnownApp("Microsoft Word", "winword", ("WINWORD.EXE",), ("word", "microsoft word", "uốt")),
    KnownApp("Microsoft Excel", "excel", ("EXCEL.EXE",), ("excel", "microsoft excel", "ếch xeo")),
    KnownApp("Microsoft PowerPoint", "powerpnt", ("POWERPNT.EXE",),
             ("powerpoint", "power point", "microsoft powerpoint")),
    KnownApp("Microsoft Outlook", "outlook", ("OUTLOOK.EXE",), ("outlook", "out look")),
    KnownApp("Visual Studio Code", "code", ("Code.exe",),
             ("vs code", "vscode", "visual studio code", "code")),
    KnownApp("Camera", "microsoft.windows.camera:", ("WindowsCamera.exe",), ("camera", "máy ảnh")),
    KnownApp("Microsoft Store", "ms-windows-store:", ("WinStore.App.exe",),
             ("store", "microsoft store", "cửa hàng")),
]

# Tiến trình hệ thống - tuyệt đối không đóng
PROTECTED_PROCESSES = {
    "explorer.exe", "svchost.exe", "csrss.exe", "winlogon.exe", "lsass.exe", "services.exe",
    "smss.exe", "wininit.exe", "system", "registry", "dwm.exe", "python.exe", "pythonw.exe",
    "py.exe", "conhost.exe", "fontdrvhost.exe", "sihost.exe",
}

FILLER = re.compile(
    r"\b(ung dung|phan mem|chuong trinh|app|cho toi|giup toi|giup minh|cho minh|len|di|nhe|"
    r"cua so)\b"
)


def clean_name(name: str) -> str:
    return re.sub(r"\s+", " ", FILLER.sub(" ", squash(name))).strip()


def score(query: str, candidate: str) -> float:
    """Điểm giống nhau 0..1 giữa tên người dùng nói và tên ứng dụng (đều đã squash)."""
    if not query or not candidate:
        return 0.0
    if query == candidate:
        return 1.0
    if re.search(rf"(?<![a-z0-9]){re.escape(query)}(?![a-z0-9])", candidate):
        return 0.9
    if candidate.startswith(query) or query.startswith(candidate):
        return 0.8
    return SequenceMatcher(None, query, candidate).ratio()


def best_match(query: str, names: list[str], threshold: float = 0.72) -> tuple[int, float] | None:
    q = clean_name(query)
    best: tuple[int, float, int] | None = None  # (index, score, length)
    for i, name in enumerate(names):
        cand = squash(name)
        s = score(q, cand)
        if s < threshold:
            continue
        if best is None or s > best[1] or (s == best[1] and len(cand) < best[2]):
            best = (i, s, len(cand))
    return (best[0], best[1]) if best else None


def find_known_app(name: str) -> KnownApp | None:
    q = clean_name(name)
    for app in KNOWN_APPS:
        if q in {squash(a) for a in app.aliases} or q == squash(app.title):
            return app
    return None


# ---------- Ứng dụng trong Start Menu (Windows) ----------

@dataclass(frozen=True)
class StartEntry:
    name: str
    launch: Callable[[], None]


def _start_menu_dirs() -> list[Path]:
    env = os.environ
    dirs = [
        Path(env.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
        Path(env.get("APPDATA", str(Path.home() / "AppData/Roaming")))
        / "Microsoft/Windows/Start Menu/Programs",
        Path.home() / "Desktop",
        Path(env.get("PUBLIC", r"C:\Users\Public")) / "Desktop",
    ]
    return [d for d in dirs if d.is_dir()]


def _scan_shortcuts() -> list[StartEntry]:
    entries: list[StartEntry] = []
    for folder in _start_menu_dirs():
        for pattern in ("*.lnk", "*.url", "*.appref-ms"):
            for path in folder.rglob(pattern):
                stem = path.stem
                if re.search(r"(?i)uninstall|gỡ cài đặt|readme|help", stem):
                    continue
                entries.append(StartEntry(stem, lambda p=path: plat.open_path(p)))
    return entries


def _scan_start_apps() -> list[StartEntry]:
    """Danh sách app của Start Menu kể cả app Store (UWP) qua PowerShell Get-StartApps."""
    try:
        proc = plat.run_quiet(
            ["powershell", "-NoProfile", "-Command",
             "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress"]
        )
        data = json.loads(proc.stdout or "[]")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        log.warning("Không đọc được Get-StartApps: %s", exc)
        return []
    if isinstance(data, dict):
        data = [data]
    entries = []
    for item in data:
        name, app_id = item.get("Name"), item.get("AppID")
        if not name or not app_id:
            continue
        entries.append(StartEntry(
            name,
            lambda a=app_id: subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{a}"]),
        ))
    return entries


@lru_cache(maxsize=1)
def installed_apps() -> tuple[StartEntry, ...]:
    if not plat.IS_WINDOWS:
        return ()
    return tuple(_scan_shortcuts() + _scan_start_apps())


def open_app(name: str) -> str:
    app = find_known_app(name)
    if app:
        plat.start(app.target)
        return f"Đã mở {app.title}."

    entries = list(installed_apps())
    match = best_match(name, [e.name for e in entries])
    if match:
        entry = entries[match[0]]
        entry.launch()
        return f"Đã mở {entry.name}."

    # Thử so khớp gần đúng với bảng ứng dụng quen thuộc
    aliases = [(app, alias) for app in KNOWN_APPS for alias in app.aliases]
    match = best_match(name, [alias for _, alias in aliases], threshold=0.8)
    if match:
        app = aliases[match[0]][0]
        plat.start(app.target)
        return f"Đã mở {app.title}."

    return (f"Không tìm thấy ứng dụng '{name}' trên máy. "
            "Hãy hỏi lại người dùng tên chính xác của ứng dụng.")


# ---------- Đóng ứng dụng ----------

def _matching_processes(name: str) -> list[str]:
    import psutil

    app = find_known_app(name)
    if app:
        wanted = {p.lower() for p in app.processes}
        running = set()
        for proc in psutil.process_iter(["name"]):
            pname = (proc.info.get("name") or "").lower()
            if pname in wanted:
                running.add(proc.info["name"])
        return sorted(running)

    q = clean_name(name)
    running = set()
    for proc in psutil.process_iter(["name"]):
        pname = proc.info.get("name") or ""
        base = squash(re.sub(r"(?i)\.exe$", "", pname))
        if q and score(q, base) >= 0.85:
            running.add(pname)
    return sorted(running)


def close_app(name: str) -> str:
    import psutil

    procs = [p for p in _matching_processes(name) if p.lower() not in PROTECTED_PROCESSES]
    if not procs:
        return f"Không thấy ứng dụng '{name}' đang chạy (hoặc đó là tiến trình hệ thống)."
    for pname in procs:
        if plat.IS_WINDOWS:
            # Không dùng /F: gửi lệnh đóng bình thường để ứng dụng kịp hỏi lưu file
            plat.run_quiet(["taskkill", "/IM", pname])
        else:
            for proc in psutil.process_iter(["name"]):
                if proc.info.get("name") == pname:
                    proc.terminate()
    return f"Đã gửi lệnh đóng: {', '.join(procs)}."


# ---------- Thư mục ----------

KNOWN_FOLDERS: dict[str, tuple[str, ...]] = {
    "Desktop": ("desktop", "man hinh chinh", "man hinh desktop"),
    "Downloads": ("downloads", "download", "tai xuong", "thu muc tai xuong", "ban tai"),
    "Documents": ("documents", "document", "tai lieu", "van ban"),
    "Pictures": ("pictures", "picture", "hinh anh", "anh", "hinh"),
    "Music": ("music", "nhac", "am nhac"),
    "Videos": ("videos", "video", "phim"),
    "": ("home", "thu muc nguoi dung", "thu muc ca nhan", "user"),
}


def folder_path(name: str) -> Path | None:
    raw = Path(os.path.expandvars(os.path.expanduser(name.strip().strip('"'))))
    if raw.is_absolute() and raw.is_dir():
        return raw
    q = re.sub(r"\b(thu muc|folder|cua toi|cua minh)\b", " ", squash(name))
    q = re.sub(r"\s+", " ", q).strip()
    for sub, aliases in KNOWN_FOLDERS.items():
        if q in aliases or q == sub.lower():
            path = Path.home() / sub if sub else Path.home()
            # OneDrive có thể chuyển Desktop/Documents/Pictures vào thư mục OneDrive
            onedrive = os.environ.get("OneDrive")
            if sub and not path.exists() and onedrive and (Path(onedrive) / sub).exists():
                path = Path(onedrive) / sub
            return path
    return None


def open_folder(name: str) -> str:
    path = folder_path(name)
    if path is None or not path.exists():
        return (f"Không biết thư mục '{name}'. Hỗ trợ: Desktop, Downloads, Documents, "
                "Pictures, Music, Videos, thư mục người dùng hoặc đường dẫn đầy đủ.")
    plat.open_path(path)
    return f"Đã mở thư mục {path}."


def register(registry: ToolRegistry) -> None:
    registry.register(Tool(
        name="open_app",
        description=(
            "Mở một ứng dụng trên máy Windows theo tên, ví dụ 'chrome', 'word', 'zalo', "
            "'máy tính', 'notepad', 'cài đặt', 'spotify'. Tự tìm trong Start Menu. "
            "Chỉ mở ứng dụng; muốn tìm kiếm trên web thì dùng web_search."
        ),
        parameters={"name": {"type": "string", "description": "Tên ứng dụng như người dùng nói"}},
        func=open_app,
    ))
    registry.register(Tool(
        name="close_app",
        description="Đóng một ứng dụng đang chạy theo tên (ví dụ 'chrome', 'word'). Cần xác nhận.",
        parameters={"name": {"type": "string", "description": "Tên ứng dụng cần đóng"}},
        func=close_app,
        confirm=lambda a: f"Bạn có chắc muốn đóng {a['name']} không? Dữ liệu chưa lưu có thể mất.",
    ))
    registry.register(Tool(
        name="open_folder",
        description=(
            "Mở thư mục trong File Explorer: Desktop, Downloads (tải xuống), Documents (tài liệu), "
            "Pictures (hình ảnh), Music (nhạc), Videos, thư mục người dùng, hoặc một đường dẫn đầy đủ."
        ),
        parameters={"name": {"type": "string", "description": "Tên thư mục hoặc đường dẫn"}},
        func=open_folder,
    ))
