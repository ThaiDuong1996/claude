"""Tìm kiếm web, mở trang web, phát video YouTube (mở bằng Google Chrome nếu có)."""

from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.request

from ..textutil import squash
from . import platform as plat
from .base import Tool, ToolRegistry

log = logging.getLogger(__name__)

SEARCH_URLS = {
    "google": "https://www.google.com/search?q={q}",
    "youtube": "https://www.youtube.com/results?search_query={q}",
    "wikipedia": "https://vi.wikipedia.org/w/index.php?search={q}",
    "google_maps": "https://www.google.com/maps/search/{q}",
    "google_images": "https://www.google.com/search?tbm=isch&q={q}",
}

POPULAR_SITES = {
    "facebook": "https://www.facebook.com",
    "messenger": "https://www.messenger.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "google drive": "https://drive.google.com",
    "drive": "https://drive.google.com",
    "google dich": "https://translate.google.com",
    "google translate": "https://translate.google.com",
    "zalo": "https://chat.zalo.me",
    "tiktok": "https://www.tiktok.com",
    "shopee": "https://shopee.vn",
    "lazada": "https://www.lazada.vn",
    "github": "https://github.com",
    "claude": "https://claude.ai",
    "netflix": "https://www.netflix.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://x.com",
    "vnexpress": "https://vnexpress.net",
}


def build_search_url(query: str, site: str) -> str:
    template = SEARCH_URLS.get(site, SEARCH_URLS["google"])
    return template.format(q=urllib.parse.quote_plus(query.strip()))


def web_search(query: str, site: str) -> str:
    if not query.strip():
        return "Thiếu nội dung cần tìm."
    browser = plat.open_url(build_search_url(query, site))
    return f"Đã tìm '{query}' trên {site} bằng {browser}."


def normalize_url(url: str) -> str | None:
    """Chuẩn hoá địa chỉ web; chỉ chấp nhận http/https. Trả về None nếu không hợp lệ."""
    text = url.strip()
    key = squash(text)
    for prefix in ("trang ", "trang web ", "website "):
        if key.startswith(prefix):
            key = key[len(prefix):]
    if key in POPULAR_SITES:
        return POPULAR_SITES[key]
    if "://" not in text:
        if " " in text or "." not in text:
            return None
        text = "https://" + text
    parsed = urllib.parse.urlparse(text)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return text


def open_website(url: str) -> str:
    target = normalize_url(url)
    if target is None:
        # Không phải địa chỉ hợp lệ -> tìm trên Google
        return web_search(url, "google")
    browser = plat.open_url(target)
    return f"Đã mở {target} bằng {browser}."


def first_youtube_video(query: str, timeout: float = 6.0) -> str | None:
    url = build_search_url(query, "youtube")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "vi,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except OSError as exc:
        log.warning("Không tải được kết quả YouTube: %s", exc)
        return None
    match = re.search(r'"videoId":"([\w-]{11})"', html)
    return match.group(1) if match else None


def play_youtube(query: str) -> str:
    video_id = first_youtube_video(query)
    if video_id:
        browser = plat.open_url(f"https://www.youtube.com/watch?v={video_id}")
        return f"Đang phát video đầu tiên cho '{query}' trên YouTube ({browser})."
    browser = plat.open_url(build_search_url(query, "youtube"))
    return f"Không lấy được video, đã mở trang kết quả YouTube cho '{query}' ({browser})."


def register(registry: ToolRegistry) -> None:
    registry.register(Tool(
        name="web_search",
        description=(
            "Mở Google Chrome và tìm kiếm. Dùng khi người dùng nói 'tìm kiếm...', 'tra cứu...', "
            "'mở chrome tìm...', 'tìm đường đến...', 'tìm ảnh...'."
        ),
        parameters={
            "query": {"type": "string", "description": "Nội dung cần tìm, giữ nguyên tiếng Việt có dấu"},
            "site": {
                "type": "string",
                "enum": list(SEARCH_URLS),
                "description": "Nơi tìm: google (mặc định), youtube, wikipedia, google_maps, google_images",
            },
        },
        func=web_search,
    ))
    registry.register(Tool(
        name="open_website",
        description="Mở một trang web theo địa chỉ hoặc tên quen thuộc (facebook, gmail, youtube, shopee...).",
        parameters={"url": {"type": "string", "description": "Địa chỉ web hoặc tên trang"}},
        func=open_website,
    ))
    registry.register(Tool(
        name="play_youtube",
        description="Phát ngay video/bài hát đầu tiên tìm được trên YouTube, ví dụ 'mở bài Lạc Trôi'.",
        parameters={"query": {"type": "string", "description": "Tên bài hát / video"}},
        func=play_youtube,
    ))
