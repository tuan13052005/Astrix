import discord
from discord import app_commands


# =========================================================
# CHỈ CHO PHÉP DÙNG TRONG SERVER
# =========================================================

def guild_only():
    """
    Decorator: chặn lệnh nếu dùng ngoài server (DM).
    Dùng thay cho việc lặp lại đoạn kiểm tra
    `if interaction.guild is None` trong từng lệnh.
    """

    async def predicate(interaction: discord.Interaction) -> bool:

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Lệnh này chỉ sử dụng được trong server.",
                ephemeral=True
            )
            return False

        return True

    return app_commands.check(predicate)


# =========================================================
# KIỂM TRA QUYỀN NGƯỜI DÙNG
# =========================================================

def has_permissions(**perms: bool):
    """
    Decorator: kiểm tra quyền của người dùng trong server,
    trả về thông báo lỗi bằng tiếng Việt.

    Ví dụ:
        @checks.has_permissions(manage_messages=True)
    """

    async def predicate(interaction: discord.Interaction) -> bool:

        if not isinstance(interaction.user, discord.Member):
            return False

        missing = [
            perm for perm, required in perms.items()
            if required and not getattr(
                interaction.user.guild_permissions, perm, False
            )
        ]

        if missing:
            missing_text = ", ".join(f"`{perm}`" for perm in missing)

            await interaction.response.send_message(
                f"❌ Bạn thiếu quyền để sử dụng lệnh này: {missing_text}",
                ephemeral=True
            )
            return False

        return True

    return app_commands.check(predicate)


# =========================================================
# KIỂM TRA BOT CÓ THỂ TÁC ĐỘNG LÊN THÀNH VIÊN KHÔNG
# =========================================================

def bot_can_act_on(
    guild: discord.Guild,
    target: discord.Member
) -> bool:
    """
    True nếu bot có thể kick/ban/mute thành viên này:
    - Target không phải chủ server
    - Role của bot cao hơn role của target
    """

    me = guild.me

    if me is None:
        return False

    if target.id == guild.owner_id:
        return False

    return target.top_role < me.top_role
