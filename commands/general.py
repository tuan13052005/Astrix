import discord
from discord import app_commands
from discord.ext import commands


class General(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # /PING
    # =====================================================

    @app_commands.command(
        name="ping",
        description="Kiểm tra Astrix có hoạt động không"
    )
    async def ping(
        self,
        interaction: discord.Interaction
    ):

        latency = round(
            self.bot.latency * 1000
        )

        await interaction.response.send_message(
            f"🏓 **Pong!**\n"
            f"⚡ Độ trễ: `{latency}ms`"
        )

    # =====================================================
    # /HELP
    # =====================================================

    @app_commands.command(
        name="help",
        description="Xem danh sách lệnh Astrix"
    )
    async def help_command(
        self,
        interaction: discord.Interaction
    ):

        embed = discord.Embed(
            title="🌟 Astrix V2",
            description="Bot Discord đa chức năng",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🛠️ Tiện ích",
            value=(
                "`/ping` — Kiểm tra bot\n"
                "`/userinfo` — Thông tin người dùng\n"
                "`/avatar` — Xem avatar\n"
                "`/serverinfo` — Thông tin server"
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ Quản trị",
            value=(
                "`/clear` — Xóa tin nhắn\n"
                "`/kick` — Yêu cầu kick thành viên\n"
                "`/ban` — Ban thành viên\n"
                "`/mute` — Timeout thành viên\n"
                "`/unmute` — Gỡ timeout\n"
                "`/warn` — Cảnh cáo thành viên"
            ),
            inline=False
        )

        embed.add_field(
            name="📋 Hệ thống",
            value=(
                "`/setlog` — Đặt kênh log"
            ),
            inline=False
        )

        embed.set_footer(
            text="Astrix V2 • Multi-Purpose Discord Bot"
        )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(bot):
    await bot.add_cog(General(bot))