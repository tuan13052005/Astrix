"""
Quản lý trạng thái phát nhạc cho từng server (guild):
- Hàng đợi bài hát (queue)
- Voice client hiện tại
- Bài đang phát
- Bảng điều khiển (panel) hiển thị trạng thái + nút bấm
- Trích xuất thông tin/luồng audio qua yt-dlp (chạy trong executor
  để không chặn event loop chính của bot)
- Hỗ trợ phát nguyên playlist khi paste link playlist YouTube
"""

import asyncio
import logging
import os
import random

import discord

from views.music_view import build_panel_embed, MusicControlView

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

log = logging.getLogger("astrix.music")


# =========================================================
# CẤU HÌNH YT-DLP / FFMPEG
# =========================================================

# YouTube hay chặn IP của các nhà cung cấp cloud (Render, Fly.io, VPS...)
# và yêu cầu xác thực bằng cookies trình duyệt thật. Bot sẽ tự dò file
# cookies.txt ở 2 nơi, theo thứ tự ưu tiên:
#   1. /etc/secrets/cookies.txt — nơi Render mount "Secret File" khi
#      chạy service dạng Docker (xem Render Dashboard -> Environment
#      -> Secret Files).
#   2. data/cookies.txt — khi chạy local hoặc VPS tự quản lý, đặt file
#      trực tiếp vào đây.
_COOKIES_CANDIDATES = [
    "/etc/secrets/cookies.txt",
    os.path.join("data", "cookies.txt"),
]

COOKIES_FILE = next(
    (path for path in _COOKIES_CANDIDATES if os.path.exists(path)),
    None
)

# Giới hạn tối đa số bài lấy từ 1 playlist, tránh treo lâu hoặc
# nhồi hàng đợi quá tải nếu ai đó paste playlist vài nghìn bài.
MAX_PLAYLIST_ITEMS = 50

YDL_OPTIONS = {
    "format": "bestaudio/best",
    # False = cho phép lấy nguyên playlist nếu query là link playlist.
    # Nếu query là link 1 video hoặc là từ khóa tìm kiếm thì vẫn
    # chỉ trả về 1 kết quả như bình thường.
    "noplaylist": False,
    "playlistend": MAX_PLAYLIST_ITEMS,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

if COOKIES_FILE:
    YDL_OPTIONS["cookiefile"] = COOKIES_FILE

    # Log chi tiết để debug mà không cần vào Render Shell: kiểm tra
    # xem file có thực sự có nội dung hợp lệ hay bị rỗng/lỗi.
    try:
        with open(COOKIES_FILE, "r", encoding="utf-8", errors="replace") as f:
            _lines = f.readlines()

        _non_comment_lines = [
            line for line in _lines
            if line.strip() and not line.strip().startswith("#")
        ]

        log.info(
            f"🍪 Đang dùng cookies YouTube từ: {COOKIES_FILE} "
            f"({len(_lines)} dòng tổng, {len(_non_comment_lines)} dòng cookie thật)"
        )

        if _lines:
            log.info(f"🍪 Dòng đầu tiên: {_lines[0].strip()!r}")

        if not _non_comment_lines:
            log.warning(
                "⚠️ cookies.txt tồn tại nhưng KHÔNG có dòng cookie nào hợp lệ "
                "(file rỗng hoặc chỉ có comment) — cần export lại và dán đúng "
                "nội dung vào Secret File."
            )
    except Exception as e:
        log.error(f"❌ Không đọc được cookies.txt dù file tồn tại: {e}")
else:
    log.warning(
        "⚠️ Không tìm thấy cookies.txt (đã kiểm tra: "
        f"{', '.join(_COOKIES_CANDIDATES)}). Nếu YouTube báo "
        "'Sign in to confirm you're not a bot', hãy thêm Secret File "
        "cookies.txt trên Render (hoặc data/cookies.txt khi chạy local/VPS)."
    )

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": "-vn"
}


