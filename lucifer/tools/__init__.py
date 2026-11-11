"""Danh sách tool mà Lucifer được phép dùng. Thêm tool mới: viết hàm, rồi đăng ký
trong hàm `register()` của module tương ứng (xem README, mục "Thêm lệnh mới")."""

from __future__ import annotations

from . import apps, files, system, web
from .base import Confirmer, Tool, ToolRegistry, ToolResult

__all__ = ["Confirmer", "Tool", "ToolRegistry", "ToolResult", "build_registry"]


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for module in (apps, web, system, files):
        module.register(registry)
    return registry
