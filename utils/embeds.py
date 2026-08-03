import discord


DEFAULT_COLOR = 0x5865F2  # Discord blurple mặc định nếu config thiếu


def brand_color(bot) -> discord.Color:
    """Màu embed mặc định, lấy từ config.json (embed.color)."""

    value = DEFAULT_COLOR

    config = getattr(bot, "config", None)
    if config:
        value = config.get("embed", {}).get("color", DEFAULT_COLOR)

    return discord.Color(value)


def branded_embed(
    bot,
    title: str | None = None,
    description: str | None = None,
    color: discord.Color | None = None
) -> discord.Embed:
    """
    Tạo embed với màu + footer đồng nhất trên toàn bot
    (tên bot + icon avatar của Astrix).
    """

    embed = discord.Embed(
        title=title,
        description=description,
        color=color or brand_color(bot)
    )

    bot_name = "Astrix"
    config = getattr(bot, "config", None)
    if config:
        bot_name = config.get("bot_name", bot_name)

    if bot.user:
        embed.set_footer(
            text=f"{bot_name} V2",
            icon_url=bot.user.display_avatar.url
        )
    else:
        embed.set_footer(text=f"{bot_name} V2")

    return embed
