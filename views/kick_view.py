import discord

from utils.logger import send_log
from utils.embeds import branded_embed


class KickApprovalView(discord.ui.View):

    def __init__(
        self,
        target: discord.Member,
        requester: discord.Member,
        reason: str,
        timeout: int = 300
    ):
        super().__init__(timeout=timeout)

        self.target = target
        self.requester = requester
        self.reason = reason

    # =====================================================
    # KIỂM TRA CHỦ SERVER
    # =====================================================

    async def check_owner(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if interaction.guild is None:
            return False

        # CHỈ guild.owner mới được duyệt
        if interaction.user.id != interaction.guild.owner_id:

            await interaction.response.send_message(
                "❌ Chỉ **chủ server** mới có thể "
                "duyệt hoặc từ chối yêu cầu này.",
                ephemeral=True
            )

            return False

        return True

    # =====================================================
    # NÚT DUYỆT
    # =====================================================

    @discord.ui.button(
        label="Duyệt Kick",
        emoji="✅",
        style=discord.ButtonStyle.success
    )
    async def approve(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await self.check_owner(interaction):
            return

        guild = interaction.guild

        if guild is None:
            return

        # Kiểm tra target còn trong server
        member = guild.get_member(
            self.target.id
        )

        if member is None:

            await interaction.response.edit_message(
                content="⚠️ Thành viên này không còn trong server.",
                embed=None,
                view=None
            )

            self.stop()
            return

        # Kiểm tra bot còn đủ quyền
        me = guild.me

        if me is None:
            await interaction.response.send_message(
                "❌ Không thể xác định Astrix.",
                ephemeral=True
            )
            return

        if member.id == guild.owner_id:

            await interaction.response.send_message(
                "❌ Không thể kick chủ server.",
                ephemeral=True
            )
            return

        if member.top_role >= me.top_role:

            await interaction.response.send_message(
                "❌ Astrix không thể kick thành viên này "
                "vì role của họ cao hơn hoặc bằng role bot.",
                ephemeral=True
            )
            return

        try:

            await member.kick(
                reason=(
                    f"{self.reason} | "
                    f"Yêu cầu bởi {self.requester} | "
                    f"Duyệt bởi {interaction.user}"
                )
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Astrix không có quyền kick thành viên này.",
                ephemeral=True
            )
            return

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Discord từ chối yêu cầu kick.",
                ephemeral=True
            )
            return

        # -------------------------------------------------
        # THÔNG BÁO ĐÃ DUYỆT
        # -------------------------------------------------

        embed = branded_embed(
            interaction.client,
            title="✅ Kick đã được duyệt",
            color=discord.Color.green()
        )

        embed.add_field(
            name="👤 Thành viên",
            value=self.target.mention,
            inline=False
        )

        embed.add_field(
            name="📝 Người yêu cầu",
            value=self.requester.mention,
            inline=True
        )

        embed.add_field(
            name="👑 Người duyệt",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="📋 Lý do",
            value=self.reason,
            inline=False
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None
        )

        await send_log(
            interaction.client,
            guild,
            title="✅ Kick đã được duyệt",
            description=(
                f"**Thành viên:** {self.target.mention} (`{self.target.id}`)\n"
                f"**Người yêu cầu:** {self.requester.mention}\n"
                f"**Người duyệt:** {interaction.user.mention}\n"
                f"**Lý do:** {self.reason}"
            ),
            color=discord.Color.green()
        )

        self.stop()

    # =====================================================
    # NÚT TỪ CHỐI
    # =====================================================

    @discord.ui.button(
        label="Từ chối",
        emoji="❌",
        style=discord.ButtonStyle.danger
    )
    async def reject(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await self.check_owner(interaction):
            return

        embed = branded_embed(
            interaction.client,
            title="❌ Yêu cầu Kick bị từ chối",
            color=discord.Color.red()
        )

        embed.add_field(
            name="👤 Thành viên",
            value=self.target.mention,
            inline=False
        )

        embed.add_field(
            name="📝 Người yêu cầu",
            value=self.requester.mention,
            inline=True
        )

        embed.add_field(
            name="👑 Người từ chối",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="📋 Lý do ban đầu",
            value=self.reason,
            inline=False
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None
        )

        await send_log(
            interaction.client,
            interaction.guild,
            title="❌ Yêu cầu kick bị từ chối",
            description=(
                f"**Thành viên:** {self.target.mention} (`{self.target.id}`)\n"
                f"**Người yêu cầu:** {self.requester.mention}\n"
                f"**Người từ chối:** {interaction.user.mention}"
            ),
            color=discord.Color.red()
        )

        self.stop()

    # =====================================================
    # HẾT THỜI GIAN
    # =====================================================

    async def on_timeout(self):

        for item in self.children:

            item.disabled = True
