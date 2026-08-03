import discord
from discord import app_commands
from discord.ext import commands

from utils import checks
from utils.embeds import branded_embed
from utils.music_manager import MusicManager
from views.music_view import MusicControlView, build_panel_embed
from utils.data_manager import (
    get_dj_role_id,
    set_dj_role_id,
    disable_dj_role
)


class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.manager = MusicManager(bot)

        # Đăng ký view "trần" ngay khi cog load, để các nút trên
        # bảng điều khiển vẫn hoạt động kể cả sau khi bot restart
        # (custom_id cố định giúp discord.py định tuyến đúng).
        self.bot.add_view(MusicControlView(self.manager))

    # =====================================================
    # KIỂM TRA: NGƯỜI DÙNG CÓ ĐANG Ở TRONG VOICE CHANNEL KHÔNG
    # =====================================================

    @staticmethod
    def _user_voice_channel(interaction: discord.Interaction):
        if (
            isinstance(interaction.user, discord.Member)
            and interaction.user.voice
            and interaction.user.voice.channel
        ):
            return interaction.user.voice.channel
        return None

    # =====================================================
    # /JOIN
    # =====================================================

    @app_commands.command(
        name="join",
        description="Astrix vào kênh thoại của bạn"
    )
    @checks.guild_only()
    async def join(self, interaction: discord.Interaction):

        channel = self._user_voice_channel(interaction)

        if channel is None:
            await interaction.response.send_message(
                "❌ Bạn cần vào một kênh thoại trước.",
                ephemeral=True
            )
            return

        # channel.connect() có thể mất hơn 3 giây (giới hạn Discord cho
        # phép trả lời interaction ban đầu) -> defer trước để tránh lỗi
        # "Unknown interaction" (404) khi kết nối chậm.
        await interaction.response.defer()

        state = self.manager.get_state(interaction.guild.id)

        try:
            if state.voice_client is None or not state.voice_client.is_connected():
                state.voice_client = await channel.connect()
            else:
                await state.voice_client.move_to(channel)
        except Exception as error:
            await interaction.followup.send(
                f"❌ Không thể kết nối kênh thoại.\n"
                f"Chi tiết lỗi: `{type(error).__name__}: {error}`",
                ephemeral=True
            )
            return

        state.text_channel = interaction.channel

        await interaction.followup.send(
            f"🔊 Đã vào kênh thoại **{channel.name}**."
        )

    # =====================================================
    # /LEAVE
    # =====================================================

    @app_commands.command(
        name="leave",
        description="Astrix rời kênh thoại và xóa hàng đợi"
    )
    @checks.guild_only()
    async def leave(self, interaction: discord.Interaction):

        state = self.manager.get_state(interaction.guild.id)

        if state.voice_client is None or not state.voice_client.is_connected():
            await interaction.response.send_message(
                "❌ Astrix hiện không ở trong kênh thoại nào.",
                ephemeral=True
            )
            return

        state.clear()
        await state.voice_client.disconnect()
        state.voice_client = None
        state.panel_message = None
        self.manager.remove_state(interaction.guild.id)

        await interaction.response.send_message("👋 Đã rời kênh thoại.")

    # =====================================================
    # /PLAY
    # =====================================================

    @app_commands.command(
        name="play",
        description="Phát nhạc theo tên bài hát hoặc link YouTube"
    )
    @app_commands.describe(
        query="Tên bài hát cần tìm hoặc link YouTube"
    )
    @checks.guild_only()
    @checks.dj_only()
    async def play(
        self,
        interaction: discord.Interaction,
        query: str
    ):

        await interaction.response.defer()

        channel = self._user_voice_channel(interaction)
        state = self.manager.get_state(interaction.guild.id)

        # Tự động vào kênh thoại của người dùng nếu bot chưa vào
        if state.voice_client is None or not state.voice_client.is_connected():

            if channel is None:
                await interaction.followup.send(
                    "❌ Bạn cần vào một kênh thoại trước khi phát nhạc."
                )
                return

            try:
                state.voice_client = await channel.connect()
            except Exception as error:
                await interaction.followup.send(
                    f"❌ Không thể kết nối kênh thoại.\n"
                    f"Chi tiết lỗi: `{type(error).__name__}: {error}`"
                )
                return

        state.text_channel = interaction.channel

        try:
            tracks = await state.add_tracks(query, interaction.user)
        except Exception as error:
            await interaction.followup.send(
                f"❌ Không thể tìm/tải bài hát: `{error}`"
            )
            return

        is_playing_now = (
            state.voice_client.is_playing() or state.voice_client.is_paused()
        )

        if len(tracks) == 1:
            track = tracks[0]

            if is_playing_now:
                await interaction.followup.send(
                    f"➕ Đã thêm vào hàng đợi: **{track.title}** "
                    f"(`{track.duration_text}`)",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"🎶 Đang chuẩn bị phát **{track.title}**...",
                    ephemeral=True
                )
                await state.play_next()

        else:
            # -------- PLAYLIST: NHIỀU BÀI CÙNG LÚC --------
            if is_playing_now:
                await interaction.followup.send(
                    f"➕ Đã thêm **{len(tracks)} bài** từ playlist "
                    f"vào hàng đợi.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"🎶 Đã thêm **{len(tracks)} bài** từ playlist, "
                    f"đang chuẩn bị phát...",
                    ephemeral=True
                )
                await state.play_next()

    # =====================================================
    # /MUSICPANEL — GỌI BẢNG ĐIỀU KHIỂN
    # =====================================================

    @app_commands.command(
        name="musicpanel",
        description="Hiện bảng điều khiển nhạc (nút bấm play/skip/volume...)"
    )
    @checks.guild_only()
    async def musicpanel(self, interaction: discord.Interaction):

        state = self.manager.get_state(interaction.guild.id)
        state.text_channel = interaction.channel

        embed = build_panel_embed(self.bot, state)
        view = MusicControlView(self.manager)

        await interaction.response.send_message(embed=embed, view=view)
        state.panel_message = await interaction.original_response()

    # =====================================================
    # /SKIP
    # =====================================================

    @app_commands.command(
        name="skip",
        description="Bỏ qua bài hát đang phát"
    )
    @checks.guild_only()
    @checks.dj_only()
    async def skip(self, interaction: discord.Interaction):

        state = self.manager.get_state(interaction.guild.id)

        if state.voice_client is None or not (
            state.voice_client.is_playing() or state.voice_client.is_paused()
        ):
            await interaction.response.send_message(
                "❌ Hiện không có bài hát nào đang phát.",
                ephemeral=True
            )
            return

        skipped = state.current.title if state.current else "?"
        state.skip()

        await interaction.response.send_message(f"⏭️ Đã bỏ qua **{skipped}**.")

    # =====================================================
    # /PAUSE
    # =====================================================

    @app_commands.command(
        name="pause",
        description="Tạm dừng bài hát đang phát"
    )
    @checks.guild_only()
    @checks.dj_only()
    async def pause(self, interaction: discord.Interaction):

        state = self.manager.get_state(interaction.guild.id)

        if state.voice_client is None or not state.voice_client.is_playing():
            await interaction.response.send_message(
                "❌ Hiện không có bài hát nào đang phát.",
                ephemeral=True
            )
            return

        state.voice_client.pause()
        await interaction.response.send_message("⏸️ Đã tạm dừng.")

    # =====================================================
    # /RESUME
    # =====================================================

    @app_commands.command(
        name="resume",
        description="Tiếp tục phát bài hát đang tạm dừng"
    )
    @checks.guild_only()
    @checks.dj_only()
    async def resume(self, interaction: discord.Interaction):

        state = self.manager.get_state(interaction.guild.id)

        if state.voice_client is None or not state.voice_client.is_paused():
            await interaction.response.send_message(
                "❌ Hiện không có bài hát nào đang tạm dừng.",
                ephemeral=True
            )
            return

        state.voice_client.resume()
        await interaction.response.send_message("▶️ Đã tiếp tục phát.")

    # =====================================================
    # /STOP
    # =====================================================

    @app_commands.command(
        name="stop",
        description="Dừng phát nhạc, xóa hàng đợi và rời kênh thoại"
    )
    @checks.guild_only()
    @checks.dj_only()
    async def stop(self, interaction: discord.Interaction):

        state = self.manager.get_state(interaction.guild.id)

        if state.voice_client is None:
            await interaction.response.send_message(
                "❌ Astrix hiện không phát nhạc ở server này.",
                ephemeral=True
            )
            return

        state.clear()

        if state.voice_client.is_connected():
            await state.voice_client.disconnect()

        state.voice_client = None
        state.panel_message = None
        self.manager.remove_state(interaction.guild.id)

        await interaction.response.send_message(
            "⏹️ Đã dừng nhạc, xóa hàng đợi và rời kênh thoại."
        )

    # =====================================================
    # /QUEUE
    # =====================================================

    @app_commands.command(
        name="queue",
        description="Xem hàng đợi bài hát hiện tại"
    )
    @checks.guild_only()
    async def queue(self, interaction: discord.Interaction):

        state = self.manager.get_state(interaction.guild.id)

        embed = branded_embed(
            self.bot,
            title="🎵 Hàng đợi phát nhạc",
            color=discord.Color.blurple()
        )

        if state.current:
            embed.add_field(
                name="▶️ Đang phát",
                value=(
                    f"**{state.current.title}** "
                    f"(`{state.current.duration_text}`) — "
                    f"yêu cầu bởi {state.current.requester.mention}"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="▶️ Đang phát",
                value="Không có bài hát nào đang phát.",
                inline=False
            )

        if state.queue:
            lines = [
                f"`{index + 1}.` **{track.title}** "
                f"(`{track.duration_text}`) — {track.requester.mention}"
                for index, track in enumerate(state.queue[:10])
            ]

            if len(state.queue) > 10:
                lines.append(f"*(+{len(state.queue) - 10} bài khác)*")

            embed.add_field(
                name=f"📋 Tiếp theo ({len(state.queue)})",
                value="\n".join(lines),
                inline=False
            )
        else:
            embed.add_field(
                name="📋 Tiếp theo",
                value="Hàng đợi trống.",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    # =====================================================
    # /NOWPLAYING
    # =====================================================

    @app_commands.command(
        name="nowplaying",
        description="Xem bài hát đang phát"
    )
    @checks.guild_only()
    async def nowplaying(self, interaction: discord.Interaction):

        state = self.manager.get_state(interaction.guild.id)

        if state.current is None:
            await interaction.response.send_message(
                "❌ Hiện không có bài hát nào đang phát.",
                ephemeral=True
            )
            return

        track = state.current

        embed = branded_embed(
            self.bot,
            title="🎶 Đang phát",
            description=f"**{track.title}**",
            color=discord.Color.blurple()
        )
        embed.add_field(name="⏱️ Thời lượng", value=f"`{track.duration_text}`", inline=True)
        embed.add_field(name="📝 Yêu cầu bởi", value=track.requester.mention, inline=True)

        if track.webpage_url:
            embed.add_field(name="🔗 Link", value=track.webpage_url, inline=False)

        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)

        await interaction.response.send_message(embed=embed)

    # =====================================================
    # /VOLUME
    # =====================================================

    @app_commands.command(
        name="volume",
        description="Chỉnh âm lượng phát nhạc (0-200%)"
    )
    @app_commands.describe(muc="Mức âm lượng, từ 0 đến 200")
    @checks.guild_only()
    @checks.dj_only()
    async def volume(
        self,
        interaction: discord.Interaction,
        muc: app_commands.Range[int, 0, 200]
    ):

        state = self.manager.get_state(interaction.guild.id)
        state.volume = muc / 100

        if (
            state.voice_client
            and state.voice_client.source
            and isinstance(state.voice_client.source, discord.PCMVolumeTransformer)
        ):
            state.voice_client.source.volume = state.volume

        await interaction.response.send_message(f"🔊 Âm lượng: `{muc}%`")

    # =====================================================
    # /SHUFFLE
    # =====================================================

    @app_commands.command(
        name="shuffle",
        description="Xáo trộn hàng đợi bài hát hiện tại"
    )
    @checks.guild_only()
    @checks.dj_only()
    async def shuffle(self, interaction: discord.Interaction):

        state = self.manager.get_state(interaction.guild.id)

        if len(state.queue) < 2:
            await interaction.response.send_message(
                "❌ Cần ít nhất 2 bài trong hàng đợi để xáo trộn.",
                ephemeral=True
            )
            return

        state.shuffle()

        await interaction.response.send_message(
            f"🔀 Đã xáo trộn **{len(state.queue)}** bài trong hàng đợi."
        )

    # =====================================================
    # /LOOP
    # =====================================================

    @app_commands.command(
        name="loop",
        description="Đặt chế độ lặp lại nhạc"
    )
    @app_commands.describe(che_do="Chế độ lặp lại mong muốn")
    @app_commands.choices(che_do=[
        app_commands.Choice(name="Tắt", value="off"),
        app_commands.Choice(name="Lặp bài hiện tại", value="track"),
        app_commands.Choice(name="Lặp toàn bộ hàng đợi", value="queue"),
    ])
    @checks.guild_only()
    @checks.dj_only()
    async def loop(
        self,
        interaction: discord.Interaction,
        che_do: app_commands.Choice[str]
    ):

        state = self.manager.get_state(interaction.guild.id)
        state.loop_mode = che_do.value

        labels = {
            "off": "❌ Tắt",
            "track": "🔂 Lặp bài hiện tại",
            "queue": "🔁 Lặp toàn bộ hàng đợi"
        }

        await interaction.response.send_message(
            f"Chế độ lặp: **{labels[che_do.value]}**"
        )

    # =====================================================
    # /SETDJROLE — GIỚI HẠN LỆNH NHẠC THEO ROLE (ADMIN)
    # =====================================================

    @app_commands.command(
        name="setdjrole",
        description="Giới hạn lệnh nhạc, chỉ role này (và admin) mới dùng được"
    )
    @app_commands.describe(role="Role được phép điều khiển nhạc")
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def setdjrole(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):

        set_dj_role_id(interaction.guild.id, role.id)

        await interaction.response.send_message(
            f"✅ Từ giờ chỉ thành viên có role {role.mention} "
            f"(hoặc admin) mới dùng được lệnh nhạc và các nút trên "
            f"bảng điều khiển."
        )

    @app_commands.command(
        name="disablemusicrole",
        description="Gỡ giới hạn role — mở lệnh nhạc cho tất cả mọi người"
    )
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def disablemusicrole(self, interaction: discord.Interaction):

        disable_dj_role(interaction.guild.id)

        await interaction.response.send_message(
            "✅ Đã gỡ giới hạn — mọi người đều dùng được lệnh nhạc."
        )

    @app_commands.command(
        name="djrole",
        description="Xem role DJ hiện tại của server"
    )
    @checks.guild_only()
    async def djrole(self, interaction: discord.Interaction):

        role_id = get_dj_role_id(interaction.guild.id)
        role = interaction.guild.get_role(role_id) if role_id else None

        if role:
            value = f"{role.mention} (và admin) mới dùng được lệnh nhạc."
        else:
            value = "Chưa giới hạn — mọi người đều dùng được lệnh nhạc."

        embed = branded_embed(
            self.bot,
            title="🎧 Role DJ hiện tại",
            description=value
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # =====================================================
    # TỰ ĐỘNG RỜI KHI KÊNH THOẠI TRỐNG (BOT LÀ NGƯỜI CUỐI CÙNG)
    # =====================================================

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):

        if member.id != self.bot.user.id:
            return

        # Nếu bot vừa rời kênh (bị kick, hoặc tự disconnect) -> dọn state
        if before.channel is not None and after.channel is None:
            self.manager.remove_state(member.guild.id)


async def setup(bot):
    await bot.add_cog(Music(bot))