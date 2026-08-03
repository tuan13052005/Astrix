import discord
from discord import app_commands
from discord.ext import commands

from utils import checks
from utils.embeds import branded_embed
from utils.data_manager import (
    get_guild_settings,
    set_welcome,
    disable_welcome,
    set_goodbye,
    disable_goodbye,
    set_autorole,
    disable_autorole
)


def _format_template(template: str, member: discord.Member) -> str:
    return (
        template
        .replace("{member}", member.mention)
        .replace("{member_name}", member.display_name)
        .replace("{server}", member.guild.name)
        .replace("{membercount}", str(member.guild.member_count))
    )


class Welcome(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # SỰ KIỆN: THÀNH VIÊN THAM GIA
    # =====================================================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        settings = get_guild_settings(member.guild.id)

        # -------- WELCOME MESSAGE --------
        welcome = settings.get("welcome")

        if welcome:
            channel = member.guild.get_channel(welcome["channel_id"])

            if isinstance(channel, discord.TextChannel):
                embed = branded_embed(
                    self.bot,
                    title="👋 Chào mừng thành viên mới!",
                    description=_format_template(welcome["message"], member),
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.display_avatar.url)

                try:
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    pass

        # -------- AUTOROLE --------
        autorole_id = settings.get("autorole_id")

        if autorole_id:
            role = member.guild.get_role(autorole_id)

            if role:
                try:
                    await member.add_roles(
                        role,
                        reason="Auto-role khi tham gia server"
                    )
                except discord.Forbidden:
                    pass

    # =====================================================
    # SỰ KIỆN: THÀNH VIÊN RỜI SERVER
    # =====================================================

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):

        settings = get_guild_settings(member.guild.id)
        goodbye = settings.get("goodbye")

        if not goodbye:
            return

        channel = member.guild.get_channel(goodbye["channel_id"])

        if not isinstance(channel, discord.TextChannel):
            return

        embed = branded_embed(
            self.bot,
            title="👋 Tạm biệt!",
            description=_format_template(goodbye["message"], member),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass

    # =====================================================
    # /SETWELCOME
    # =====================================================

    @app_commands.command(
        name="setwelcome",
        description="Đặt kênh và nội dung chào mừng thành viên mới"
    )
    @app_commands.describe(
        channel="Kênh gửi lời chào mừng",
        message=(
            "Nội dung. Dùng {member}, {member_name}, "
            "{server}, {membercount}"
        )
    )
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def setwelcome(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str = "Chào mừng {member} đến với {server}! 🎉"
    ):

        set_welcome(interaction.guild.id, channel.id, message)

        await interaction.response.send_message(
            f"✅ Đã bật lời chào mừng tại {channel.mention}.\n"
            f"📋 Nội dung mẫu: {_format_template(message, interaction.user)}"
        )

    @app_commands.command(
        name="disablewelcome",
        description="Tắt lời chào mừng thành viên mới"
    )
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def disablewelcome(self, interaction: discord.Interaction):
        disable_welcome(interaction.guild.id)
        await interaction.response.send_message("✅ Đã tắt lời chào mừng.")

    # =====================================================
    # /SETGOODBYE
    # =====================================================

    @app_commands.command(
        name="setgoodbye",
        description="Đặt kênh và nội dung tạm biệt khi thành viên rời server"
    )
    @app_commands.describe(
        channel="Kênh gửi lời tạm biệt",
        message="Nội dung. Dùng {member_name}, {server}, {membercount}"
    )
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def setgoodbye(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str = "{member_name} đã rời khỏi {server}. 😢"
    ):

        set_goodbye(interaction.guild.id, channel.id, message)

        await interaction.response.send_message(
            f"✅ Đã bật lời tạm biệt tại {channel.mention}."
        )

    @app_commands.command(
        name="disablegoodbye",
        description="Tắt lời tạm biệt khi thành viên rời server"
    )
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def disablegoodbye(self, interaction: discord.Interaction):
        disable_goodbye(interaction.guild.id)
        await interaction.response.send_message("✅ Đã tắt lời tạm biệt.")

    # =====================================================
    # /SETAUTOROLE
    # =====================================================

    @app_commands.command(
        name="setautorole",
        description="Tự động gán role cho thành viên mới tham gia"
    )
    @app_commands.describe(
        role="Role sẽ tự động gán"
    )
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def setautorole(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):

        guild = interaction.guild

        if role >= guild.me.top_role:
            await interaction.response.send_message(
                "❌ Role của Astrix phải cao hơn role này để có thể gán tự động.",
                ephemeral=True
            )
            return

        set_autorole(guild.id, role.id)

        await interaction.response.send_message(
            f"✅ Thành viên mới sẽ tự động nhận role {role.mention}."
        )

    @app_commands.command(
        name="disableautorole",
        description="Tắt tự động gán role"
    )
    @checks.guild_only()
    @checks.has_permissions(administrator=True)
    async def disableautorole(self, interaction: discord.Interaction):
        disable_autorole(interaction.guild.id)
        await interaction.response.send_message("✅ Đã tắt auto-role.")


async def setup(bot):
    await bot.add_cog(Welcome(bot))
