import discord
from discord import app_commands
from discord.ext import commands

from utils import checks
from utils.data_manager import get_log_channel_id, set_guild_setting
from utils.embeds import branded_embed


class System(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # /SETLOG
    # =====================================================

    @app_commands.command(
        name="setlog",
        description="Đặt kênh nhận log kiểm duyệt của Astrix"
    )
    @app_commands.describe(
        channel="Kênh văn bản dùng để nhận log"
    )
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def setlog(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):

        set_guild_setting(
            interaction.guild.id,
            "log_channel_id",
            channel.id
        )

        embed = branded_embed(
            self.bot,
            title="✅ Đã đặt kênh log",
            description=f"Log kiểm duyệt sẽ được gửi vào {channel.mention}.",
            color=discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed
        )

    # =====================================================
    # /VIEWLOG
    # =====================================================

    @app_commands.command(
        name="viewlog",
        description="Xem kênh log hiện tại của server"
    )
    @checks.guild_only()
    async def viewlog(
        self,
        interaction: discord.Interaction
    ):

        channel_id = get_log_channel_id(interaction.guild.id)
        channel = (
            interaction.guild.get_channel(channel_id)
            if channel_id else None
        )

        if channel:
            value = channel.mention
        else:
            value = (
                "Chưa thiết lập — Astrix sẽ tìm kênh "
                "`#astrix-logs` theo mặc định."
            )

        embed = branded_embed(
            self.bot,
            title="📋 Kênh Log Hiện Tại",
            description=value
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(System(bot))
