import os
import json

import discord
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
# ASTRIX BOT
# =========================================================

class Astrix(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):

        print("📦 Đang load commands...")

        # General
        await self.load_extension(
            "commands.general"
        )

        # User
        await self.load_extension(
            "commands.user"
        )

        # Server
        await self.load_extension(
            "commands.server"
        )

        # Moderation
        await self.load_extension(
            "commands.moderation"
        )

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