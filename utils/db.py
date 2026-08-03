"""
Client Supabase dùng chung cho toàn bộ bot.

Thay cho việc đọc/ghi file JSON trong data/ (mất khi redeploy trên
Fly.io/Render/Railway ephemeral filesystem), mọi dữ liệu bền vững giờ
được lưu trong Postgres của Supabase.

Biến môi trường cần có trong .env (hoặc Fly secrets / VPS env):
    SUPABASE_URL          — URL project, dạng https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY  — Service Role key (Settings -> API), KHÔNG
                             dùng anon key vì cần bỏ qua Row Level
                             Security để bot ghi/đọc mọi bảng.

Client được khởi tạo "lazy" (chỉ tạo khi lần đầu được gọi), để đảm bảo
load_dotenv() trong bot.py đã chạy xong và nạp biến môi trường trước
khi utils/data_manager.py cần dùng đến kết nối.
"""

import os

from supabase import create_client, Client


_client: Client | None = None


def get_client() -> Client:
    """Trả về Supabase client (singleton), tự khởi tạo lần gọi đầu tiên."""

    global _client

    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError(
            "❌ Thiếu SUPABASE_URL hoặc SUPABASE_SERVICE_KEY trong .env. "
            "Xem hướng dẫn trong .env.example / DEPLOY_FLY_SUPABASE.md"
        )

    _client = create_client(url, key)
    return _client