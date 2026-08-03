import discord
from discord import app_commands

from utils.data_manager import get_dj_role_id


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
# KIỂM TRA ROLE "DJ" (DÙNG CHO LỆNH NHẠC + BẢNG ĐIỀU KHIỂN)
# =========================================================

def is_dj(interaction: discord.Interaction) -> bool:
    """
    Hàm kiểm tra thuần (không tự gửi phản hồi), dùng chung cho:
    - decorator dj_only() (slash command)
    - các nút bấm trong MusicControlView (views/music_view.py)

    Quy tắc:
    - Admin luôn được phép, bất kể có role DJ hay không.
    - Server CHƯA cấu hình role DJ nào -> mở cho tất cả.
    - Đã cấu hình -> chỉ ai có role đó (+ admin).
    """

    if not isinstance(interaction.user, discord.Member):
        return False

    if interaction.guild is None:
        return True  # guild_only() đã xử lý riêng trường hợp này

    if interaction.user.guild_permissions.administrator:
        return True

    role_id = get_dj_role_id(interaction.guild.id)

    if role_id is None:
        return True

    return any(role.id == role_id for role in interaction.user.roles)


def dj_only():
    """
    Decorator: giới hạn lệnh nhạc theo role DJ đã cấu hình qua
    /setdjrole. Nếu server CHƯA cấu hình role DJ nào thì mở cho
    tất cả mọi người (hành vi mặc định, không phá vỡ trải nghiệm
    cũ). Admin luôn được phép, bất kể có role DJ hay không.
    """

    async def predicate(interaction: discord.Interaction) -> bool:

        if is_dj(interaction):
            return True

        role_id = get_dj_role_id(interaction.guild.id)
        role = interaction.guild.get_role(role_id) if role_id else None
        role_text = role.mention if role else "DJ (role đã bị xóa)"

        await interaction.response.send_message(
            f"❌ Bạn cần role {role_text} để sử dụng lệnh nhạc này.",
            ephemeral=True
        )
        return False

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