import pytest

from lucifer.brain import RuleBrain
from lucifer.tools import build_registry


@pytest.fixture(scope="module")
def brain():
    return RuleBrain(build_registry())


@pytest.mark.parametrize(
    "text, tool, args",
    [
        ("mở Chrome", "open_app", {"name": "Chrome"}),
        ("mở google chrome giúp tôi", "open_app", {"name": "google chrome"}),
        ("hãy mở Zalo đi", "open_app", {"name": "Zalo"}),
        ("mở google chrome và tìm kiếm thời tiết Hà Nội", "web_search",
         {"query": "thời tiết Hà Nội", "site": "google"}),
        ("mở chrome tìm kiếm giá vàng hôm nay", "web_search",
         {"query": "giá vàng hôm nay", "site": "google"}),
        ("tìm kiếm trên YouTube Sơn Tùng", "web_search", {"query": "Sơn Tùng", "site": "youtube"}),
        ("tìm công thức nấu phở trên youtube", "web_search",
         {"query": "công thức nấu phở", "site": "youtube"}),
        ("tìm đường đến Hồ Gươm", "web_search", {"query": "Hồ Gươm", "site": "google_maps"}),
        ("tìm hình ảnh mèo con", "web_search", {"query": "mèo con", "site": "google_images"}),
        ("mở bài hát Lạc Trôi", "play_youtube", {"query": "Lạc Trôi"}),
        ("phát nhạc Đen Vâu trên youtube", "play_youtube", {"query": "Đen Vâu"}),
        ("mở trang web vnexpress.net", "open_website", {"url": "vnexpress.net"}),
        ("mở github.com", "open_website", {"url": "github.com"}),
        ("mở thư mục tải xuống", "open_folder", {"name": "tải xuống"}),
        ("mở Downloads", "open_folder", {"name": "Downloads"}),
        ("đóng Chrome", "close_app", {"name": "Chrome"}),
        ("tắt ứng dụng Word", "close_app", {"name": "Word"}),
        ("tăng âm lượng", "set_volume", {"action": "up", "steps": 5}),
        ("giảm âm lượng 20%", "set_volume", {"action": "down", "steps": 10}),
        ("tắt tiếng", "set_volume", {"action": "mute", "steps": 1}),
        ("bài tiếp theo", "media_control", {"action": "next"}),
        ("tạm dừng", "media_control", {"action": "play_pause"}),
        ("mấy giờ rồi", "get_datetime", {}),
        ("hôm nay là thứ mấy", "get_datetime", {}),
        ("máy có nóng không", "system_status", {}),
        ("chụp màn hình", "take_screenshot", {}),
        ("khoá màn hình", "lock_screen", {}),
        ("tắt máy", "power", {"action": "shutdown"}),
        ("tắt máy tính đi", "power", {"action": "shutdown"}),
        ("khởi động lại máy", "power", {"action": "restart"}),
        ("huỷ tắt máy", "power", {"action": "cancel"}),
    ],
)
def test_parse(brain, text, tool, args):
    intent = brain.parse(text)
    assert intent.reply is None, intent.reply
    assert intent.tool == tool
    assert intent.args == args


@pytest.mark.parametrize("text", ["xin chào", "bạn là ai", "bạn làm được gì", "abc xyz linh tinh"])
def test_replies(brain, text):
    assert brain.parse(text).reply


def test_intents_match_tool_schemas(brain):
    """Mọi intent của bộ luật phải hợp lệ với schema của tool tương ứng."""
    registry = build_registry()
    for text in ["mở chrome", "tìm kiếm abc", "tăng âm lượng", "mấy giờ rồi", "tắt máy"]:
        intent = brain.parse(text)
        tool = registry.tools[intent.tool]
        assert set(intent.args) == set(tool.parameters)
