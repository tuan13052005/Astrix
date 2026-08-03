# Astrix V2

Bot Discord đa chức năng viết bằng `discord.py`.

## Cấu trúc dự án

- `commands/` — Các cog chứa slash command (general, user, server, moderation,
  system, welcome, automod, poll, giveaway, reminder)
- `views/` — Các UI View tương tác (button, modal...)
- `utils/` — Tiện ích dùng chung: logging, kiểm tra quyền, lưu trữ dữ liệu,
  keep-alive server
- `data/` — Dữ liệu bền vững (guild settings, warnings, reminders, giveaways,
  file log `bot.log`) — tự tạo khi bot chạy, **không commit lên Git**

## Danh sách tính năng

**Quản trị:** `/clear` `/kick` `/ban` `/mute` `/unmute` `/warn` `/warnings`
`/delwarn` `/clearwarnings` `/setlog` `/viewlog`

**Welcome / Auto-role:** `/setwelcome` `/disablewelcome` `/setgoodbye`
`/disablegoodbye` `/setautorole` `/disableautorole`

**Auto-Moderation:** `/automod enable|disable|blocklinks|addword|removeword|status`
— tự động xóa tin nhắn chứa từ cấm hoặc link/invite Discord, có log lại

**Poll / Giveaway:** `/poll` (bình chọn bằng nút bấm) và `/giveaway`
(giveaway có lưu trạng thái bền vững, tự quay số kể cả khi bot restart)

**Nhắc nhở:** `/remind` `/reminders` `/delremind` — nhắc nhở được lưu vào
file, không mất khi bot khởi động lại

## Chạy bot (local)

```bash
pip install -r requirements.txt
cp .env.example .env
# rồi mở .env điền DISCORD_TOKEN thật vào
python bot.py
```

Xem chi tiết các biến môi trường trong `.env.example`.

## Triển khai chạy 24/7 trên nền tảng cloud

Dự án đã có sẵn `Procfile`, `requirements.txt`, `runtime.txt` và một
web server keep-alive nhỏ (`utils/keep_alive.py`) để tương thích với
Railway, Render và Replit.

### Railway
1. Tạo project mới → **Deploy from GitHub repo** (push project này lên
   GitHub trước, hoặc dùng Railway CLI).
2. Vào tab **Variables** → thêm `DISCORD_TOKEN` (không cần thêm `PORT`,
   Railway tự cấp).
3. Railway tự nhận `Procfile` và chạy `python bot.py`. Worker chạy nền
   liên tục, không bị "ngủ" — không cần dịch vụ ping thêm.

### Render
1. **New** → **Web Service** → kết nối repo GitHub chứa project này.
2. Build Command: `pip install -r requirements.txt`
   Start Command: `python bot.py`
3. Vào **Environment** → thêm biến `DISCORD_TOKEN`.
4. Gói **Free** của Render sẽ tự "ngủ" sau ~15 phút không có traffic HTTP.
   Web server keep-alive đã tích hợp sẵn sẽ trả về HTTP 200 tại URL public
   của service — thêm URL đó vào [UptimeRobot](https://uptimerobot.com)
   (hoặc dịch vụ tương tự), ping mỗi 5 phút để giữ bot luôn thức.
   *(Nếu nâng cấp lên gói trả phí / Background Worker thì không cần bước này.)*

### Replit
1. Import project từ GitHub (hoặc kéo-thả toàn bộ thư mục).
2. Vào tab **Secrets** → thêm `DISCORD_TOKEN`.
3. Nhấn **Run** — Replit sẽ tự cài `requirements.txt` và chạy `bot.py`.
4. Copy URL Replit cung cấp (từ web server keep-alive) và thêm vào
   UptimeRobot để giữ Repl không bị ngủ trên gói miễn phí.

### Lưu ý chung khi chạy 24/7
- File dữ liệu trong `data/` (warnings, reminders, giveaways...) nằm trên
  ổ đĩa tạm của most nền tảng free — **có thể bị xóa khi redeploy**. Nếu
  cần giữ dữ liệu lâu dài, gắn thêm Volume/Persistent Disk (Railway/Render
  đều hỗ trợ) và trỏ thư mục `data/` vào đó.
- Bot đã có: tự log lỗi ra `data/bot.log` (xoay vòng 5MB/file, giữ 3 bản),
  tự bắt lỗi trong các vòng lặp nền (giveaway/reminder) để không bị dừng
  ngầm, và discord.py tự động reconnect khi rớt mạng.
- Không commit file `.env` lên Git (đã có trong `.gitignore`) — luôn set
  token qua biến môi trường (Variables/Secrets) của nền tảng hosting.

## Điểm mới trong bản cập nhật gần đây

- **`utils/checks.py`**: decorator dùng chung `@checks.guild_only()`,
  `@checks.has_permissions(...)` thay cho việc lặp code kiểm tra quyền.
- **`utils/data_manager.py`**: mở rộng lưu trữ JSON cho welcome/goodbye,
  auto-role, auto-mod, reminders, giveaways — ngoài warnings có sẵn.
- **`commands/welcome.py`**, **`commands/automod.py`**,
  **`commands/poll.py`**, **`commands/giveaway.py`**,
  **`commands/reminder.py`**: 5 cog mới.
- **`bot.py`**: logging ra file xoay vòng, bắt lỗi sự kiện tập trung
  (`on_error`), theo dõi reconnect (`on_disconnect`/`on_resumed`), khởi
  động web server keep-alive trước khi chạy bot.
- **`Procfile` / `requirements.txt` / `runtime.txt` / `.env.example`**:
  sẵn sàng deploy lên Railway/Render/Replit.
