import discord
from datetime import timedelta, datetime, timezone
from discord import app_commands
from discord.ext import commands

from views.kick_view import KickApprovalView
from utils import checks
from utils.logger import send_log
from utils.embeds import branded_embed
from utils.data_manager import (
    add_warning,
    get_warnings,
    remove_warning,
    clear_warnings
)


class Moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

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
    @checks.guild_only()
    @checks.has_permissions(manage_messages=True)
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100]
    ):

        if not isinstance(
            interaction.channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ Lệnh này chỉ dùng trong kênh văn bản.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        deleted = await interaction.channel.purge(limit=amount)

        await interaction.followup.send(
            f"🧹 Đã xóa **{len(deleted)}** tin nhắn.",
            ephemeral=True
        )

        await send_log(
            self.bot,
            interaction.guild,
            title="🧹 Xóa tin nhắn",
            description=(
                f"**Kênh:** {interaction.channel.mention}\n"
                f"**Số lượng:** {len(deleted)}\n"
                f"**Người thực hiện:** {interaction.user.mention}"
            )
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
    @checks.guild_only()
    @checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Không có lý do"
    ):

        guild = interaction.guild

        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Bạn không thể yêu cầu kick chính mình.",
                ephemeral=True
            )
            return

        if member.id == guild.owner_id:
            await interaction.response.send_message(
                "❌ Không thể kick chủ server.",
                ephemeral=True
            )
            return

        if not checks.bot_can_act_on(guild, member):
            await interaction.response.send_message(
                "❌ Astrix không thể kick người này vì "
                "vai trò của họ cao hơn hoặc bằng vai trò của bot.",
                ephemeral=True
            )
            return

        embed = branded_embed(
            self.bot,
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
            value=guild.owner.mention,
            inline=False
        )

        embed.set_footer(
            text="Chỉ chủ server mới có thể Duyệt hoặc Từ chối."
        )

        timeout = (
            getattr(self.bot, "config", {})
            .get("moderation", {})
            .get("kick_request_timeout", 300)
        )

        view = KickApprovalView(
            target=member,
            requester=interaction.user,
            reason=reason,
            timeout=timeout
        )

        await interaction.response.send_message(
            content=guild.owner.mention,
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
    @checks.guild_only()
    @checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Không có lý do"
    ):

        guild = interaction.guild

        if member.id == guild.owner_id:
            await interaction.response.send_message(
                "❌ Không thể ban chủ server.",
                ephemeral=True
            )
            return

        if not checks.bot_can_act_on(guild, member):
            await interaction.response.send_message(
                "❌ Astrix không thể ban người này.",
                ephemeral=True
            )
            return

        try:
            await member.ban(
                reason=f"{reason} | Bởi {interaction.user}"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Astrix không có đủ quyền để ban người này.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🔨 Đã ban {member.mention}.\n"
            f"📝 Lý do: {reason}"
        )

        await send_log(
            self.bot,
            guild,
            title="🔨 Ban thành viên",
            description=(
                f"**Thành viên:** {member.mention} (`{member.id}`)\n"
                f"**Người thực hiện:** {interaction.user.mention}\n"
                f"**Lý do:** {reason}"
            ),
            color=discord.Color.red()
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
    @checks.guild_only()
    @checks.has_permissions(moderate_members=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str = "Không có lý do"
    ):

        await interaction.response.defer()

        guild = interaction.guild
        bot_member = guild.me

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

        if member.id == guild.owner_id:
            await interaction.followup.send(
                "❌ Không thể mute chủ server."
            )
            return

        if member.id == interaction.user.id:
            await interaction.followup.send(
                "❌ Bạn không thể tự mute chính mình."
            )
            return

        if not checks.bot_can_act_on(guild, member):
            await interaction.followup.send(
                "❌ Role của Astrix phải nằm cao hơn "
                "role của thành viên cần mute."
            )
            return

        try:
            duration = discord.utils.utcnow() + timedelta(minutes=minutes)

            await member.timeout(
                duration,
                reason=f"{reason} | Bởi {interaction.user}"
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

        embed = branded_embed(
            self.bot,
            title="🔇 Thành viên đã bị mute",
            color=discord.Color.orange()
        )

        embed.add_field(name="👤 Thành viên", value=member.mention, inline=True)
        embed.add_field(name="⏱️ Thời gian", value=f"{minutes} phút", inline=True)
        embed.add_field(name="📝 Người thực hiện", value=interaction.user.mention, inline=True)
        embed.add_field(name="📋 Lý do", value=reason, inline=False)

        await interaction.followup.send(embed=embed)

        await send_log(
            self.bot,
            guild,
            title="🔇 Mute thành viên",
            description=(
                f"**Thành viên:** {member.mention} (`{member.id}`)\n"
                f"**Thời gian:** {minutes} phút\n"
                f"**Người thực hiện:** {interaction.user.mention}\n"
                f"**Lý do:** {reason}"
            ),
            color=discord.Color.orange()
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
    @checks.guild_only()
    @checks.has_permissions(moderate_members=True)
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):

        try:
            await member.timeout(
                None,
                reason=f"Gỡ mute bởi {interaction.user}"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Astrix không có đủ quyền để unmute.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🔊 Đã unmute {member.mention}."
        )

        await send_log(
            self.bot,
            interaction.guild,
            title="🔊 Unmute thành viên",
            description=(
                f"**Thành viên:** {member.mention} (`{member.id}`)\n"
                f"**Người thực hiện:** {interaction.user.mention}"
            ),
            color=discord.Color.green()
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
    @checks.guild_only()
    @checks.has_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Không có lý do"
    ):

        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Bạn không thể tự warn chính mình.",
                ephemeral=True
            )
            return

        entry = add_warning(
            guild_id=interaction.guild.id,
            member_id=member.id,
            moderator_id=interaction.user.id,
            reason=reason
        )

        total = len(get_warnings(interaction.guild.id, member.id))

        embed = branded_embed(
            self.bot,
            title="⚠️ Cảnh cáo thành viên",
            color=discord.Color.yellow()
        )

        embed.add_field(name="👤 Thành viên", value=member.mention, inline=False)
        embed.add_field(name="📝 Người cảnh cáo", value=interaction.user.mention, inline=False)
        embed.add_field(name="📋 Lý do", value=reason, inline=False)
        embed.set_footer(
            text=f"Cảnh cáo #{entry['id']} • Tổng cộng: {total} lần"
        )

        await interaction.response.send_message(embed=embed)

        await send_log(
            self.bot,
            interaction.guild,
            title="⚠️ Warn thành viên",
            description=(
                f"**Thành viên:** {member.mention} (`{member.id}`)\n"
                f"**Người thực hiện:** {interaction.user.mention}\n"
                f"**Lý do:** {reason}\n"
                f"**Tổng số cảnh cáo:** {total}"
            ),
            color=discord.Color.yellow()
        )

    # =====================================================
    # /WARNINGS — XEM DANH SÁCH CẢNH CÁO
    # =====================================================

    @app_commands.command(
        name="warnings",
        description="Xem danh sách cảnh cáo của một thành viên"
    )
    @app_commands.describe(
        member="Thành viên cần xem"
    )
    @checks.guild_only()
    @checks.has_permissions(moderate_members=True)
    async def warnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):

        entries = get_warnings(interaction.guild.id, member.id)

        embed = branded_embed(
            self.bot,
            title=f"📋 Cảnh cáo của {member.display_name}",
            color=discord.Color.yellow()
        )

        if not entries:
            embed.description = "Thành viên này chưa có cảnh cáo nào."
        else:
            for entry in entries[-10:]:
                moderator = f"<@{entry['moderator_id']}>"
                timestamp = discord.utils.format_dt(
                    datetime.fromtimestamp(
                        entry["timestamp"], tz=timezone.utc
                    ),
                    style="R"
                )

                embed.add_field(
                    name=f"#{entry['id']} — {timestamp}",
                    value=f"**Lý do:** {entry['reason']}\n**Bởi:** {moderator}",
                    inline=False
                )

            embed.set_footer(text=f"Tổng cộng: {len(entries)} cảnh cáo")

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =====================================================
    # /DELWARN — XÓA MỘT CẢNH CÁO
    # =====================================================

    @app_commands.command(
        name="delwarn",
        description="Xóa một cảnh cáo theo ID"
    )
    @app_commands.describe(
        member="Thành viên cần xóa cảnh cáo",
        warn_id="ID cảnh cáo (xem qua /warnings)"
    )
    @checks.guild_only()
    @checks.has_permissions(moderate_members=True)
    async def delwarn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        warn_id: int
    ):

        success = remove_warning(
            interaction.guild.id,
            member.id,
            warn_id
        )

        if not success:
            await interaction.response.send_message(
                f"❌ Không tìm thấy cảnh cáo `#{warn_id}` của {member.mention}.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"✅ Đã xóa cảnh cáo `#{warn_id}` của {member.mention}."
        )

        await send_log(
            self.bot,
            interaction.guild,
            title="🗑️ Xóa cảnh cáo",
            description=(
                f"**Thành viên:** {member.mention} (`{member.id}`)\n"
                f"**Cảnh cáo:** #{warn_id}\n"
                f"**Người thực hiện:** {interaction.user.mention}"
            )
        )

    # =====================================================
    # /CLEARWARNINGS — XÓA TOÀN BỘ CẢNH CÁO
    # =====================================================

    @app_commands.command(
        name="clearwarnings",
        description="Xóa toàn bộ cảnh cáo của một thành viên"
    )
    @app_commands.describe(
        member="Thành viên cần xóa toàn bộ cảnh cáo"
    )
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def clearwarnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):

        clear_warnings(interaction.guild.id, member.id)

        await interaction.response.send_message(
            f"🧹 Đã xóa toàn bộ cảnh cáo của {member.mention}."
        )

        await send_log(
            self.bot,
            interaction.guild,
            title="🧹 Xóa toàn bộ cảnh cáo",
            description=(
                f"**Thành viên:** {member.mention} (`{member.id}`)\n"
                f"**Người thực hiện:** {interaction.user.mention}"
            )
        )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
