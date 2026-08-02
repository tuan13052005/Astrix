import discord
from discord import app_commands
from discord.ext import commands


class Server(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # /SERVERINFO
    # =====================================================

    @app_commands.command(
        name="serverinfo",
        description="Xem thông tin server"
    )
    async def serverinfo(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Lệnh này chỉ được sử dụng trong server.",
                ephemeral=True
            )

            return

        guild = interaction.guild

        embed = discord.Embed(
            title=f"🏠 {guild.name}",
            description="Thông tin máy chủ Discord",
            color=discord.Color.blurple()
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=False)

        if guild.owner:
            owner = guild.owner.mention
        else:
            owner = f"<@{guild.owner_id}>"

        embed.add_field(name="👑 Chủ Server", value=owner, inline=True)
        embed.add_field(name="👥 Thành viên", value=f"`{guild.member_count}`", inline=True)

        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)

        embed.add_field(name="💬 Kênh văn bản", value=f"`{text_channels}`", inline=True)
        embed.add_field(name="🔊 Kênh thoại", value=f"`{voice_channels}`", inline=True)
        embed.add_field(name="📁 Danh mục", value=f"`{categories}`", inline=True)
        embed.add_field(name="🎭 Vai trò", value=f"`{len(guild.roles)}`", inline=True)
        embed.add_field(name="🚀 Boost", value=f"`{guild.premium_subscription_count}`", inline=True)
        embed.add_field(name="⭐ Level Boost", value=f"`{guild.premium_tier}`", inline=True)

        verification_names = {
            discord.VerificationLevel.none: "Không",
            discord.VerificationLevel.low: "Thấp",
            discord.VerificationLevel.medium: "Trung bình",
            discord.VerificationLevel.high: "Cao",
            discord.VerificationLevel.highest: "Rất cao"
        }

        verification = verification_names.get(guild.verification_level, "Không xác định")
        embed.add_field(name="🔐 Xác minh", value=verification, inline=True)

        embed.add_field(
            name="📅 Ngày tạo",
            value=discord.utils.format_dt(guild.created_at, style="F"),
            inline=False
        )

        embed.set_footer(text=f"Astrix V2 • {guild.name}")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Server(bot))
