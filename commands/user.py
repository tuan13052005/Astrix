import discord
from discord import app_commands
from discord.ext import commands


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

        embed = discord.Embed(
            title=f"👤 Thông tin {member.display_name}",
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Tên", value=member.name, inline=True)
        embed.add_field(name="🏷️ Nickname", value=member.display_name, inline=True)
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=False)
        embed.add_field(
            name="🤖 Bot?",
            value="Có 🤖" if member.bot else "Không 👤",
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
            roles = [role.mention for role in member.roles[1:]]

            if roles:
                role_text = " ".join(roles[-10:])
            else:
                role_text = "Không có"

            embed.add_field(name="🎭 Vai trò", value=role_text, inline=False)

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

        embed = discord.Embed(
            title=f"🖼️ Avatar của {member.display_name}",
            color=discord.Color.blurple()
        )

        embed.set_image(url=avatar_url)
        embed.add_field(
            name="🔗 Link Avatar",
            value=f"[Mở ảnh]({avatar_url})",
            inline=False
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(User(bot))
