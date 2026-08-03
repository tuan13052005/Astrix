"""
Quản lý trạng thái phát nhạc cho từng server (guild):
- Hàng đợi bài hát (queue)
- Voice client hiện tại
- Bài đang phát
- Bảng điều khiển (panel) hiển thị trạng thái + nút bấm
- Trích xuất thông tin/luồng audio qua yt-dlp (chạy trong executor
  để không chặn event loop chính của bot)
- Hỗ trợ phát nguyên playlist khi paste link playlist YouTube
- Fallback tự động sang SoundCloud khi YouTube chặn bot-check
  ("Sign in to confirm you're not a bot")
- Hỗ trợ link Spotify (track/album/playlist): chỉ dùng Spotify Web API
  để đọc tên bài + nghệ sĩ (Spotify DRM-khóa audio, không tải được
  trực tiếp), rồi tìm audio thật trên YouTube/SoundCloud
"""

import asyncio
import base64
import logging
import os
import random
import re
import time

import aiohttp
import discord

from views.music_view import build_panel_embed, MusicControlView

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

log = logging.getLogger("astrix.music")

if yt_dlp is not None:
    log.info(f"📦 yt-dlp version đang chạy: {yt_dlp.version.__version__}")
else:
    log.error("❌ yt-dlp chưa được cài đặt!")


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

_SOURCE_COOKIES_FILE = next(
    (path for path in _COOKIES_CANDIDATES if os.path.exists(path)),
    None
)

# yt-dlp không chỉ ĐỌC cookiefile — nó còn GHI LẠI file này sau khi
# dùng (để lưu cookie mới được refresh trong lúc request). Nếu file
# nằm ở /etc/secrets (Render Secret File) thì filesystem đó READ-ONLY,
# nên phải copy sang data/ (writable) rồi trỏ yt-dlp vào bản copy đó,
# chứ không dùng thẳng file gốc.
COOKIES_FILE = None

if _SOURCE_COOKIES_FILE is not None:
    os.makedirs("data", exist_ok=True)
    _writable_path = os.path.join("data", "cookies.txt")

    try:
        if os.path.abspath(_SOURCE_COOKIES_FILE) != os.path.abspath(_writable_path):
            import shutil
            shutil.copyfile(_SOURCE_COOKIES_FILE, _writable_path)

        COOKIES_FILE = _writable_path
    except OSError as e:
        log.error(f"❌ Không copy được cookies.txt sang thư mục ghi được: {e}")
        COOKIES_FILE = None

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
    # Client Android thường ít bị soi bot-check hơn client Web.
    "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
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

log.info(f"🍪 COOKIES_FILE cuối cùng đang dùng: {COOKIES_FILE}")

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": "-vn"
}


# =========================================================
# SOUNDCLOUD — NGUỒN DỰ PHÒNG KHI YOUTUBE CHẶN BOT-CHECK
# =========================================================
# SoundCloud hiện ít bị chặn hơn nhiều so với YouTube. Dùng làm
# fallback tự động khi YouTube báo lỗi "Sign in to confirm you're
# not a bot", chỉ áp dụng cho TỪ KHÓA tìm kiếm (không áp dụng cho
# link YouTube cụ thể, vì không thể tự ý thay bằng bài không liên quan).

SOUNDCLOUD_YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "playlistend": MAX_PLAYLIST_ITEMS,
    "quiet": True,
    "no_warnings": True,
    "default_search": "scsearch",
    "source_address": "0.0.0.0",
}


# =========================================================
# SPOTIFY — CHỈ DÙNG ĐỂ ĐỌC TÊN BÀI HÁT, KHÔNG TẢI AUDIO
# =========================================================
# Spotify DRM-khóa toàn bộ stream nhạc, yt-dlp không thể lấy audio
# thật từ đây. Ta chỉ gọi Spotify Web API để lấy "tên bài - nghệ sĩ",
# rồi đưa chuỗi đó vào pipeline YouTube/SoundCloud có sẵn để tìm
# audio thật.

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

