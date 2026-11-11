# Lucifer: trợ lý giọng nói điều khiển máy tính Windows

Bạn gọi tên rồi ra lệnh bằng giọng nói, Lucifer làm theo trên máy, giống J.A.R.V.I.S. trong Iron Man.

```
Bạn:     "Lucifer, mở Chrome và tìm kiếm thời tiết Hà Nội"
Lucifer: "Đã tìm thời tiết Hà Nội trên Google, thưa sếp."   (Chrome mở ra với kết quả tìm kiếm)

Bạn:     "Ê PC, mở Zalo"
Lucifer: "Đã mở Zalo."

Bạn:     "Lucifer"
Lucifer: *bíp* "Vâng, tôi đây."
Bạn:     "Phát bài Lạc Trôi"   (sau khi được gọi, không cần nhắc tên lại trong 15 giây)
```

## Tính năng

| Nhóm | Ví dụ câu lệnh |
|---|---|
| Mở / đóng ứng dụng | "mở Chrome", "mở Word", "mở Zalo", "mở máy tính", "mở cài đặt", "đóng Chrome" |
| Tìm kiếm | "mở Chrome tìm giá vàng hôm nay", "tìm trên YouTube Sơn Tùng", "tìm đường đến Hồ Gươm", "tìm hình ảnh mèo con" |
| Web & nhạc | "mở Facebook", "mở vnexpress.net", "phát bài Lạc Trôi", "bài tiếp theo", "tạm dừng" |
| Hệ thống | "tăng âm lượng", "giảm âm lượng 20%", "tắt tiếng", "mấy giờ rồi", "máy có nóng không" |
| File & thư mục | "mở thư mục tải xuống", "tìm file báo cáo tháng 10" |
| Khác | "chụp màn hình", "khoá màn hình", "tắt máy" (có hỏi xác nhận), "huỷ tắt máy" |
| Trò chuyện (khi có AI) | "giải thích giúp tôi lỗi này", "dịch câu này sang tiếng Anh", "kể chuyện cười đi" |

Lucifer có **2 chế độ bộ não**:

- **Claude AI** (khi bạn có API key): hiểu ngôn ngữ tự nhiên, câu lệnh nhiều bước, trò chuyện và hỏi lại khi lệnh chưa rõ. Nếu mất mạng, nó tự chuyển sang chế độ offline.
- **Offline (bộ luật)**: không cần Internet hay API key, miễn phí, nhưng chỉ hiểu các mẫu câu như bảng trên.

## Cài đặt (Windows 10/11)

