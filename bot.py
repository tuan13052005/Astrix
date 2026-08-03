import os
import json
import logging
from logging.handlers import RotatingFileHandler

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from utils.keep_alive import keep_alive


# =========================================================
# LOAD .ENV
# =========================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "❌ Không tìm thấy DISCORD_TOKEN trong file .env"
    )

# Tùy chọn: đặt DEV_GUILD_ID trong .env để đồng bộ slash command
# NGAY LẬP TỨC cho một server cụ thể (phục vụ test khi phát triển).
# Nếu để trống, bot sẽ đồng bộ TOÀN CỤC (global) — Discord có thể
# mất tới khoảng 1 giờ để lệnh mới hiện ra trên client.
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")


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
# LOGGING (GHI RA FILE + CONSOLE — DỄ TRA LỖI KHI CHẠY 24/24)
# =========================================================

os.makedirs("data", exist_ok=True)

log_formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

file_handler = RotatingFileHandler(
    filename="data/bot.log",
    encoding="utf-8",
    maxBytes=5 * 1024 * 1024,  # 5MB / file
    backupCount=3
)
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

log = logging.getLogger("astrix")


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
    "commands.welcome",
    "commands.automod",
    "commands.poll",
    "commands.giveaway",
    "commands.reminder",
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

        log.info("📦 Đang load commands...")

        for extension in EXTENSIONS:
            await self.load_extension(extension)
            log.info(f"   ↳ Đã load: {extension}")

        log.info("✅ Đã load toàn bộ commands!")

        # Sync slash commands
        log.info("🔄 Đang đồng bộ Slash Commands...")

        if DEV_GUILD_ID:
            # Đồng bộ theo guild: gần như tức thì, dùng khi phát triển/test.
            guild_obj = discord.Object(id=int(DEV_GUILD_ID))
            self.tree.copy_global_to(guild=guild_obj)
            synced = await self.tree.sync(guild=guild_obj)

            log.info(
                f"✅ Đã đồng bộ {len(synced)} Slash Commands "
                f"cho guild {DEV_GUILD_ID} (tức thì)."
            )

        else:
            # Đồng bộ toàn cục: dùng khi phát hành chính thức.
            # Lưu ý: Discord có thể mất tới ~1 giờ để lệnh mới
            # hiện ra trên client của người dùng.
            synced = await self.tree.sync()

            log.info(
                f"✅ Đã đồng bộ {len(synced)} Slash Commands (toàn cục)."
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
        log.exception(f"App Command Error: {error}")
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

    log.info("=" * 55)
    log.info("🚀 ASTRIX V2 ĐÃ ONLINE!")
    log.info("=" * 55)

    log.info(f"🤖 Bot       : {bot.user}")
    log.info(f"🆔 ID        : {bot.user.id}")
    log.info(f"🌐 Servers   : {len(bot.guilds)}")
    log.info(f"📦 Version   : {config.get('version', 'Unknown')}")

    log.info("=" * 55)
    log.info("⚡ Astrix đang hoạt động!")
    log.info("=" * 55)


# =========================================================
# THEO DÕI KẾT NỐI (HỮU ÍCH KHI CHẠY 24/24)
# =========================================================

@bot.event
async def on_disconnect():
    log.warning("⚠️ Mất kết nối tới Discord — đang thử kết nối lại...")


@bot.event
async def on_resumed():
    log.info("🔄 Đã kết nối lại với Discord thành công.")


# =========================================================
# BẮT LỖI KHÔNG XÁC ĐỊNH TRONG EVENT (KHÔNG LÀM SẬP BOT)
# =========================================================

@bot.event
async def on_error(event_method, *args, **kwargs):
    log.exception(f"Lỗi không xác định trong sự kiện '{event_method}'")


# =========================================================
# BOT ERROR (PREFIX COMMAND — KHÔNG DÙNG NHƯNG GIỮ ĐỂ AN TOÀN)
# =========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):
    log.exception(f"Command Error: {error}")


# =========================================================
# CHẠY BOT
# =========================================================

if __name__ == "__main__":

    # Web server nhỏ để nền tảng cloud (Render/Replit) nhận diện
    # tiến trình đang "sống" và để UptimeRobot ping giữ bot thức.
    keep_alive()

    try:

        bot.run(TOKEN, log_handler=None)

    except discord.LoginFailure:

        log.error("❌ TOKEN KHÔNG HỢP LỆ! Hãy kiểm tra DISCORD_TOKEN trong .env")

    except Exception:

        log.exception("❌ Astrix gặp lỗi nghiêm trọng khi khởi động")