SPOTIFY_LINK_PATTERN = re.compile(
    r"open\.spotify\.com/(track|album|playlist)/([A-Za-z0-9]+)"
)

_spotify_token: str | None = None
_spotify_token_expires_at: float = 0.0


async def _get_spotify_token() -> str | None:
    """Lấy access token Spotify (Client Credentials flow), tự cache lại
    tới khi hết hạn để không gọi API xin token liên tục."""

    global _spotify_token, _spotify_token_expires_at

    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None

    if _spotify_token and time.time() < _spotify_token_expires_at:
        return _spotify_token

    auth = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {auth}"},
            data={"grant_type": "client_credentials"},
        ) as resp:
            if resp.status != 200:
                log.error(f"❌ Không lấy được Spotify token: HTTP {resp.status}")
                return None
            payload = await resp.json()

    _spotify_token = payload["access_token"]
    _spotify_token_expires_at = time.time() + payload.get("expires_in", 3600) - 60

    return _spotify_token


async def _resolve_spotify_queries(url: str) -> list[str]:
    """Trả về danh sách chuỗi 'Tên bài hát Nghệ sĩ' để tìm trên
    YouTube/SoundCloud, đọc từ 1 track / album / playlist Spotify."""

    match = SPOTIFY_LINK_PATTERN.search(url)
    if not match:
        return []

    kind, spotify_id = match.groups()
    token = await _get_spotify_token()

    if token is None:
        raise RuntimeError(
            "Chưa cấu hình SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET trên "
            "server, nên không đọc được link Spotify."
        )

    headers = {"Authorization": f"Bearer {token}"}

    async with aiohttp.ClientSession() as session:

        if kind == "track":
            async with session.get(
                f"https://api.spotify.com/v1/tracks/{spotify_id}",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Spotify API lỗi HTTP {resp.status}")
                data = await resp.json()

            artists = ", ".join(a["name"] for a in data.get("artists", []))
            return [f"{data['name']} {artists}"]

        # album hoặc playlist -> lấy danh sách bài
        items_url = (
            f"https://api.spotify.com/v1/albums/{spotify_id}/tracks"
            if kind == "album"
            else f"https://api.spotify.com/v1/playlists/{spotify_id}/tracks"
        )

        queries: list[str] = []
        next_url = items_url

        while next_url and len(queries) < MAX_PLAYLIST_ITEMS:
            async with session.get(next_url, headers=headers) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Spotify API lỗi HTTP {resp.status}")
                page = await resp.json()

            for item in page.get("items", []):
                track = item.get("track") if kind == "playlist" else item

                if not track:
                    continue

                artists = ", ".join(a["name"] for a in track.get("artists", []))
                queries.append(f"{track['name']} {artists}")

            next_url = page.get("next")

        return queries[:MAX_PLAYLIST_ITEMS]


class Track:
    """Một bài hát trong hàng đợi."""

    def __init__(self, data: dict, requester: discord.Member, source: str = "YouTube"):
        self.title = data.get("title", "Không rõ tên")
        self.webpage_url = data.get("webpage_url", "")
        self.stream_url = data.get("url")
        self.duration = data.get("duration") or 0
        self.thumbnail = data.get("thumbnail")
        self.requester = requester
        self.source = source

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
    # THÊM BÀI HÁT / PLAYLIST VÀO HÀNG ĐỢI
    # -----------------------------------------------------

    async def add_tracks(self, query: str, requester: discord.Member) -> list[Track]:
        """
        Trả về danh sách Track vừa thêm vào hàng đợi:
        - Link Spotify (track/album/playlist) -> đọc tên bài qua Spotify
          API, rồi tìm audio thật cho từng bài trên YouTube (fallback
          SoundCloud nếu YouTube chặn).
        - Link YouTube / từ khóa tìm kiếm -> tìm trực tiếp trên YouTube,
          tự động fallback sang SoundCloud nếu YouTube chặn bot-check
          ("Sign in to confirm you're not a bot") VÀ query là từ khóa
          tìm kiếm (không áp dụng fallback cho link YouTube cụ thể).
        """

        if yt_dlp is None:
            raise RuntimeError(
                "Thư viện `yt-dlp` chưa được cài đặt. "
                "Chạy: pip install yt-dlp"
            )

        if SPOTIFY_LINK_PATTERN.search(query):
            return await self._add_from_spotify(query, requester)

        return await self._fetch_single(query, requester)

    async def _add_from_spotify(self, url: str, requester: discord.Member) -> list["Track"]:
        """Đọc danh sách bài từ link Spotify rồi tìm audio thật cho
        từng bài. Bỏ qua (không raise) những bài không tìm được audio,
        miễn là ít nhất 1 bài thành công."""

        queries = await _resolve_spotify_queries(url)

        if not queries:
            raise RuntimeError(
                "Không đọc được thông tin bài hát từ link Spotify này."
            )

        all_tracks: list[Track] = []

        for search_text in queries:
            try:
                tracks = await self._fetch_single(search_text, requester)
                all_tracks.extend(tracks)
            except Exception as error:
                log.warning(f"⚠️ Bỏ qua bài '{search_text}' từ Spotify: {error}")
                continue

        if not all_tracks:
            raise RuntimeError(
                "Không tìm được bản audio nào khớp với các bài trong "
                "link Spotify này."
            )

        return all_tracks

    async def _fetch_single(self, query: str, requester: discord.Member) -> list["Track"]:
        """Tìm 1 query (link YouTube hoặc từ khóa) trên YouTube trước,
        tự động fallback sang SoundCloud nếu YouTube chặn bot-check."""

        loop = asyncio.get_running_loop()

        def _extract(options: dict, q: str):
            with yt_dlp.YoutubeDL(options) as ydl:
                return ydl.extract_info(q, download=False)

        is_direct_link = query.strip().lower().startswith(("http://", "https://"))
        source_label = "YouTube"

        try:
            data = await loop.run_in_executor(None, _extract, YDL_OPTIONS, query)

        except yt_dlp.utils.DownloadError as error:
            error_text = str(error).lower()
            is_bot_block = (
                "sign in to confirm" in error_text
                or "not a bot" in error_text
            )

            if not is_bot_block:
                raise RuntimeError(f"Không thể tải từ YouTube: {error}") from error

            if is_direct_link:
                # Link YouTube cụ thể -> không thể thay thế bằng kết quả
                # SoundCloud không liên quan, nên báo lỗi rõ ràng thay vì
                # tự ý phát nhầm bài khác.
                raise RuntimeError(
                    "YouTube đang chặn bot-check cho link này. "
                    "Thử lại bằng cách gõ TÊN bài hát thay vì dán link, "
                    "để mình tự tìm trên SoundCloud."
                ) from error

            log.warning(
                f"⚠️ YouTube chặn bot-check cho '{query}', "
                f"đang thử lại trên SoundCloud..."
            )
            source_label = "SoundCloud"

            try:
                data = await loop.run_in_executor(
                    None, _extract, SOUNDCLOUD_YDL_OPTIONS, query
                )
            except yt_dlp.utils.DownloadError as sc_error:
                raise RuntimeError(
                    "YouTube bị chặn (bot-check) và SoundCloud cũng "
                    f"không tìm được bài phù hợp: {sc_error}"
                ) from sc_error

        if "entries" in data:
            # Playlist HOẶC kết quả tìm kiếm (yt-dlp cũng bọc trong "entries")
            raw_entries = data["entries"]
        else:
            raw_entries = [data]

        # Bỏ qua entry None (video trong playlist đã bị xóa/riêng tư)
        tracks = [
            Track(entry, requester, source=source_label)
            for entry in raw_entries if entry
        ]

        if not tracks:
            raise RuntimeError("Không tìm thấy bài hát khả dụng nào.")

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