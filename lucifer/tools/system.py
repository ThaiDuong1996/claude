"""Thông tin & điều khiển hệ thống: giờ, CPU/RAM/pin, âm lượng, media, khoá máy, nguồn."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from . import platform as plat
from .base import Tool, ToolRegistry

WEEKDAYS = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]


def get_datetime() -> str:
    now = dt.datetime.now()
    return (f"Bây giờ là {now:%H:%M}, {WEEKDAYS[now.weekday()]}, "
            f"ngày {now.day} tháng {now.month} năm {now.year}.")


def system_status() -> str:
    import psutil

    parts = [
        f"CPU {psutil.cpu_percent(interval=0.5):.0f}%",
        f"RAM {psutil.virtual_memory().percent:.0f}%",
    ]
    try:
        disk = psutil.disk_usage(str(Path.home().anchor or "/"))
        parts.append(f"ổ đĩa hệ thống còn trống {disk.free / 1024**3:.0f} GB")
    except OSError:
        pass
    battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if battery is not None:
        state = "đang sạc" if battery.power_plugged else "không cắm sạc"
        parts.append(f"pin {battery.percent:.0f}% ({state})")
    return "Tình trạng máy: " + ", ".join(parts) + "."


VOLUME_KEYS = {
    "up": plat.VK_VOLUME_UP,
    "down": plat.VK_VOLUME_DOWN,
    "mute": plat.VK_VOLUME_MUTE,
}


def set_volume(action: str, steps: int) -> str:
    if action not in VOLUME_KEYS:
        return f"Hành động không hợp lệ: {action}"
    if action == "mute":
        plat.press_key(plat.VK_VOLUME_MUTE)
        return "Đã bật/tắt tiếng."
    steps = max(1, min(int(steps), 50))
    plat.press_key(VOLUME_KEYS[action], steps)
    word = "tăng" if action == "up" else "giảm"
    return f"Đã {word} âm lượng khoảng {steps * 2}%."


MEDIA_KEYS = {
    "play_pause": plat.VK_MEDIA_PLAY_PAUSE,
    "next": plat.VK_MEDIA_NEXT,
    "previous": plat.VK_MEDIA_PREV,
    "stop": plat.VK_MEDIA_STOP,
}


def media_control(action: str) -> str:
    if action not in MEDIA_KEYS:
        return f"Hành động không hợp lệ: {action}"
    plat.press_key(MEDIA_KEYS[action])
    return f"Đã gửi lệnh media: {action}."


def lock_screen() -> str:
    if not plat.IS_WINDOWS:
        return "Khoá màn hình hiện chỉ hỗ trợ Windows."
    import ctypes

    ctypes.windll.user32.LockWorkStation()  # type: ignore[attr-defined]
    return "Đã khoá màn hình."


POWER_COMMANDS = {
    "shutdown": (["shutdown", "/s", "/t", "30"], "Máy sẽ tắt sau 30 giây."),
    "restart": (["shutdown", "/r", "/t", "30"], "Máy sẽ khởi động lại sau 30 giây."),
    "cancel": (["shutdown", "/a"], "Đã huỷ lệnh tắt/khởi động lại."),
    "sleep": (["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], "Đang cho máy ngủ."),
}

POWER_NAMES = {"shutdown": "tắt máy", "restart": "khởi động lại máy", "sleep": "cho máy ngủ"}


def power(action: str) -> str:
    if action not in POWER_COMMANDS:
        return f"Hành động không hợp lệ: {action}"
    if not plat.IS_WINDOWS:
        return "Điều khiển nguồn hiện chỉ hỗ trợ Windows."
    cmd, message = POWER_COMMANDS[action]
    result = plat.run_quiet(cmd)
    if result.returncode != 0 and action == "cancel":
        return "Không có lệnh tắt máy nào đang chờ."
    if action in ("shutdown", "restart"):
        message += " Nói 'huỷ tắt máy' nếu đổi ý."
    return message


def take_screenshot() -> str:
    from PIL import ImageGrab

    folder = Path.home() / "Pictures" / "Lucifer"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"screenshot_{dt.datetime.now():%Y%m%d_%H%M%S}.png"
    ImageGrab.grab(all_screens=True).save(path)
    return f"Đã chụp màn hình, lưu tại {path}."


def register(registry: ToolRegistry) -> None:
    registry.register(Tool(
        name="get_datetime",
        description="Lấy giờ, thứ và ngày tháng hiện tại.",
        parameters={},
        func=get_datetime,
    ))
    registry.register(Tool(
        name="system_status",
        description="Xem tình trạng máy: % CPU, % RAM, dung lượng ổ đĩa trống, pin.",
        parameters={},
        func=system_status,
    ))
    registry.register(Tool(
        name="set_volume",
        description="Tăng, giảm hoặc bật/tắt tiếng loa. Mỗi bước khoảng 2%.",
        parameters={
            "action": {"type": "string", "enum": list(VOLUME_KEYS)},
            "steps": {"type": "integer", "description": "Số bước (1-50). Mặc định nên dùng 5 = 10%."},
        },
        func=set_volume,
    ))
    registry.register(Tool(
        name="media_control",
        description="Điều khiển nhạc/video đang phát: tạm dừng/tiếp tục, bài tiếp, bài trước, dừng.",
        parameters={"action": {"type": "string", "enum": list(MEDIA_KEYS)}},
        func=media_control,
    ))
    registry.register(Tool(
        name="lock_screen",
        description="Khoá màn hình Windows.",
        parameters={},
        func=lock_screen,
    ))
    registry.register(Tool(
        name="power",
        description=(
            "Tắt máy (shutdown), khởi động lại (restart), cho máy ngủ (sleep), hoặc huỷ lệnh "
            "tắt/khởi động lại đang chờ (cancel). Các lệnh trừ cancel cần xác nhận."
        ),
        parameters={"action": {"type": "string", "enum": list(POWER_COMMANDS)}},
        func=power,
        confirm=lambda a: (f"Bạn có chắc muốn {POWER_NAMES[a['action']]} không?"
                           if a.get("action") in POWER_NAMES else None),
    ))
    registry.register(Tool(
        name="take_screenshot",
        description="Chụp toàn bộ màn hình và lưu vào thư mục Pictures/Lucifer.",
        parameters={},
        func=take_screenshot,
    ))
