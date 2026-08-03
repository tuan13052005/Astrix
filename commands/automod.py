import re

import discord
from discord import app_commands
from discord.ext import commands

from utils import checks
from utils.logger import send_log
from utils.embeds import branded_embed
from utils.data_manager import (
    get_automod_settings,
    set_automod_enabled,
    set_automod_block_links,
    add_banned_word,
    remove_banned_word
)


LINK_PATTERN = re.compile(
    r"(https?://\S+|discord\.gg/\S+|discordapp\.com/invite/\S+)",
    re.IGNORECASE
)


class AutoMod(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # LỌC TIN NHẮN
    # =====================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author.bot:
            return

        if message.guild is None:
            return

        if not isinstance(message.author, discord.Member):
            return

        # Bỏ qua người có quyền quản lý tin nhắn (mod/admin)
        if message.author.guild_permissions.manage_messages:
            return

        settings = get_automod_settings(message.guild.id)

        if not settings["enabled"]:
            return

        reason = None
        content_lower = message.content.lower()

        # -------- KIỂM TRA TỪ CẤM --------
        for word in settings["banned_words"]:
            if word in content_lower:
                reason = f"chứa từ ngữ bị cấm (`{word}`)"
                break

        # -------- KIỂM TRA LINK / INVITE --------
        if reason is None and settings["block_links"]:
            if LINK_PATTERN.search(message.content):
                reason = "chứa liên kết không được phép"

        if reason is None:
            return

        try:
            await message.delete()
        except discord.HTTPException:
            return

        try:
            warning = await message.channel.send(
                f"⚠️ {message.author.mention}, tin nhắn của bạn đã bị xóa "
                f"vì {reason}.",
                delete_after=6
            )
        except discord.HTTPException:
            warning = None

        await send_log(
            self.bot,
            message.guild,
            title="🛡️ Auto-Mod: Đã xóa tin nhắn",
            description=(
                f"**Thành viên:** {message.author.mention} "
                f"(`{message.author.id}`)\n"
                f"**Kênh:** {message.channel.mention}\n"
                f"**Lý do:** {reason}\n"
                f"**Nội dung:** {message.content[:200]}"
            ),
            color=discord.Color.orange()
        )

    # =====================================================
    # /AUTOMOD — NHÓM LỆNH QUẢN LÝ
    # =====================================================

    automod_group = app_commands.Group(
        name="automod",
        description="Quản lý hệ thống auto-moderation",
        default_permissions=discord.Permissions(administrator=True)
    )

    @automod_group.command(name="enable", description="Bật auto-moderation")
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def automod_enable(self, interaction: discord.Interaction):
        set_automod_enabled(interaction.guild.id, True)
        await interaction.response.send_message("✅ Đã bật auto-moderation.")

    @automod_group.command(name="disable", description="Tắt auto-moderation")
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def automod_disable(self, interaction: discord.Interaction):
        set_automod_enabled(interaction.guild.id, False)
        await interaction.response.send_message("✅ Đã tắt auto-moderation.")

    @automod_group.command(
        name="blocklinks",
        description="Bật/tắt chặn link và link mời Discord"
    )
    @app_commands.describe(bat="True để bật, False để tắt")
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def automod_block_links(
        self,
        interaction: discord.Interaction,
        bat: bool
    ):
        set_automod_block_links(interaction.guild.id, bat)
        trang_thai = "bật" if bat else "tắt"
        await interaction.response.send_message(
            f"✅ Đã {trang_thai} chặn link."
        )

    @automod_group.command(
        name="addword",
        description="Thêm một từ vào danh sách cấm"
    )
    @app_commands.describe(tu="Từ cần cấm")
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def automod_add_word(
        self,
        interaction: discord.Interaction,
        tu: str
    ):
        added = add_banned_word(interaction.guild.id, tu)

        if added:
            await interaction.response.send_message(
                f"✅ Đã thêm `{tu}` vào danh sách từ cấm.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ `{tu}` đã có trong danh sách rồi.",
                ephemeral=True
            )

    @automod_group.command(
        name="removeword",
        description="Xóa một từ khỏi danh sách cấm"
    )
    @app_commands.describe(tu="Từ cần xóa")
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def automod_remove_word(
        self,
        interaction: discord.Interaction,
        tu: str
    ):
        removed = remove_banned_word(interaction.guild.id, tu)

        if removed:
            await interaction.response.send_message(
                f"✅ Đã xóa `{tu}` khỏi danh sách từ cấm.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ Không tìm thấy `{tu}` trong danh sách.",
                ephemeral=True
            )

    @automod_group.command(
        name="status",
        description="Xem trạng thái auto-moderation hiện tại"
    )
    @checks.guild_only()
    async def automod_status(self, interaction: discord.Interaction):

        settings = get_automod_settings(interaction.guild.id)

        embed = branded_embed(
            self.bot,
            title="🛡️ Trạng thái Auto-Moderation",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Bật/Tắt",
            value="✅ Bật" if settings["enabled"] else "❌ Tắt",
            inline=True
        )
        embed.add_field(
            name="Chặn link",
            value="✅ Bật" if settings["block_links"] else "❌ Tắt",
            inline=True
        )

        words = settings["banned_words"]
        embed.add_field(
            name=f"Từ cấm ({len(words)})",
            value=", ".join(f"`{w}`" for w in words) if words else "Không có",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
