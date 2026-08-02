import discord
from datetime import timedelta
from discord import app_commands
from discord.ext import commands

from views.kick_view import KickApprovalView


class Moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # KIỂM TRA QUYỀN QUẢN TRỊ
    # =====================================================

    async def require_moderator(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Lệnh này chỉ sử dụng được trong server.",
                ephemeral=True
            )
            return False

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return False

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Bạn không có quyền sử dụng lệnh này.",
                ephemeral=True
            )
            return False

        return True

    # =====================================================
    # /CLEAR
    # =====================================================

    @app_commands.command(
        name="clear",
        description="Xóa nhiều tin nhắn"
    )
    @app_commands.describe(
        amount="Số lượng tin nhắn cần xóa (1-100)"
    )
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100]
    ):

        if not await self.require_moderator(interaction):
            return

        if not isinstance(
            interaction.channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ Lệnh này chỉ dùng trong kênh văn bản.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        deleted = await interaction.channel.purge(
            limit=amount
        )

        await interaction.followup.send(
            f"🧹 Đã xóa **{len(deleted)}** tin nhắn.",
            ephemeral=True
        )

    # =====================================================
    # /KICK
    # =====================================================

    @app_commands.command(
        name="kick",
        description="Gửi yêu cầu kick thành viên cho chủ server"
    )
    @app_commands.describe(
        member="Thành viên cần kick",
        reason="Lý do kick"
    )
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Không có lý do"
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Lệnh này chỉ dùng trong server.",
                ephemeral=True
            )
            return

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return

        # Người yêu cầu phải có quyền quản lý thành viên
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message(
                "❌ Bạn không có quyền yêu cầu kick thành viên.",
                ephemeral=True
            )
            return

        # Không cho kick chính mình
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Bạn không thể yêu cầu kick chính mình.",
                ephemeral=True
            )
            return

        # Không cho yêu cầu kick chủ server
        if member.id == interaction.guild.owner_id:
            await interaction.response.send_message(
                "❌ Không thể kick chủ server.",
                ephemeral=True
            )
            return

        # Kiểm tra bot có thể kick mục tiêu
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "❌ Astrix không thể kick người này vì "
                "vai trò của họ cao hơn hoặc bằng vai trò của bot.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="⚠️ Yêu cầu Kick Thành Viên",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Thành viên",
            value=member.mention,
            inline=True
        )

        embed.add_field(
            name="📝 Người yêu cầu",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="📋 Lý do",
            value=reason,
            inline=False
        )

        embed.add_field(
            name="👑 Người duyệt",
            value=interaction.guild.owner.mention,
            inline=False
        )

        embed.set_footer(
            text="Chỉ chủ server mới có thể Duyệt hoặc Từ chối."
        )

        view = KickApprovalView(
            target=member,
            requester=interaction.user,
            reason=reason
        )

        await interaction.response.send_message(
            content=interaction.guild.owner.mention,
            embed=embed,
            view=view
        )

    # =====================================================
    # /BAN
    # =====================================================

    @app_commands.command(
        name="ban",
        description="Ban thành viên khỏi server"
    )
    @app_commands.describe(
        member="Thành viên cần ban",
        reason="Lý do ban"
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Không có lý do"
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Lệnh này chỉ dùng trong server.",
                ephemeral=True
            )
            return

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return

        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message(
                "❌ Bạn không có quyền ban thành viên.",
                ephemeral=True
            )
            return

        if member.id == interaction.guild.owner_id:
            await interaction.response.send_message(
                "❌ Không thể ban chủ server.",
                ephemeral=True
            )
            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "❌ Astrix không thể ban người này.",
                ephemeral=True
            )
            return

        try:
            await member.ban(
                reason=f"{reason} | Bởi {interaction.user}"
            )

            await interaction.response.send_message(
                f"🔨 Đã ban {member.mention}.\n"
                f"📝 Lý do: {reason}"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Astrix không có đủ quyền để ban người này.",
                ephemeral=True
            )

    # =====================================================
    # /MUTE
    # =====================================================

    @app_commands.command(
    name="mute",
    description="Timeout thành viên"
    )
    @app_commands.describe(
        member="Thành viên cần mute",
        minutes="Thời gian mute tính bằng phút",
        reason="Lý do mute"
    )
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str = "Không có lý do"
    ):

        # -------------------------------------------------
        # KIỂM TRA SERVER
        # -------------------------------------------------

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Lệnh này chỉ dùng trong server.",
                ephemeral=True
            )
            return

        # -------------------------------------------------
        # KIỂM TRA NGƯỜI DÙNG
        # -------------------------------------------------

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return

        # -------------------------------------------------
        # KIỂM TRA QUYỀN NGƯỜI DÙNG
        # -------------------------------------------------

        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "❌ Bạn không có quyền mute thành viên.",
                ephemeral=True
            )
            return

        # -------------------------------------------------
        # DEFER NGAY LẬP TỨC
        # -------------------------------------------------

        await interaction.response.defer()

        guild = interaction.guild
        bot_member = guild.me

        # -------------------------------------------------
        # KIỂM TRA QUYỀN BOT
        # -------------------------------------------------

        if bot_member is None:
            await interaction.followup.send(
                "❌ Không thể xác định Astrix trong server."
            )
            return

        if not bot_member.guild_permissions.moderate_members:
            await interaction.followup.send(
                "❌ Astrix chưa có quyền "
                "**Điều hành thành viên / Moderate Members**."
            )
            return

        # -------------------------------------------------
        # KHÔNG CHO MUTE CHỦ SERVER
        # -------------------------------------------------

        if member.id == guild.owner_id:
            await interaction.followup.send(
                "❌ Không thể mute chủ server."
            )
            return

        # -------------------------------------------------
        # KHÔNG CHO MUTE CHÍNH MÌNH
        # -------------------------------------------------

        if member.id == interaction.user.id:
            await interaction.followup.send(
                "❌ Bạn không thể tự mute chính mình."
            )
            return

        # -------------------------------------------------
        # KIỂM TRA ROLE
        # -------------------------------------------------

        if member.top_role >= bot_member.top_role:
            await interaction.followup.send(
                "❌ Role của Astrix phải nằm cao hơn "
                "role của thành viên cần mute."
            )
            return

        # -------------------------------------------------
        # THỰC HIỆN TIMEOUT
        # -------------------------------------------------

        try:

            duration = discord.utils.utcnow() + timedelta(
                minutes=minutes
            )

            await member.timeout(
                duration,
                reason=(
                    f"{reason} | "
                    f"Bởi {interaction.user}"
                )
            )

        except discord.Forbidden:

            await interaction.followup.send(
                "❌ Discord từ chối thao tác.\n\n"
                "Hãy kiểm tra:\n"
                "• Astrix có quyền Moderate Members không?\n"
                "• Role Astrix có cao hơn thành viên không?"
            )
            return

        except discord.HTTPException as error:

            await interaction.followup.send(
                f"❌ Discord trả về lỗi khi mute.\n"
                f"Mã lỗi: `{error.code}`"
            )
            return

        # -------------------------------------------------
        # THÀNH CÔNG
        # -------------------------------------------------

        embed = discord.Embed(
            title="🔇 Thành viên đã bị mute",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Thành viên",
            value=member.mention,
            inline=True
        )

        embed.add_field(
            name="⏱️ Thời gian",
            value=f"{minutes} phút",
            inline=True
        )

        embed.add_field(
            name="📝 Người thực hiện",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="📋 Lý do",
            value=reason,
            inline=False
        )

        await interaction.followup.send(
            embed=embed
        )

    # =====================================================
    # /UNMUTE
    # =====================================================

    @app_commands.command(
        name="unmute",
        description="Gỡ timeout thành viên"
    )
    @app_commands.describe(
        member="Thành viên cần unmute"
    )
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Lệnh này chỉ dùng trong server.",
                ephemeral=True
            )
            return

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return

        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "❌ Bạn không có quyền unmute thành viên.",
                ephemeral=True
            )
            return

        try:

            await member.timeout(
                None,
                reason=f"Gỡ mute bởi {interaction.user}"
            )

            await interaction.response.send_message(
                f"🔊 Đã unmute {member.mention}."
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Astrix không có đủ quyền để unmute.",
                ephemeral=True
            )

    # =====================================================
    # /WARN
    # =====================================================

    @app_commands.command(
        name="warn",
        description="Cảnh cáo thành viên"
    )
    @app_commands.describe(
        member="Thành viên cần cảnh cáo",
        reason="Lý do cảnh cáo"
    )
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Không có lý do"
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Lệnh này chỉ dùng trong server.",
                ephemeral=True
            )
            return

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return

        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "❌ Bạn không có quyền warn thành viên.",
                ephemeral=True
            )
            return

        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Bạn không thể tự warn chính mình.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="⚠️ Cảnh cáo thành viên",
            color=discord.Color.yellow()
        )

        embed.add_field(
            name="👤 Thành viên",
            value=member.mention,
            inline=False
        )

        embed.add_field(
            name="📝 Người cảnh cáo",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="📋 Lý do",
            value=reason,
            inline=False
        )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(bot):
    await bot.add_cog(Moderation(bot))