1. Cài [Python 3.10 trở lên](https://www.python.org/downloads/). Khi cài, nhớ tick **"Add python.exe to PATH"**.
2. Tải project này về, rồi nhấp đúp **`setup.bat`**. Script sẽ tạo môi trường ảo và cài thư viện.
3. (Tuỳ chọn, nên làm) Mở file `.env` và điền `ANTHROPIC_API_KEY=...` để bật AI. Key lấy ở [console.anthropic.com](https://console.anthropic.com).
4. Nhấp đúp **`run.bat`**, rồi nói *"Lucifer, mở Chrome"*.

Cài bằng tay:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m lucifer
```

## Cách chạy

```bat
python -m lucifer                 :: nghe micro, gọi "Lucifer" hoặc "Ê PC" để ra lệnh
python -m lucifer --text          :: gõ phím thay vì nói (thử khi chưa có micro)
python -m lucifer --brain rules   :: ép dùng chế độ offline
python -m lucifer --stt whisper   :: nhận dạng giọng nói offline (cài thêm requirements-whisper.txt)
python -m lucifer --no-wake       :: không cần gọi tên, câu nào nghe được cũng coi là lệnh
python -m lucifer --list-tools    :: xem danh sách lệnh hệ thống
python -m lucifer --debug         :: in log chi tiết
```

Một số câu điều khiển chính trợ lý:

- "tạm biệt" / "nghỉ đi": quay về chế độ chờ gọi tên.
- "quên hết đi": xoá cuộc trò chuyện với AI.
- "thoát chương trình" / "tắt Lucifer": thoát hẳn.

Cấu hình (tên, từ đánh thức, giọng đọc, model...) nằm trong file `.env`. Xem chú thích trong [`.env.example`](.env.example).
Ví dụ, muốn đổi tên thành Jarvis: `LUCIFER_NAME=Jarvis` và `LUCIFER_WAKE_WORDS=jarvis,gia vis,ê pc`.

## Cách hoạt động

```
 Micro ──► SpeechRecognition ──► Google STT / Whisper ──► "lucifer mở chrome tìm thời tiết"
                                                               │
                                              WakeWordDetector (có "lucifer"? -> lấy phần lệnh)
                                                               │
                                       Brain: Claude (tool use)  ── lỗi mạng ──►  RuleBrain (regex)
                                                               │
                                     ToolRegistry: danh sách tool được phép + hỏi xác nhận
                                                               │
                         open_app / web_search / set_volume / power / ...  ──►  Windows
                                                               │
 Loa ◄── pygame ◄── Edge TTS (giọng Việt neural) / pyttsx3 ◄── "Đã tìm thời tiết, thưa sếp."
```

| File | Vai trò |
|---|---|
| `lucifer/__main__.py` | Điểm khởi chạy, đọc tham số dòng lệnh |
| `lucifer/assistant.py` | Vòng lặp chính: nghe, đánh thức, xử lý, trả lời, hỏi xác nhận |
| `lucifer/wakeword.py` | Phát hiện "Lucifer"/"Ê PC" trong câu, chịu được STT nghe nhầm ("lu xi phơ") |
| `lucifer/brain.py` | `ClaudeBrain` (AI + tool use), `RuleBrain` (offline), `HybridBrain` (tự chuyển khi lỗi) |
| `lucifer/voice.py` | Nghe (Google/Whisper) và nói (Edge TTS/pyttsx3) |
| `lucifer/tools/` | Các thao tác máy tính: `apps.py`, `web.py`, `system.py`, `files.py` |
| `lucifer/config.py` | Đọc cấu hình từ `.env` |

## An toàn

Cho AI điều khiển máy thì phải có giới hạn:

- **Chỉ dùng tool trong danh sách trắng.** AI không chạy được lệnh shell tuỳ ý, chỉ chọn một tool đã viết sẵn. Tham số của tool được kiểm tra chặt (`strict` schema), và tên chương trình chứa ký tự đặc biệt (`& | > ^`...) bị chặn.
- **Hỏi xác nhận bằng giọng nói** trước khi tắt máy, khởi động lại, cho máy ngủ, đóng ứng dụng, hoặc mở file thực thi (`.exe`, `.bat`, `.ps1`...).
- Tắt máy có độ trễ 30 giây; nói *"huỷ tắt máy"* để dừng.
- Không đóng các tiến trình hệ thống (explorer, svchost, winlogon...).
- Nội dung trả về từ web hay tên file chỉ được coi là dữ liệu, không phải mệnh lệnh (chống prompt injection).
- Mọi thao tác được ghi lại trong `lucifer.log`.

## Thêm lệnh mới

Ví dụ thêm lệnh mở Spotify và phát playlist: viết hàm trong `lucifer/tools/` rồi đăng ký nó.

```python
# lucifer/tools/web.py
def open_spotify(name: str) -> str:
    plat.open_url("https://open.spotify.com/search/" + urllib.parse.quote(name))
    return f"Đã mở Spotify tìm '{name}'."

# ...trong hàm register(registry):
registry.register(Tool(
    name="open_spotify",
    description="Tìm và mở bài hát/playlist trên Spotify, ví dụ 'nhạc chill'.",
    parameters={"name": {"type": "string", "description": "Tên bài hát hoặc playlist"}},
    func=open_spotify,
))
```

Claude tự hiểu khi nào cần dùng tool mới nhờ phần `description`. Với chế độ offline, bạn thêm mẫu câu tương ứng trong `RuleBrain.parse()`.

## Chi phí và độ trễ

- Google STT và Edge TTS miễn phí, nhưng cần Internet.
- Claude tính phí theo token. Mỗi lệnh thường chỉ vài nghìn token, vì lịch sử hội thoại ngắn và phần system prompt + tool đã được cache. Model mặc định là `claude-opus-5-5` với effort `low` để phản hồi nhanh. Muốn rẻ và nhanh hơn nữa thì đổi `LUCIFER_MODEL` sang `claude-sonnet-5-5` hoặc `claude-haiku-5-5`.
- Lucifer bật tính năng *fallback* phía máy chủ: nếu model chính từ chối một yêu cầu, API tự chuyển sang model dự phòng phù hợp.

## Xử lý sự cố

| Vấn đề | Cách xử lý |
|---|---|
| `pip install PyAudio` lỗi | Dùng Python bản 64-bit mới (3.10 trở lên) để có sẵn wheel, hoặc `pip install pipwin && pipwin install pyaudio` |
| Không nghe thấy gì | Kiểm tra micro mặc định trong *Settings > System > Sound > Input*. Chạy `--debug` để xem log |
| Hay nhận nhầm từ đánh thức | Thêm biến thể vào `LUCIFER_WAKE_WORDS`, ví dụ `lucifer,lu xi phơ,lu xi phe` |
| Không có tiếng | Edge TTS cần mạng. Khi offline, Lucifer dùng pyttsx3; cài giọng tiếng Việt trong *Settings > Time & Language > Speech* |
| "Không tìm thấy ứng dụng" | Nói đúng tên như trong Start Menu, hoặc thêm vào `KNOWN_APPS` trong `lucifer/tools/apps.py` |
| Muốn hoàn toàn offline | `LUCIFER_BRAIN=rules`, `LUCIFER_STT=whisper`, `LUCIFER_TTS=pyttsx3` |

## Phát triển

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Test không cần micro, không gọi API thật, và chạy được cả trên Linux/macOS.

## Hướng phát triển tiếp

- [ ] Giao diện HUD kiểu Iron Man (C# WPF hoặc PyQt) giao tiếp với lõi Python qua WebSocket
- [ ] Wake word offline chuyên dụng (openWakeWord/Porcupine) để đỡ tốn mạng khi nghe liên tục
- [ ] Đọc / gửi email, xem lịch, nhắc việc
- [ ] "Computer use": AI nhìn màn hình và tự click, gõ phím
- [ ] Bộ nhớ dài hạn (nhớ sở thích, thói quen của người dùng)
