import time
import re
import logging
from datetime import datetime, timezone, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.data_manager import (
    add_reminder,
    get_due_reminders,
    get_user_reminders,
    remove_reminder
)

log = logging.getLogger("astrix.reminder")


DURATION_PATTERN = re.compile(
    r"(\d+)\s*(d|h|m|s)",
    re.IGNORECASE
)

UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(text: str) -> int | None:
    """
    Hỗ trợ nhiều đơn vị ghép: '1h30m', '2d', '45s'...
    Trả về tổng số giây, hoặc None nếu không parse được.
    """

    text = text.strip().lower().replace(" ", "")
    matches = DURATION_PATTERN.findall(text)

    if not matches:
        return None

    total_seconds = 0
    for value, unit in matches:
        total_seconds += int(value) * UNITS[unit]

    return total_seconds if total_seconds > 0 else None


class Reminder(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    # =====================================================
    # /REMIND
    # =====================================================

    @app_commands.command(
        name="remind",
        description="Đặt nhắc nhở sau một khoảng thời gian"
    )
    @app_commands.describe(
        thoi_gian="VD: 10m, 2h, 1d, 1h30m",
        noi_dung="Nội dung cần nhắc"
    )
    async def remind(
        self,
        interaction: discord.Interaction,
        thoi_gian: str,
        noi_dung: str
    ):

        seconds = parse_duration(thoi_gian)

        if seconds is None:
            await interaction.response.send_message(
                "❌ Sai định dạng thời gian. Dùng vd: `10m`, `2h`, `1d`, `1h30m`.",
                ephemeral=True
            )
            return

        if seconds > 30 * 86400:
            await interaction.response.send_message(
                "❌ Thời gian nhắc tối đa là 30 ngày.",
                ephemeral=True
            )
            return

        remind_at = time.time() + seconds

        entry = add_reminder(
            guild_id=interaction.guild.id if interaction.guild else None,
            channel_id=interaction.channel.id,
            user_id=interaction.user.id,
            remind_at=remind_at,
            message=noi_dung
        )

        remind_time = discord.utils.utcnow() + timedelta(seconds=seconds)

        await interaction.response.send_message(
            f"⏰ Đã đặt nhắc nhở `#{entry['id']}` — "
            f"mình sẽ nhắc bạn {discord.utils.format_dt(remind_time, style='R')}.",
            ephemeral=True
        )

    # =====================================================
    # /REMINDERS — DANH SÁCH NHẮC NHỞ CỦA TÔI
    # =====================================================

    @app_commands.command(
        name="reminders",
        description="Xem danh sách nhắc nhở của bạn"
    )
    async def reminders(self, interaction: discord.Interaction):

        entries = get_user_reminders(interaction.user.id)

        if not entries:
            await interaction.response.send_message(
                "📭 Bạn chưa có nhắc nhở nào.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="⏰ Nhắc nhở của bạn",
            color=discord.Color.blurple()
        )

        for entry in entries[:15]:
            dt = datetime.fromtimestamp(
                entry["remind_at"], tz=timezone.utc
            )

            embed.add_field(
                name=f"#{entry['id']} — {discord.utils.format_dt(dt, style='R')}",
                value=entry["message"][:200],
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # =====================================================
    # /DELREMIND — HỦY MỘT NHẮC NHỞ
    # =====================================================

    @app_commands.command(
        name="delremind",
        description="Hủy một nhắc nhở theo ID"
    )
    @app_commands.describe(
        remind_id="ID nhắc nhở (xem qua /reminders)"
    )
    async def delremind(
        self,
        interaction: discord.Interaction,
        remind_id: int
    ):

        # Chỉ cho hủy nhắc nhở của chính mình
        entries = get_user_reminders(interaction.user.id)

        if not any(entry["id"] == remind_id for entry in entries):
            await interaction.response.send_message(
                f"❌ Không tìm thấy nhắc nhở `#{remind_id}` của bạn.",
                ephemeral=True
            )
            return

        remove_reminder(remind_id)

        await interaction.response.send_message(
            f"✅ Đã hủy nhắc nhở `#{remind_id}`.",
            ephemeral=True
        )

    # =====================================================
    # VÒNG LẶP KIỂM TRA NHẮC NHỞ ĐẾN HẠN
    # =====================================================

    @tasks.loop(seconds=15)
    async def check_reminders(self):

        try:
            due = get_due_reminders(time.time())
        except Exception:
            log.exception("Lỗi khi đọc dữ liệu nhắc nhở")
            return

        for entry in due:

            try:
                remove_reminder(entry["id"])

                channel = self.bot.get_channel(entry["channel_id"])

                embed = discord.Embed(
                    title="⏰ Nhắc nhở!",
                    description=entry["message"],
                    color=discord.Color.blurple()
                )

                mention = f"<@{entry['user_id']}>"

                if channel is not None:
                    await channel.send(content=mention, embed=embed)
                else:
                    user = await self.bot.fetch_user(entry["user_id"])
                    await user.send(embed=embed)

            except discord.HTTPException:
                # Kênh/user không còn truy cập được — bỏ qua
                pass
            except Exception:
                log.exception(f"Lỗi khi gửi nhắc nhở #{entry.get('id')}")

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

    @check_reminders.error
    async def check_reminders_error(self, error: Exception):
        log.exception(f"Vòng lặp check_reminders gặp lỗi, đang khởi động lại: {error}")
        self.check_reminders.restart()


async def setup(bot):
    await bot.add_cog(Reminder(bot))
