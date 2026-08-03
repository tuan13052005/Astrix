"""
Bảng điều khiển nhạc dạng nút bấm (control panel).

Quyền bấm nút được kiểm tra dựa theo vai trò của người bấm
(xem utils.checks.is_dj):
- Nút 📋 Hàng đợi: ai cũng bấm được.
- Các nút còn lại (⏯️ ⏭️ ⏹️ 🔀 🔉 🔊 🔁): cần role DJ đã cấu hình
  qua /setdjrole, hoặc quyền admin. Nếu server chưa cấu hình DJ
  role thì mở cho tất cả, giống các lệnh nhạc hiện có.

View dùng timeout=None + custom_id cố định nên vẫn hoạt động
sau khi bot restart, miễn là được đăng ký lại qua bot.add_view()
(đã làm trong commands/music.py -> Music.__init__).

LƯU Ý QUAN TRỌNG: hàm cập nhật embed bảng điều khiển được đặt tên
`_refresh_panel` (KHÔNG phải `_refresh`). `discord.ui.View` (class
gốc của discord.py) đã có sẵn một phương thức nội bộ tên `_refresh`
dùng để đồng bộ trạng thái component sau khi edit — nếu đặt trùng
tên, discord.py sẽ gọi nhầm vào hàm của mình với chữ ký khác, gây
lỗi `TypeError: _refresh() missing 1 required positional argument`.
Vì vậy KHÔNG được đổi tên `_refresh_panel` lại thành `_refresh`.
"""

import discord

from utils import checks
from utils.embeds import branded_embed


# =========================================================
# DỰNG EMBED BẢNG ĐIỀU KHIỂN
# =========================================================

def build_panel_embed(bot, state) -> discord.Embed:
    """Dựng embed hiển thị trạng thái phát nhạc hiện tại của một server."""

    if state.current:
        track = state.current

        description = (
            f"**[{track.title}]({track.webpage_url})**"
            if track.webpage_url else f"**{track.title}**"
        )

        embed = branded_embed(
            bot,
            title="🎶 Đang phát",
            description=description,
            color=discord.Color.blurple()
        )

        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)

        is_paused = bool(state.voice_client and state.voice_client.is_paused())

        embed.add_field(name="⏱️ Thời lượng", value=f"`{track.duration_text}`", inline=True)
        embed.add_field(name="📝 Yêu cầu bởi", value=track.requester.mention, inline=True)
        embed.add_field(
            name="📶 Trạng thái",
            value="⏸️ Tạm dừng" if is_paused else "▶️ Đang phát",
            inline=True
        )

        embed.add_field(name="🔊 Âm lượng", value=f"`{round(state.volume * 100)}%`", inline=True)

        loop_labels = {
            "off": "❌ Tắt",
            "track": "🔂 Bài hiện tại",
            "queue": "🔁 Toàn bộ hàng đợi"
        }
        embed.add_field(name="🔁 Chế độ lặp", value=loop_labels[state.loop_mode], inline=True)
        embed.add_field(name="📋 Số bài chờ", value=f"`{len(state.queue)}`", inline=True)

        if state.queue:
            preview_lines = [
                f"`{index + 1}.` {t.title}"
                for index, t in enumerate(state.queue[:5])
            ]
            if len(state.queue) > 5:
                preview_lines.append(f"*(+{len(state.queue) - 5} bài khác)*")

            embed.add_field(
                name="⏭️ Tiếp theo",
                value="\n".join(preview_lines),
                inline=False
            )

    else:
        embed = branded_embed(
            bot,
            title="🎵 Bảng điều khiển nhạc",
            description=(
                "Hiện không có bài hát nào đang phát.\n"
                "Dùng `/play` để bắt đầu nghe nhạc."
            ),
            color=discord.Color.greyple()
        )

    embed.set_footer(text="🎧 Astrix Music Panel")

    return embed


# =========================================================
# VIEW — CÁC NÚT ĐIỀU KHIỂN
# =========================================================

