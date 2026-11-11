"""Kiểm tra vòng lặp tool của ClaudeBrain bằng client giả (không gọi API thật)."""

from types import SimpleNamespace as NS

import pytest

from lucifer.brain import ClaudeBrain
from lucifer.config import Settings
from lucifer.tools import Tool, ToolRegistry


def text(t):
    return NS(type="text", text=t)


def tool_use(id_, name, args):
    return NS(type="tool_use", id=id_, name=name, input=args)


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kwargs):
        # chụp lại messages tại thời điểm gọi
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.ran = []
    reg.register(Tool("web_search", "", {"query": {"type": "string"}, "site": {"type": "string"}},
                      lambda query, site: reg.ran.append(("web_search", query)) or f"Đã tìm {query}"))
    reg.register(Tool("power", "", {"action": {"type": "string"}},
                      lambda action: reg.ran.append(("power", action)) or "Máy sẽ tắt",
                      confirm=lambda a: "Tắt máy?"))
    return reg


def test_tool_loop(registry):
    client = FakeClient([
        NS(stop_reason="tool_use", content=[
            text("Vâng."), tool_use("t1", "web_search", {"query": "thời tiết", "site": "google"})]),
        NS(stop_reason="end_turn", content=[text("Đã tìm thời tiết, thưa sếp.")]),
    ])
    brain = ClaudeBrain(Settings(), registry, client=client)
    spoken = []
    reply = brain.handle("mở chrome tìm thời tiết", spoken.append, lambda q: True)

    assert registry.ran == [("web_search", "thời tiết")]
    assert spoken == ["Vâng.", "Đã tìm thời tiết, thưa sếp."]
    assert reply == "Vâng. Đã tìm thời tiết, thưa sếp."
    # request thứ 2 phải chứa tool_result khớp id
    last_user = client.requests[1]["messages"][-1]
    assert last_user["role"] == "user"
    assert last_user["content"][0]["tool_use_id"] == "t1"
    assert last_user["content"][0]["content"] == "Đã tìm thời tiết"
    # cấu hình request
    req = client.requests[0]
    assert req["model"] == "claude-opus-5-5"
    assert req["output_config"] == {"effort": "low"}
    assert req["fallbacks"] == "default"
    assert all(t["strict"] for t in req["tools"])


def test_declined_confirmation_is_reported(registry):
    client = FakeClient([
        NS(stop_reason="tool_use", content=[tool_use("t1", "power", {"action": "shutdown"})]),
        NS(stop_reason="end_turn", content=[text("Đã huỷ tắt máy.")]),
    ])
    brain = ClaudeBrain(Settings(), registry, client=client)
    brain.handle("tắt máy", lambda t: None, lambda q: False)
    assert registry.ran == []
    result = client.requests[1]["messages"][-1]["content"][0]
    assert "từ chối" in result["content"]


def test_refusal_and_history_stays_valid(registry):
    client = FakeClient([NS(stop_reason="refusal", content=[])])
    brain = ClaudeBrain(Settings(), registry, client=client)
    spoken = []
    brain.handle("abc", spoken.append, lambda q: True)
    assert spoken and "không thể" in spoken[0]
    assert brain.messages[-1]["role"] == "assistant"


def test_max_tokens_with_dangling_tool_use_is_closed(registry):
    client = FakeClient([
        NS(stop_reason="max_tokens", content=[tool_use("t9", "web_search", {"query": "x"})]),
    ])
    brain = ClaudeBrain(Settings(), registry, client=client)
    brain.handle("abc", lambda t: None, lambda q: True)
    assert registry.ran == []
    assert brain.messages[-1]["content"][0]["tool_use_id"] == "t9"
