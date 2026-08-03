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
                "`/warn` — Cảnh cáo thành viên\n"
                "`/warnings` — Xem cảnh cáo của thành viên\n"
                "`/delwarn` — Xóa một cảnh cáo\n"
                "`/clearwarnings` — Xóa toàn bộ cảnh cáo"
            ),
            inline=False
        )

        embed.add_field(
            name="📋 Hệ thống",
            value=(
                "`/setlog` — Đặt kênh log\n"
                "`/viewlog` — Xem kênh log hiện tại"
            ),
            inline=False
        )

        embed.add_field(
            name="👋 Welcome / Auto-role",
            value=(
                "`/setwelcome` — Đặt lời chào mừng\n"
                "`/disablewelcome` — Tắt lời chào mừng\n"
                "`/setgoodbye` — Đặt lời tạm biệt\n"
                "`/disablegoodbye` — Tắt lời tạm biệt\n"
                "`/setautorole` — Tự động gán role\n"
                "`/disableautorole` — Tắt auto-role"
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ Auto-Moderation",
            value=(
                "`/automod enable|disable` — Bật/tắt lọc tự động\n"
                "`/automod blocklinks` — Chặn link/invite\n"
                "`/automod addword|removeword` — Quản lý từ cấm\n"
                "`/automod status` — Xem trạng thái"
            ),
            inline=False
        )

        embed.add_field(
            name="🎉 Poll / Giveaway",
            value=(
                "`/poll` — Tạo bình chọn\n"
                "`/giveaway` — Tạo giveaway"
            ),
            inline=False
        )

        embed.add_field(
            name="⏰ Nhắc nhở",
            value=(
                "`/remind` — Đặt nhắc nhở\n"
                "`/reminders` — Xem danh sách nhắc nhở\n"
                "`/delremind` — Hủy nhắc nhở"
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
