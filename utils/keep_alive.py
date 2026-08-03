"""
Web server tối giản để giữ bot "thức" trên các nền tảng cloud
yêu cầu tiến trình phải lắng nghe một cổng HTTP (vd: Render Web Service
miễn phí, Replit). Không cần thiết trên Railway (worker chạy nền vẫn
được coi là "sống" mà không cần mở cổng), nhưng chạy thêm cũng không
gây hại gì.

Cách dùng: gọi keep_alive() một lần trước khi bot.run(...).
Sau đó có thể trỏ UptimeRobot (hoặc dịch vụ ping tương tự) vào
URL public của service, ping mỗi 5 phút để tránh bị "ngủ".
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class _PingHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Astrix đang hoạt động! 🚀".encode("utf-8"))

    def log_message(self, format, *args):
        # Tắt log mặc định của http.server để không làm rối log bot
        pass


def _run_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), _PingHandler)
    server.serve_forever()


def keep_alive():
    """Chạy web server ping ở một thread nền, không chặn bot chính."""

    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()
