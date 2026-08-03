import logging
import random
import time
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils import checks
from utils.data_manager import (
    create_giveaway,
    get_giveaway,
    add_giveaway_participant,
    get_due_giveaways,
    mark_giveaway_ended
)


log = logging.getLogger("astrix.giveaway")


def parse_duration(text: str) -> int | None:
    """
    Chuyển '10m', '2h', '1d', '30s' thành số giây.
    Trả về None nếu sai định dạng.
    """

    text = text.strip().lower()

    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}

    if not text or text[-1] not in units:
        return None

    try:
        value = int(text[:-1])
    except ValueError:
        return None

    if value <= 0:
        return None

    return value * units[text[-1]]


class GiveawayJoinView(discord.ui.View):

    def __init__(self, message_id: int | None = None):
        super().__init__(timeout=None)
        self.message_id = message_id

    @discord.ui.button(
        label="🎉 Tham gia",
        style=discord.ButtonStyle.success,
        custom_id="giveaway_join"
    )
    async def join(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        message_id = self.message_id or interaction.message.id
        giveaway = get_giveaway(message_id)

        if giveaway is None or giveaway["ended"]:
            await interaction.response.send_message(
                "⚠️ Giveaway này đã kết thúc.",
                ephemeral=True
            )
            return

        added = add_giveaway_participant(message_id, interaction.user.id)

        if added:
            await interaction.response.send_message(
                "✅ Bạn đã tham gia giveaway thành công! Chúc may mắn 🍀",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "☑️ Bạn đã tham gia giveaway này rồi.",
                ephemeral=True
            )


class Giveaway(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        # View "trần" — xử lý nút bấm cho MỌI giveaway đang chạy,
        # kể cả sau khi bot khởi động lại (nhờ custom_id cố định).
        self.bot.add_view(GiveawayJoinView())
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

    # =====================================================
    # /GIVEAWAY START
    # =====================================================

    @app_commands.command(
        name="giveaway",
        description="Tạo một giveaway mới"
    )
    @app_commands.describe(
        prize="Phần thưởng",
        duration="Thời gian (vd: 30s, 10m, 2h, 1d)",
        winners="Số người thắng"
    )
    @checks.guild_only()
    @checks.has_permissions(manage_guild=True)
    async def giveaway(
        self,
        interaction: discord.Interaction,
        prize: str,
        duration: str,
        winners: app_commands.Range[int, 1, 20] = 1
    ):

        seconds = parse_duration(duration)

        if seconds is None:
            await interaction.response.send_message(
                "❌ Sai định dạng thời gian. Dùng vd: `30s`, `10m`, `2h`, `1d`.",
                ephemeral=True
            )
            return

        end_time = time.time() + seconds

        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=(
                f"**Phần thưởng:** {prize}\n"
                f"**Số người thắng:** {winners}\n"
                f"**Kết thúc:** "
                f"{discord.utils.format_dt(discord.utils.utcnow() + timedelta(seconds=seconds), style='R')}\n\n"
                f"Bấm nút bên dưới để tham gia!"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Tổ chức bởi {interaction.user.display_name}")

        view = GiveawayJoinView()

        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()

        # Gắn message_id thật vào view đang hiển thị
        view.message_id = message.id

        create_giveaway(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            message_id=message.id,
            host_id=interaction.user.id,
            prize=prize,
            winners_count=winners,
            end_time=end_time
        )

    # =====================================================
    # VÒNG LẶP KIỂM TRA GIVEAWAY ĐẾN HẠN
    # =====================================================

    @tasks.loop(seconds=20)
    async def check_giveaways(self):

        try:
            due = get_due_giveaways(time.time())
        except Exception:
            log.exception("Lỗi khi đọc dữ liệu giveaway")
            return

        for entry in due:
            try:
                await self._finish_giveaway(entry)
            except Exception:
                log.exception(
                    f"Lỗi khi kết thúc giveaway #{entry.get('message_id')}"
                )

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        await self.bot.wait_until_ready()

    @check_giveaways.error
    async def check_giveaways_error(self, error: Exception):
        # An toàn cuối cùng: nếu vòng lặp tự nó lỗi ngoài dự kiến,
        # ghi log rồi tự khởi động lại thay vì để tác vụ nền chết hẳn.
        log.exception(f"Vòng lặp check_giveaways gặp lỗi, đang khởi động lại: {error}")
        self.check_giveaways.restart()

    async def _finish_giveaway(self, entry: dict):

        mark_giveaway_ended(entry["message_id"])

        channel = self.bot.get_channel(entry["channel_id"])

        if channel is None:
            return

        participants = entry["participants"]

        if not participants:
            try:
                await channel.send(
                    f"😢 Giveaway **{entry['prize']}** kết thúc "
                    f"nhưng không có ai tham gia."
                )
            except discord.HTTPException:
                pass
            return

        winners_count = min(entry["winners_count"], len(participants))
        winner_ids = random.sample(participants, winners_count)
        mentions = ", ".join(f"<@{uid}>" for uid in winner_ids)

        embed = discord.Embed(
            title="🎊 Giveaway đã kết thúc!",
            description=(
                f"**Phần thưởng:** {entry['prize']}\n"
                f"**Người thắng:** {mentions}"
            ),
            color=discord.Color.gold()
        )

        try:
            await channel.send(
                content=f"🎉 Chúc mừng {mentions}!",
                embed=embed
            )
        except discord.HTTPException:
            pass


async def setup(bot):
    await bot.add_cog(Giveaway(bot))
