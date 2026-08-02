import os
import json

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


# =========================================================
# LOAD .ENV
# =========================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "❌ Không tìm thấy DISCORD_TOKEN trong file .env"
    )


# =========================================================
# LOAD CONFIG
# =========================================================

CONFIG_FILE = "config.json"

try:
    with open(
        CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        config = json.load(file)

except FileNotFoundError:
    raise RuntimeError(
        "❌ Không tìm thấy config.json"
    )

except json.JSONDecodeError:
    raise RuntimeError(
        "❌ config.json bị lỗi định dạng JSON"
    )


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()

# Thành viên
intents.members = True

# Nội dung tin nhắn
intents.message_content = True


# =========================================================
# DANH SÁCH EXTENSIONS CẦN LOAD
# =========================================================

EXTENSIONS = [
    "commands.general",
    "commands.user",
    "commands.server",
    "commands.moderation",
    "commands.system",
]


# =========================================================
# ASTRIX BOT
# =========================================================

class Astrix(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

        # Cho phép mọi cog truy cập config qua self.bot.config
        self.config = config

    async def setup_hook(self):

        print("📦 Đang load commands...")

        for extension in EXTENSIONS:
            await self.load_extension(extension)
            print(f"   ↳ Đã load: {extension}")

        print("✅ Đã load toàn bộ commands!")

        # Sync slash commands
        print("🔄 Đang đồng bộ Slash Commands...")

        synced = await self.tree.sync()

        print(
            f"✅ Đã đồng bộ {len(synced)} Slash Commands!"
        )


# =========================================================
# KHỞI TẠO
# =========================================================

bot = Astrix()


# =========================================================
# XỬ LÝ LỖI SLASH COMMANDS (TẬP TRUNG, ĐỒNG BỘ)
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    # Các lỗi do check() tự trả thông báo riêng (đã ephemeral)
    # thì không cần xử lý lại ở đây.
    if isinstance(error, app_commands.CheckFailure):
        return

    if isinstance(error, app_commands.CommandOnCooldown):
        message = (
            f"⏳ Lệnh đang hồi chiêu, thử lại sau "
            f"`{error.retry_after:.1f}s`."
        )

    elif isinstance(error, app_commands.MissingPermissions):
        message = "❌ Bạn không có đủ quyền để sử dụng lệnh này."

    elif isinstance(error, app_commands.BotMissingPermissions):
        message = "❌ Astrix thiếu quyền cần thiết để thực hiện lệnh này."

    else:
        print(f"❌ App Command Error: {error}")
        message = "❌ Đã xảy ra lỗi không xác định khi chạy lệnh."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    except discord.HTTPException:
        pass


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    print()
    print("=" * 55)
    print("🚀 ASTRIX V2 ĐÃ ONLINE!")
    print("=" * 55)

    print(f"🤖 Bot       : {bot.user}")
    print(f"🆔 ID        : {bot.user.id}")
    print(f"🌐 Servers   : {len(bot.guilds)}")
    print(
        f"📦 Version   : "
        f"{config.get('version', 'Unknown')}"
    )

    print("=" * 55)
    print("⚡ Astrix đang hoạt động!")
    print("=" * 55)
    print()


# =========================================================
# BOT ERROR
# =========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    print(
        f"❌ Command Error: {error}"
    )


# =========================================================
# CHẠY BOT
# =========================================================

if __name__ == "__main__":

    try:

        bot.run(TOKEN)

    except discord.LoginFailure:

        print()
        print("❌ TOKEN KHÔNG HỢP LỆ!")
        print(
            "Hãy kiểm tra DISCORD_TOKEN trong .env"
        )

    except Exception as error:

        print()
        print(
            f"❌ Astrix gặp lỗi: {error}"
        )
