import pytest

from lucifer.textutil import normalize, prepare
from lucifer.wakeword import WakeWordDetector


def test_normalize_keeps_length():
    text = "Lucifer ơi, mở Chrome tìm kiếm “thời tiết” Đà Nẵng!"
    assert len(normalize(text)) == len(prepare(text))
    assert normalize("Đà Nẵng") == "da nang"


@pytest.mark.parametrize(
    "heard, command",
    [
        ("Lucifer mở Chrome", "mở Chrome"),
        ("lucifer, mở google chrome và tìm kiếm thời tiết Hà Nội", "mở google chrome và tìm kiếm thời tiết Hà Nội"),
        ("Lu xi phơ mở Zalo", "mở Zalo"),
        ("Lu-si-phe tăng âm lượng", "tăng âm lượng"),
        ("Ê PC mở nhạc", "mở nhạc"),
        ("ê pi xi, mấy giờ rồi", "mấy giờ rồi"),
        ("Mở Chrome đi Lucifer", "Mở Chrome đi"),
    ],
)
def test_wake_word_with_command(heard, command):
    result = WakeWordDetector().detect(heard)
    assert result.detected
    assert result.command == command


@pytest.mark.parametrize("heard", ["Lucifer", "lucifer ơi", "Ê PC", "ê lucifer"])
def test_wake_word_only(heard):
    result = WakeWordDetector().detect(heard)
    assert result.detected
    assert result.command in ("", "ơi")


@pytest.mark.parametrize("heard", ["mở chrome", "hôm nay trời đẹp", "lucy ferris", "épc"])
def test_no_wake_word(heard):
    assert not WakeWordDetector().detect(heard).detected


def test_custom_wake_words():
    detector = WakeWordDetector(["Jarvis", "ê máy"])
    assert detector.detect("Jarvis mở word").command == "mở word"
    assert detector.detect("Ê máy, mở excel").command == "mở excel"
    assert not detector.detect("Lucifer mở word").detected