class MusicControlView(discord.ui.View):

    def __init__(self, manager):
        super().__init__(timeout=None)
        self.manager = manager

    # -----------------------------------------------------
    # HÀM DÙNG CHUNG: LẤY STATE + KIỂM TRA QUYỀN
    # -----------------------------------------------------

    async def _get_state(
        self,
        interaction: discord.Interaction,
        require_dj: bool = True
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Chỉ dùng được trong server.", ephemeral=True
            )
            return None

        if require_dj and not checks.is_dj(interaction):
            await interaction.response.send_message(
                "❌ Bạn cần role DJ (hoặc quyền admin) để dùng nút này.",
                ephemeral=True
            )
            return None

        return self.manager.get_state(interaction.guild.id)

    async def _refresh_panel(self, interaction: discord.Interaction, state):
        embed = build_panel_embed(interaction.client, state)
        await interaction.response.edit_message(embed=embed, view=self)

    # =====================================================
    # HÀNG 1 — PHÁT / SKIP / DỪNG / XÁO TRỘN
    # =====================================================

    @discord.ui.button(
        emoji="⏯️", style=discord.ButtonStyle.primary,
        custom_id="music_panel:toggle", row=0
    )
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):

        state = await self._get_state(interaction)
        if state is None:
            return

        if state.voice_client is None:
            await interaction.response.send_message(
                "❌ Astrix hiện không phát nhạc.", ephemeral=True
            )
            return

        if state.voice_client.is_playing():
            state.voice_client.pause()
        elif state.voice_client.is_paused():
            state.voice_client.resume()
        else:
            await interaction.response.send_message(
                "❌ Không có bài nào đang phát.", ephemeral=True
            )
            return

        await self._refresh_panel(interaction, state)

    @discord.ui.button(
        emoji="⏭️", style=discord.ButtonStyle.secondary,
        custom_id="music_panel:skip", row=0
    )
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):

        state = await self._get_state(interaction)
        if state is None:
            return

        if state.voice_client is None or not (
            state.voice_client.is_playing() or state.voice_client.is_paused()
        ):
            await interaction.response.send_message(
                "❌ Không có bài nào đang phát.", ephemeral=True
            )
            return

        state.skip()
        await interaction.response.send_message("⏭️ Đã bỏ qua bài hát.", ephemeral=True)

    @discord.ui.button(
        emoji="⏹️", style=discord.ButtonStyle.danger,
        custom_id="music_panel:stop", row=0
    )
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):

        state = await self._get_state(interaction)
        if state is None:
            return

        if state.voice_client is None:
            await interaction.response.send_message(
                "❌ Astrix hiện không phát nhạc ở server này.", ephemeral=True
            )
            return

        state.clear()

        if state.voice_client.is_connected():
            await state.voice_client.disconnect()

        state.voice_client = None
        state.panel_message = None
        self.manager.remove_state(interaction.guild.id)

        for item in self.children:
            item.disabled = True

        embed = build_panel_embed(interaction.client, state)

        await interaction.response.edit_message(
            content="⏹️ Đã dừng nhạc, xóa hàng đợi và rời kênh thoại.",
            embed=embed,
            view=self
        )

        self.stop()

    @discord.ui.button(
        emoji="🔀", style=discord.ButtonStyle.secondary,
        custom_id="music_panel:shuffle", row=0
    )
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):

        state = await self._get_state(interaction)
        if state is None:
            return

        if len(state.queue) < 2:
            await interaction.response.send_message(
                "❌ Cần ít nhất 2 bài trong hàng đợi để xáo trộn.", ephemeral=True
            )
            return

        state.shuffle()
        await self._refresh_panel(interaction, state)

    # =====================================================
    # HÀNG 2 — ÂM LƯỢNG / LẶP / HÀNG ĐỢI
    # =====================================================

    @discord.ui.button(
        emoji="🔉", label="-10%", style=discord.ButtonStyle.secondary,
        custom_id="music_panel:vol_down", row=1
    )
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):

        state = await self._get_state(interaction)
        if state is None:
            return

        state.volume = max(0.0, round(state.volume - 0.1, 2))

        if state.voice_client and isinstance(
            state.voice_client.source, discord.PCMVolumeTransformer
        ):
            state.voice_client.source.volume = state.volume

        await self._refresh_panel(interaction, state)

    @discord.ui.button(
        emoji="🔊", label="+10%", style=discord.ButtonStyle.secondary,
        custom_id="music_panel:vol_up", row=1
    )
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):

        state = await self._get_state(interaction)
        if state is None:
            return

        state.volume = min(2.0, round(state.volume + 0.1, 2))

        if state.voice_client and isinstance(
            state.voice_client.source, discord.PCMVolumeTransformer
        ):
            state.voice_client.source.volume = state.volume

        await self._refresh_panel(interaction, state)

    @discord.ui.button(
        emoji="🔁", label="Lặp", style=discord.ButtonStyle.secondary,
        custom_id="music_panel:loop", row=1
    )
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):

        state = await self._get_state(interaction)
        if state is None:
            return

        order = ["off", "track", "queue"]
        state.loop_mode = order[(order.index(state.loop_mode) + 1) % len(order)]

        await self._refresh_panel(interaction, state)

    @discord.ui.button(
        label="📋 Hàng đợi", style=discord.ButtonStyle.secondary,
        custom_id="music_panel:queue", row=1
    )
    async def view_queue(self, interaction: discord.Interaction, button: discord.ui.Button):

        # Ai cũng xem được hàng đợi — không cần quyền DJ
        state = await self._get_state(interaction, require_dj=False)
        if state is None:
            return

        if not state.queue:
            await interaction.response.send_message(
                "📭 Hàng đợi hiện đang trống.", ephemeral=True
            )
            return

        lines = [
            f"`{index + 1}.` **{t.title}** (`{t.duration_text}`) — {t.requester.mention}"
            for index, t in enumerate(state.queue[:15])
        ]
        if len(state.queue) > 15:
            lines.append(f"*(+{len(state.queue) - 15} bài khác)*")

        embed = branded_embed(
            interaction.client,
            title=f"📋 Hàng đợi ({len(state.queue)} bài)",
            description="\n".join(lines)
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)