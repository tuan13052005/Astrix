import discord


async def send_log(
    bot,
    guild: discord.Guild,
    title: str,
    description: str,
    color: discord.Color = discord.Color.blurple()
):
    """
    Gửi log vào kênh log của server.

    Hiện tại dùng tên kênh:
    #astrix-logs
    """

    if guild is None:
        return

    # Tìm kênh log
    log_channel = discord.utils.get(
        guild.text_channels,
        name="astrix-logs"
    )

    # Nếu chưa có kênh log thì bỏ qua
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