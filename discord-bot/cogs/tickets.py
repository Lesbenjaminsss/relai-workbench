import io
import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import embed, error, success, save_config

TICKET_OPEN_ID = "ticket:open"


class TicketCloseView(discord.ui.View):
    def __init__(self, bot, channel_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.channel_id = channel_id

    @discord.ui.button(
        label="Ticket'ı Kapat",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:close",
    )
    async def close(self, interaction, button):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("Ticket kanalı bulunamadı.", ephemeral=True)
        ticket = self.bot.db.get_ticket(self.channel_id)
        if not ticket or ticket["status"] == "closed":
            return await interaction.response.send_message("Bu ticket zaten kapalı.", ephemeral=True)

        await interaction.response.defer()

        # Transcript olustur
        lines = [f"# Ticket transcript - #{channel.name}", f"Açan: <@{ticket['user_id']}>", ""]
        async for msg in channel.history(limit=500, oldest_first=True):
            lines.append(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M')}] {msg.author}: {msg.content}")
        transcript = "\n".join(lines)

        log_id = self.bot.config.get("log_channel_id")
        if log_id:
            log = interaction.guild.get_channel(int(log_id))
            if log:
                f = discord.File(io.StringIO(transcript), filename=f"ticket-{self.channel_id}.txt")
                await log.send(embed=embed("Ticket kapatıldı", f"#{channel.name} — <@{ticket['user_id']}>"), file=f)

        self.bot.db.close_ticket(self.channel_id)
        await channel.delete(reason="Ticket kapatıldı")


class TicketPanelView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="🎫 Ticket Aç",
        style=discord.ButtonStyle.green,
        custom_id=TICKET_OPEN_ID,
    )
    async def open_ticket(self, interaction, button):
        guild = interaction.guild
        if not guild:
            return
        category_id = self.bot.config.get("ticket_category_id")
        category = guild.get_channel(int(category_id)) if category_id else None

        existing = None
        for ch in guild.text_channels:
            t = self.bot.db.get_ticket(ch.id)
            if t and t["status"] == "open" and t["user_id"] == interaction.user.id:
                existing = ch
                break
        if existing:
            return await interaction.response.send_message(
                f"Zaten açık bir ticket'in var: {existing.mention}", ephemeral=True
            )

        name = f"ticket-{interaction.user.name}-{interaction.user.discriminator}"[:90]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        ch = await guild.create_text_channel(name, overwrites=overwrites, category=category)
        self.bot.db.add_ticket(ch.id, guild.id, interaction.user.id)
        self.bot.add_view(TicketCloseView(self.bot, ch.id))

        e = embed("Ticket oluşturuldu", f"Merhaba {interaction.user.mention}, destek ekibi kısa süre içinde seninle ilgilenecek.\nKapatmak için aşağıdaki butonu kullan.")
        await ch.send(e, view=TicketCloseView(self.bot, ch.id))
        await interaction.response.send_message(f"Ticket oluşturuldu: {ch.mention}", ephemeral=True)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setup-ticket", description="Ticket panelini kurar.")
    @commands.has_permissions(administrator=True)
    async def setup_ticket(self, ctx, category: discord.CategoryChannel = None):
        if category:
            self.bot.config["ticket_category_id"] = category.id
            save_config(self.bot.config)

        view = TicketPanelView(self.bot)
        msg = await ctx.send(
            embed=embed("🎫 Destek Sistemi", "Yardıma mı ihtiyacınız var? Aşağıdaki butona basarak ticket açın."),
            view=view,
        )
        self.bot.db.set_panel("ticket:panel", ctx.guild.id, msg.id, {})
        self.bot.add_view(view)
        await ctx.send(embed=success("Kuruldu", "Ticket paneli oluşturuldu."), ephemeral=True)

    @commands.hybrid_command(name="ticket-kapat", description="Mevcut ticketi kapatir.")
    async def ticket_close(self, ctx):
        t = self.bot.db.get_ticket(ctx.channel.id)
        if not t or t["status"] == "closed":
            return await ctx.send(embed=error("Hata", "Bu kanal bir ticket değil."))
        view = TicketCloseView(self.bot, ctx.channel.id)
        await ctx.send(embed=embed("Kapat", "Ticket'i kapatmak için butona basın."), view=view)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
