"""Khung đăng ký "tool" - các hàm mà AI được phép gọi để điều khiển máy.

Nguyên tắc an toàn: AI KHÔNG được chạy lệnh shell tuỳ ý. Nó chỉ chọn một tool
trong danh sách trắng (whitelist) này. Tool nguy hiểm (tắt máy, đóng ứng dụng,
chạy file thực thi...) phải được người dùng xác nhận trước khi chạy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

log = logging.getLogger(__name__)

# Hàm hỏi xác nhận: nhận câu hỏi, trả về True nếu người dùng đồng ý
Confirmer = Callable[[str], bool]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, dict[str, Any]]
    func: Callable[..., str]
    # Trả về câu hỏi xác nhận nếu lần gọi này cần xác nhận, None nếu không cần
    confirm: Callable[[dict[str, Any]], str | None] | None = None

    def schema(self) -> dict[str, Any]:
        """Định nghĩa tool theo định dạng Claude API (strict: input luôn đúng schema)."""
        return {
            "name": self.name,
            "description": self.description,
            "strict": True,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.parameters),
                "additionalProperties": False,
            },
        }


@dataclass
class ToolResult:
    content: str
    is_error: bool = False


@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> Tool:
        if tool.name in self.tools:
            raise ValueError(f"Tool '{tool.name}' đã tồn tại")
        self.tools[tool.name] = tool
        return tool

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self.tools.values()]

    def names(self) -> list[str]:
        return list(self.tools)

    def run(self, name: str, args: dict[str, Any], confirmer: Confirmer | None) -> ToolResult:
        tool = self.tools.get(name)
        if tool is None:
            return ToolResult(f"Không có tool tên '{name}'.", is_error=True)
        if not isinstance(args, dict):
            return ToolResult("Tham số phải là một object.", is_error=True)
        missing = [p for p in tool.parameters if p not in args]
        unknown = [p for p in args if p not in tool.parameters]
        if missing or unknown:
            return ToolResult(
                f"Tham số không hợp lệ. Thiếu: {missing}, thừa: {unknown}.", is_error=True
            )

        question = tool.confirm(args) if tool.confirm else None
        if question:
            if confirmer is None or not confirmer(question):
                log.info("Người dùng từ chối tool %s %s", name, args)
                return ToolResult("Người dùng đã từ chối thao tác này. Không thực hiện.")

        log.info("Chạy tool %s %s", name, args)
        try:
            return ToolResult(tool.func(**args))
        except Exception as exc:  # tool lỗi không được làm sập trợ lý
            log.exception("Tool %s lỗi", name)
            return ToolResult(f"Lỗi khi chạy {name}: {exc}", is_error=True)
