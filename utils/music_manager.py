"""
Quản lý trạng thái phát nhạc cho từng server (guild):
- Hàng đợi bài hát (queue)
- Voice client hiện tại
- Bài đang phát
- Bảng điều khiển (panel) hiển thị trạng thái + nút bấm
- Trích xuất thông tin/luồng audio qua yt-dlp (chạy trong executor
  để không chặn event loop chính của bot)
"""

import asyncio
import logging
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

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

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
    # THÊM BÀI HÁT VÀO HÀNG ĐỢI (TÌM KIẾM QUA YT-DLP)
    # -----------------------------------------------------

    async def add_track(self, query: str, requester: discord.Member) -> Track:

        if yt_dlp is None:
            raise RuntimeError(
                "Thư viện `yt-dlp` chưa được cài đặt. "
                "Chạy: pip install yt-dlp"
            )

        loop = asyncio.get_running_loop()

        def _extract():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(query, download=False)

                if "entries" in info:
                    # Kết quả tìm kiếm (ytsearch) -> lấy bản đầu tiên
                    info = info["entries"][0]

                return info

        data = await loop.run_in_executor(None, _extract)

        track = Track(data, requester)
        self.queue.append(track)

        return track

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

        # Ưu tiên edit tin nhắn panel cũ để tránh spam kênh chat
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