class Track:
    """Một bài hát trong hàng đợi."""

    def __init__(self, data: dict, requester: discord.Member):
        self.title = data.get("title", "Không rõ tên")
        self.webpage_url = data.get("webpage_url", "")
        self.stream_url = data.get("url")
        self.duration = data.get("duration") or 0
        self.thumbnail = data.get("thumbnail")
        self.requester = requester

    @property
    def duration_text(self) -> str:
        if not self.duration:
            return "??:??"
        minutes, seconds = divmod(int(self.duration), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"


class GuildMusicState:
    """Trạng thái nhạc riêng của một server."""

    def __init__(self, bot: discord.Client, guild_id: int, manager: "MusicManager"):
        self.bot = bot
        self.guild_id = guild_id
        self.manager = manager

        self.queue: list[Track] = []
        self.voice_client: discord.VoiceClient | None = None
        self.current: Track | None = None
        self.text_channel: discord.abc.Messageable | None = None

        # Tin nhắn bảng điều khiển hiện tại — được edit lại mỗi khi
        # trạng thái thay đổi thay vì spam tin nhắn mới.
        self.panel_message: discord.Message | None = None

        self.volume: float = 1.0
        self._skip_requested = False

        # "off" | "track" (lặp bài hiện tại) | "queue" (lặp toàn bộ hàng đợi)
        self.loop_mode: str = "off"

    # -----------------------------------------------------
    # THÊM BÀI HÁT / PLAYLIST VÀO HÀNG ĐỢI (QUA YT-DLP)
    # -----------------------------------------------------

    async def add_tracks(self, query: str, requester: discord.Member) -> list[Track]:
        """
        Trả về danh sách Track vừa thêm vào hàng đợi:
        - Query là 1 video / từ khóa tìm kiếm -> list có 1 phần tử.
        - Query là link playlist -> list có nhiều phần tử
          (tối đa MAX_PLAYLIST_ITEMS bài).
        """

        if yt_dlp is None:
            raise RuntimeError(
                "Thư viện `yt-dlp` chưa được cài đặt. "
                "Chạy: pip install yt-dlp"
            )

        loop = asyncio.get_running_loop()

        def _extract():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                return ydl.extract_info(query, download=False)

        data = await loop.run_in_executor(None, _extract)

        if "entries" in data:
            # Playlist HOẶC kết quả tìm kiếm (yt-dlp cũng bọc trong "entries")
            raw_entries = data["entries"]
        else:
            raw_entries = [data]

        # Bỏ qua entry None (video trong playlist đã bị xóa/riêng tư)
        tracks = [Track(entry, requester) for entry in raw_entries if entry]

        if not tracks:
            raise RuntimeError("Không tìm thấy video khả dụng nào.")

        self.queue.extend(tracks)

        return tracks

    # -----------------------------------------------------
    # PHÁT BÀI TIẾP THEO TRONG HÀNG ĐỢI
    # -----------------------------------------------------

    async def play_next(self):

        if self.voice_client is None or not self.voice_client.is_connected():
            return

        # -------- CHẾ ĐỘ LẶP LẠI BÀI HIỆN TẠI --------
        if self.loop_mode == "track" and self.current is not None:
            track = self.current

        else:
            # -------- CHẾ ĐỘ LẶP TOÀN BỘ HÀNG ĐỢI --------
            if self.loop_mode == "queue" and self.current is not None:
                self.queue.append(self.current)

            if not self.queue:
                self.current = None
                await self._update_panel()
                return

            track = self.queue.pop(0)

        self.current = track

        source = discord.FFmpegPCMAudio(
            track.stream_url,
            **FFMPEG_OPTIONS
        )
        source = discord.PCMVolumeTransformer(source, volume=self.volume)

        def _after_playback(error: Exception | None):
            if error:
                log.exception(f"Lỗi khi phát nhạc: {error}")

            fut = asyncio.run_coroutine_threadsafe(
                self.play_next(), self.bot.loop
            )
            try:
                fut.result()
            except Exception:
                log.exception("Lỗi khi chuyển sang bài tiếp theo")

        self.voice_client.play(source, after=_after_playback)

        await self._update_panel()

    # -----------------------------------------------------
    # CẬP NHẬT BẢNG ĐIỀU KHIỂN (EMBED + NÚT BẤM)
    # -----------------------------------------------------

    async def _update_panel(self):

        if self.text_channel is None:
            return

        embed = build_panel_embed(self.bot, self)
        view = MusicControlView(self.manager)

        if self.panel_message is not None:
            try:
                await self.panel_message.edit(embed=embed, view=view)
                return
            except discord.HTTPException:
                self.panel_message = None

        try:
            self.panel_message = await self.text_channel.send(embed=embed, view=view)
        except discord.HTTPException:
            pass

    def skip(self):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()  # sẽ tự trigger play_next() qua after=

    def shuffle(self):
        random.shuffle(self.queue)

    def clear(self):
        self.queue.clear()
        self.current = None


class MusicManager:
    """Registry giữ GuildMusicState cho mỗi server (dict theo guild_id)."""

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self._states: dict[int, GuildMusicState] = {}

    def get_state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self._states:
            self._states[guild_id] = GuildMusicState(self.bot, guild_id, self)
        return self._states[guild_id]

    def remove_state(self, guild_id: int) -> None:
        self._states.pop(guild_id, None)