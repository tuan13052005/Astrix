# Astrix V2

Bot Discord đa chức năng viết bằng `discord.py`.

## Cấu trúc dự án

- `commands/` — Các cog chứa slash command (general, user, server, moderation, system)
- `views/` — Các UI View tương tác (button, modal...)
- `utils/` — Tiện ích dùng chung: logging, kiểm tra quyền, lưu trữ dữ liệu
- `data/` — Dữ liệu bền vững (guild settings, warnings) — tự tạo khi bot chạy

## Điểm mới trong bản cập nhật này

- **`utils/checks.py`**: gộp các đoạn kiểm tra "chỉ dùng trong server" và
  "kiểm tra quyền" thành decorator dùng chung (`@checks.guild_only()`,
  `@checks.has_permissions(...)`), giảm lặp code và đồng bộ thông báo lỗi.
- **`utils/data_manager.py`**: lưu trữ JSON đơn giản cho cấu hình theo từng
  server (kênh log) và hệ thống cảnh cáo (warnings) có thể tra cứu/xóa.
- **`commands/system.py`**: thêm `/setlog` và `/viewlog` để chủ server tự
  chọn kênh nhận log thay vì bị cố định tên `#astrix-logs`.
- **Log hành động kiểm duyệt**: `clear`, `kick`, `ban`, `mute`, `unmute`,
  `warn` và các thao tác liên quan đều tự động gửi log nếu đã cấu hình kênh.
- **Hệ thống cảnh cáo đầy đủ**: `/warn` giờ lưu lại cảnh cáo, thêm
  `/warnings`, `/delwarn`, `/clearwarnings` để quản lý.
- **`bot.py`**: nạp cấu hình vào `bot.config`, thêm bộ xử lý lỗi tập trung
  cho slash command (`@bot.tree.error`).

## Chạy bot

```bash
pip install -r requirements.txt
python bot.py
```

Tạo file `.env` với nội dung:

```
DISCORD_TOKEN=your_token_here
```
