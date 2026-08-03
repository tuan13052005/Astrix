import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import branded_embed


CATEGORIES = {
    "utility": {
        "label": "🛠️ Tiện ích",
        "emoji": "🛠️",
        "description": "Lệnh cơ bản, thông tin server & người dùng",
        "commands": (
            "`/ping` — Kiểm tra bot\n"
            "`/userinfo` — Thông tin người dùng\n"
            "`/avatar` — Xem avatar\n"
            "`/serverinfo` — Thông tin server"
        )
    },
    "moderation": {
        "label": "🛡️ Quản trị",
        "emoji": "🛡️",
        "description": "Kiểm duyệt, cảnh cáo, kick/ban thành viên",
        "commands": (
            "`/clear` — Xóa tin nhắn\n"
            "`/kick` — Yêu cầu kick thành viên\n"
            "`/ban` — Ban thành viên\n"
            "`/mute` — Timeout thành viên\n"
            "`/unmute` — Gỡ timeout\n"
            "`/warn` — Cảnh cáo thành viên\n"
            "`/warnings` — Xem cảnh cáo của thành viên\n"
            "`/delwarn` — Xóa một cảnh cáo\n"
            "`/clearwarnings` — Xóa toàn bộ cảnh cáo"
        )
    },
    "system": {
        "label": "📋 Hệ thống",
        "emoji": "📋",
        "description": "Cấu hình kênh log của Astrix",
        "commands": (
            "`/setlog` — Đặt kênh log\n"
            "`/viewlog` — Xem kênh log hiện tại"
        )
    },
    "welcome": {
        "label": "👋 Welcome / Auto-role",
        "emoji": "👋",
        "description": "Lời chào mừng, tạm biệt, tự động gán role",
        "commands": (
            "`/setwelcome` — Đặt lời chào mừng\n"
            "`/disablewelcome` — Tắt lời chào mừng\n"
            "`/setgoodbye` — Đặt lời tạm biệt\n"
            "`/disablegoodbye` — Tắt lời tạm biệt\n"
            "`/setautorole` — Tự động gán role\n"
            "`/disableautorole` — Tắt auto-role"
        )
    },
    "automod": {
        "label": "🤖 Auto-Moderation",
        "emoji": "🤖",
        "description": "Tự động lọc từ cấm và link/invite spam",
        "commands": (
            "`/automod enable` — Bật auto-moderation\n"
            "`/automod disable` — Tắt auto-moderation\n"
            "`/automod blocklinks` — Bật/tắt chặn link\n"
            "`/automod addword` — Thêm từ cấm\n"
            "`/automod removeword` — Xóa từ cấm\n"
            "`/automod status` — Xem trạng thái"
        )
    },
    "fun": {
        "label": "🎉 Poll / Giveaway",
        "emoji": "🎉",
        "description": "Bình chọn và tổ chức giveaway",
        "commands": (
            "`/poll` — Tạo bình chọn (tối đa 5 lựa chọn)\n"
            "`/giveaway` — Tạo giveaway, tự động quay số"
        )
    },
    "reminder": {
        "label": "⏰ Nhắc nhở",
        "emoji": "⏰",
        "description": "Đặt và quản lý nhắc nhở cá nhân",
        "commands": (
            "`/remind` — Đặt nhắc nhở\n"
            "`/reminders` — Xem danh sách nhắc nhở\n"
            "`/delremind` — Hủy nhắc nhở"
        )
    },
    "music": {
        "label": "🎵 Nhạc",
        "emoji": "🎵",
        "description": "Nghe nhạc trong kênh thoại, hàng đợi, lặp lại",
        "commands": (
            "`/join` — Vào kênh thoại\n"
            "`/leave` — Rời kênh thoại\n"
            "`/play` — Phát nhạc theo tên hoặc link\n"
            "`/skip` — Bỏ qua bài hát\n"
            "`/pause` — Tạm dừng\n"
            "`/resume` — Tiếp tục phát\n"
            "`/stop` — Dừng nhạc & rời kênh thoại\n"
            "`/queue` — Xem hàng đợi\n"
            "`/nowplaying` — Bài đang phát\n"
            "`/volume` — Chỉnh âm lượng\n"
            "`/shuffle` — Xáo trộn hàng đợi\n"
            "`/loop` — Chế độ lặp lại\n"
            "`/setdjrole` — Giới hạn lệnh nhạc theo role\n"
            "`/disablemusicrole` — Gỡ giới hạn role\n"
            "`/djrole` — Xem role DJ hiện tại"
        )
    },
}


class HelpSelect(discord.ui.Select):

    def __init__(self, bot):
        self.bot = bot

        options = [
            discord.SelectOption(
                label=data["label"],
                value=key,
                description=data["description"],
                emoji=data["emoji"]
            )
            for key, data in CATEGORIES.items()
        ]

        super().__init__(
            placeholder="📂 Chọn một danh mục lệnh...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):

        data = CATEGORIES[self.values[0]]

        embed = branded_embed(
            self.bot,
            title=f"{data['label']}",
            description=data["commands"]
        )

        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):

    def __init__(self, bot):
        super().__init__(timeout=180)
        self.add_item(HelpSelect(bot))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


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

        latency = round(self.bot.latency * 1000)

        embed = branded_embed(
            self.bot,
            title="🏓 Pong!",
            description=f"⚡ Độ trễ: `{latency}ms`"
        )

        await interaction.response.send_message(embed=embed)

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

        total_commands = sum(
            data["commands"].count("`/") for data in CATEGORIES.values()
        )

        embed = branded_embed(
            self.bot,
            title="🌟 Astrix V2",
            description=(
                "Bot Discord đa chức năng — quản trị, chào mừng thành viên, "
                "auto-mod, bình chọn, giveaway, nhắc nhở và nghe nhạc.\n\n"
                f"📦 **{total_commands} lệnh** trong **{len(CATEGORIES)} danh mục**.\n"
                "👇 Chọn một danh mục bên dưới để xem chi tiết."
            )
        )

        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        view = HelpView(self.bot)

        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(General(bot))
