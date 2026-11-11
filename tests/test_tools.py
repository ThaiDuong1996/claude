from lucifer.assistant import is_yes
from lucifer.tools import Tool, ToolRegistry, build_registry
from lucifer.tools.apps import best_match, find_known_app
from lucifer.tools.web import build_search_url, normalize_url


def test_schemas_are_strict():
    for schema in build_registry().schemas():
        s = schema["input_schema"]
        assert schema["strict"] is True
        assert s["additionalProperties"] is False
        assert set(s["required"]) == set(s["properties"])


def test_known_apps():
    assert find_known_app("Google Chrome").target == "chrome"
    assert find_known_app("ứng dụng máy tính").target == "calc"
    assert find_known_app("cài đặt").target == "ms-settings:"
    assert find_known_app("zalo") is None


def test_best_match_prefers_closest_name():
    names = ["Chrome Remote Desktop", "Google Chrome", "Zalo", "Spotify"]
    assert names[best_match("chrome", names)[0]] == "Google Chrome"
    assert names[best_match("dalo", names, threshold=0.7)[0]] == "Zalo"
    assert best_match("photoshop", names) is None


def test_urls():
    assert build_search_url("thời tiết Hà Nội", "google") == (
        "https://www.google.com/search?q=th%E1%BB%9Di+ti%E1%BA%BFt+H%C3%A0+N%E1%BB%99i"
    )
    assert normalize_url("facebook") == "https://www.facebook.com"
    assert normalize_url("vnexpress.net") == "https://vnexpress.net"
    assert normalize_url("javascript:alert(1)") is None
    assert normalize_url("file:///C:/Windows") is None


def test_registry_confirmation_and_validation():
    calls = []
    registry = ToolRegistry()
    registry.register(Tool(
        name="danger", description="", parameters={"x": {"type": "string"}},
        func=lambda x: calls.append(x) or "done", confirm=lambda a: "Chắc chưa?",
    ))
    # bị từ chối -> không chạy
    assert "từ chối" in registry.run("danger", {"x": "1"}, lambda q: False).content
    assert calls == []
    # đồng ý -> chạy
    assert registry.run("danger", {"x": "2"}, lambda q: True).content == "done"
    assert calls == ["2"]
    # thiếu tham số / tool lạ
    assert registry.run("danger", {}, lambda q: True).is_error
    assert registry.run("nope", {}, lambda q: True).is_error


def test_power_needs_confirmation_except_cancel():
    power = build_registry().tools["power"]
    assert power.confirm({"action": "shutdown"})
    assert power.confirm({"action": "cancel"}) is None


def test_is_yes():
    for answer in ["có", "Có, tắt đi", "ok", "đồng ý", "chắc chắn rồi", "đúng rồi", "co"]:
        assert is_yes(answer), answer
    for answer in ["không", "thôi", "huỷ đi", "dừng lại", "không có", "khong", "ờ để xem"]:
        assert not is_yes(answer), answer
