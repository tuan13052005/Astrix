import discord
from discord import app_commands
from utils.embeds import branded_embed
from discord.ext import commands


EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]


class PollView(discord.ui.View):

    def __init__(self, options: list[str]):
        super().__init__(timeout=None)

        self.options = options
        self.votes: dict[int, int] = {}  # user_id -> option index
        self.counts = [0] * len(options)

        for index, option in enumerate(options):
            button = discord.ui.Button(
                label=f"{option[:75]}",
                emoji=EMOJIS[index],
                style=discord.ButtonStyle.secondary,
                custom_id=f"poll_option_{index}"
            )
            button.callback = self._make_callback(index)
            self.add_item(button)

    def _make_callback(self, index: int):

        async def callback(interaction: discord.Interaction):

            user_id = interaction.user.id
            previous = self.votes.get(user_id)

            if previous == index:
                await interaction.response.send_message(
                    "☑️ Bạn đã chọn phương án này rồi.",
                    ephemeral=True
                )
                return

            if previous is not None:
                self.counts[previous] -= 1

            self.votes[user_id] = index
            self.counts[index] += 1

            await interaction.response.edit_message(
                embed=self._build_embed(interaction.message.embeds[0]),
                view=self
            )

        return callback

    def _build_embed(self, base_embed: discord.Embed) -> discord.Embed:

        embed = base_embed.copy()
        total = sum(self.counts) or 1

        lines = []
        for index, option in enumerate(self.options):
            count = self.counts[index]
            percent = round(count / total * 100)
            bar_len = round(percent / 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)

            lines.append(
                f"{EMOJIS[index]} **{option}**\n"
                f"`{bar}` {count} phiếu ({percent}%)"
            )

        embed.description = "\n\n".join(lines)
        embed.set_footer(text=f"Tổng cộng: {sum(self.counts)} phiếu bầu")

        return embed


class Poll(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="poll",
        description="Tạo bình chọn (tối đa 5 lựa chọn)"
    )
    @app_commands.describe(
        question="Câu hỏi bình chọn",
        option1="Lựa chọn 1",
        option2="Lựa chọn 2",
        option3="Lựa chọn 3 (tùy chọn)",
        option4="Lựa chọn 4 (tùy chọn)",
        option5="Lựa chọn 5 (tùy chọn)"
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: str | None = None,
        option4: str | None = None,
        option5: str | None = None
    ):

        options = [
            option for option in
            [option1, option2, option3, option4, option5]
            if option
        ]

        embed = branded_embed(
            self.bot,
            title=f"📊 {question}",
            color=discord.Color.blurple()
        )

        lines = [
            f"{EMOJIS[index]} **{option}**\n`░░░░░░░░░░` 0 phiếu (0%)"
            for index, option in enumerate(options)
        ]
        embed.description = "\n\n".join(lines)
        embed.set_footer(text="Tổng cộng: 0 phiếu bầu")
        embed.set_author(
            name=f"Tạo bởi {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )

        view = PollView(options)

        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Poll(bot))
