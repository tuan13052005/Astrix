import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import branded_embed, brand_color


class User(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # /USERINFO
    # =====================================================

    @app_commands.command(
        name="userinfo",
        description="Xem thông tin người dùng"
    )
    @app_commands.describe(
        member="Người dùng muốn xem"
    )
    async def userinfo(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None
    ):

        await interaction.response.defer()

        member = member or interaction.user

        # Dùng màu role cao nhất của thành viên làm điểm nhấn cá nhân hóa,
        # nếu họ không có role màu nào thì dùng màu thương hiệu mặc định.
        accent_color = (
            member.color
            if member.color != discord.Color.default()
            else brand_color(self.bot)
        )

        embed = branded_embed(
            self.bot,
            title=f"👤 {member.display_name}",
            color=accent_color
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="👤 Tên", value=member.name, inline=True)
        embed.add_field(name="🏷️ Nickname", value=member.display_name, inline=True)
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)

        embed.add_field(
            name="🤖 Loại",
            value="Bot 🤖" if member.bot else "Người dùng 👤",
            inline=True
        )

        if member.top_role.name != "@everyone":
            embed.add_field(
                name="🎖️ Role cao nhất",
                value=member.top_role.mention,
                inline=True
            )

        status_emojis = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🌙 Idle",
            discord.Status.dnd: "⛔ Do Not Disturb",
            discord.Status.offline: "⚫ Offline"
        }
        embed.add_field(
            name="📶 Trạng thái",
            value=status_emojis.get(member.status, "⚫ Offline"),
            inline=True
        )

        embed.add_field(
            name="📅 Tài khoản tạo",
            value=discord.utils.format_dt(member.created_at, style="F"),
            inline=False
        )

        if member.joined_at:
            joined = discord.utils.format_dt(member.joined_at, style="F")
        else:
            joined = "Không xác định"

        embed.add_field(name="📥 Tham gia server", value=joined, inline=False)

        if member.roles:
            roles = [role.mention for role in reversed(member.roles[1:])]

            if roles:
                shown = roles[:10]
                role_text = " ".join(shown)
                if len(roles) > 10:
                    role_text += f" *(+{len(roles) - 10} role khác)*"
            else:
                role_text = "Không có"

            embed.add_field(
                name=f"🎭 Vai trò ({len(member.roles) - 1})",
                value=role_text,
                inline=False
            )

        await interaction.followup.send(embed=embed)

    # =====================================================
    # /AVATAR
    # =====================================================

    @app_commands.command(
        name="avatar",
        description="Xem avatar người dùng"
    )
    @app_commands.describe(
        member="Người dùng muốn xem avatar"
    )
    async def avatar(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None
    ):

        member = member or interaction.user
        avatar_url = member.display_avatar.url

        accent_color = (
            member.color
            if member.color != discord.Color.default()
            else brand_color(self.bot)
        )

        embed = branded_embed(
            self.bot,
            title=f"🖼️ Avatar của {member.display_name}",
            color=accent_color
        )

        embed.set_image(url=avatar_url)
        embed.add_field(
            name="🔗 Liên kết",
            value=(
                f"[PNG]({member.display_avatar.replace(format='png').url}) • "
                f"[JPG]({member.display_avatar.replace(format='jpg').url}) • "
                f"[WEBP]({member.display_avatar.replace(format='webp').url})"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(User(bot))
