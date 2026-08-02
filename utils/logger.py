import discord

from utils.data_manager import get_log_channel_id


async def send_log(
    bot,
    guild: discord.Guild,
    title: str,
    description: str,
    color: discord.Color = discord.Color.blurple()
):
    """
    Gửi log vào kênh log của server.

    Thứ tự ưu tiên tìm kênh log:
    1. Kênh đã được đặt qua lệnh /setlog (lưu trong data/guild_settings.json)
    2. Kênh có tên mặc định trong config.json (log.channel_name)
    """

    if guild is None:
        return

    log_channel = None

    # -----------------------------------------------------
    # 1. KÊNH ĐÃ ĐƯỢC CẤU HÌNH RIÊNG CHO SERVER
    # -----------------------------------------------------

    channel_id = get_log_channel_id(guild.id)

    if channel_id is not None:
        channel = guild.get_channel(channel_id)

        if isinstance(channel, discord.TextChannel):
            log_channel = channel

    # -----------------------------------------------------
    # 2. FALLBACK: TÊN KÊNH MẶC ĐỊNH TỪ config.json
    # -----------------------------------------------------

    if log_channel is None:
        default_name = "astrix-logs"
        config = getattr(bot, "config", None)

        if config:
            default_name = config.get("log", {}).get(
                "channel_name", default_name
            )

        log_channel = discord.utils.get(
            guild.text_channels,
            name=default_name
        )

    # Nếu vẫn không tìm thấy kênh log thì bỏ qua
    if log_channel is None:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )

    embed.set_footer(
        text="Astrix V2 • Moderation Log"
    )

    try:
        await log_channel.send(
            embed=embed
        )

    except discord.Forbidden:
        print(
            f"⚠️ Astrix không có quyền gửi log "
            f"trong server: {guild.name}"
        )

    except discord.HTTPException as error:
        print(
            f"⚠️ Không thể gửi log: {error}"
        )
