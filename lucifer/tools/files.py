"""Tìm và mở file trong các thư mục cá nhân của người dùng."""

from __future__ import annotations

import os
from pathlib import Path

from ..textutil import squash
from . import platform as plat
from .apps import folder_path
from .base import Tool, ToolRegistry

SEARCH_ROOTS = ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos")
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "AppData", "$RECYCLE.BIN", ".venv", "venv"}
EXECUTABLE_SUFFIXES = {
    ".exe", ".bat", ".cmd", ".com", ".ps1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".msi",
    ".scr", ".hta", ".cpl", ".reg", ".jar",
}
MAX_SCANNED = 50_000


def _roots(folder: str) -> list[Path]:
    if folder.strip():
        path = folder_path(folder)
        return [path] if path and path.is_dir() else []
    roots = []
    onedrive = os.environ.get("OneDrive")
    for sub in SEARCH_ROOTS:
        for base in filter(None, [Path.home(), Path(onedrive) if onedrive else None]):
            if (base / sub).is_dir():
                roots.append(base / sub)
    return roots


def search_files(query: str, folder: str) -> str:
    words = squash(query).split()
    if not words:
        return "Thiếu tên file cần tìm."
    roots = _roots(folder)
    if not roots:
        return f"Không tìm thấy thư mục '{folder}'."
    found: list[Path] = []
    scanned = 0
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for fname in filenames:
                scanned += 1
                if all(w in squash(fname) for w in words):
                    found.append(Path(dirpath) / fname)
            if scanned > MAX_SCANNED or len(found) >= 50:
                break
    if not found:
        return f"Không tìm thấy file nào khớp '{query}'."
    found.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    lines = [str(p) for p in found[:10]]
    return f"Tìm thấy {len(found)} file (mới nhất trước):\n" + "\n".join(lines)


def is_executable(path: str) -> bool:
    return Path(path).suffix.lower() in EXECUTABLE_SUFFIXES


def open_file(path: str) -> str:
    target = Path(os.path.expandvars(os.path.expanduser(path.strip().strip('"'))))
    if not target.exists():
        return f"File không tồn tại: {target}. Hãy dùng search_files để tìm đường dẫn đúng."
    plat.open_path(target)
    return f"Đã mở {target}."


def register(registry: ToolRegistry) -> None:
    registry.register(Tool(
        name="search_files",
        description=(
            "Tìm file theo tên trong Desktop, Documents, Downloads, Pictures, Music, Videos. "
            "Trả về tối đa 10 đường dẫn, file mới sửa gần nhất trước."
        ),
        parameters={
            "query": {"type": "string", "description": "Một phần tên file, ví dụ 'báo cáo tháng 10'"},
            "folder": {"type": "string",
                       "description": "Giới hạn trong một thư mục (vd 'Downloads'); chuỗi rỗng = tất cả"},
        },
        func=search_files,
    ))
    registry.register(Tool(
        name="open_file",
        description="Mở một file bằng ứng dụng mặc định. Cần đường dẫn đầy đủ (lấy từ search_files).",
        parameters={"path": {"type": "string", "description": "Đường dẫn đầy đủ tới file"}},
        func=open_file,
        confirm=lambda a: (f"File {Path(a['path']).name} là file chạy chương trình. "
                           "Bạn có chắc muốn mở không?" if is_executable(a["path"]) else None),
    ))
