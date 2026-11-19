import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import embed, human_time

COLOR = discord.Color.light_grey()


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _log(self, guild, e):
        log_id = self.bot.config.get("log_channel_id")
        if not log_id:
            return
        ch = guild.get_channel(int(log_id))
        if ch:
            try:
                await ch.send(embed=e)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        e = embed("🗑️ Mesaj silindi", None, COLOR)
        e.add_field(name="Kanal", value=message.channel.mention, inline=True)
        e.add_field(name="Yazar", value=str(message.author), inline=True)
        e.add_field(name="İçerik", value=(message.content or "(boş)")[:1000], inline=False)
        await self._log(message.guild, e)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        e = embed("✏️ Mesaj düzenlendi", None, COLOR)
        e.add_field(name="Kanal", value=before.channel.mention, inline=True)
        e.add_field(name="Yazar", value=str(before.author), inline=True)
        e.add_field(name="Önce", value=(before.content or "(boş)")[:600], inline=False)
        e.add_field(name="Sonra", value=(after.content or "(boş)")[:600], inline=False)
        await self._log(before.guild, e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        e = embed("➡️ Üye katıldı", f"{member.mention} — {member}", discord.Color.green())
        e.add_field(name="Hesap oluşturulma", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        e.add_field(name="Toplam üye", value=str(member.guild.member_count), inline=True)
        await self._log(member.guild, e)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        e = embed("⬅️ Üye ayrıldı", f"{member} ({member.id})", discord.Color.orange())
        await self._log(member.guild, e)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            added = [r.name for r in after.roles if r not in before.roles]
            removed = [r.name for r in before.roles if r not in after.roles]
            if added or removed:
                e = embed("🎭 Rol değişikliği", f"{before.mention}", COLOR)
                if added:
                    e.add_field(name="Eklenen", value=", ".join(added), inline=True)
                if removed:
                    e.add_field(name="Kaldırılan", value=", ".join(removed), inline=True)
                await self._log(before.guild, e)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        e = embed("📁 Kanal oluşturuldu", f"{channel.mention} ({channel.type})", COLOR)
        await self._log(channel.guild, e)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        e = embed("🗑️ Kanal silindi", f"#{channel.name} ({channel.type})", COLOR)
        await self._log(channel.guild, e)

    @commands.hybrid_command(name="stats", description="Sunucu istatistiklerini gosterir.")
    async def stats(self, ctx):
        g = ctx.guild
        e = embed(f"📊 {g.name} İstatistikleri")
        e.set_thumbnail(url=g.icon.url if g.icon else ctx.me.display_avatar.url)
        e.add_field(name="Üye", value=str(g.member_count), inline=True)
        e.add_field(name="Kanal", value=str(len(g.channels)), inline=True)
        e.add_field(name="Rol", value=str(len(g.roles)), inline=True)
        e.add_field(name="Kuruluş", value=g.created_at.strftime("%Y-%m-%d"), inline=True)
        e.add_field(name="Sahip", value=str(g.owner), inline=True)
        e.add_field(name="Boost", value=str(g.premium_subscription_count), inline=True)
        e.add_field(name="Bot açık süre", value=human_time((discord.utils.utcnow() - self.bot.start_time).total_seconds()), inline=False)
        await ctx.send(embed=e)

    @commands.hybrid_command(name="uptime", description="Botun calisma suresini gosterir.")
    async def uptime(self, ctx):
        delta = discord.utils.utcnow() - self.bot.start_time
        await ctx.send(embed=embed("⏱️ Çalışma süresi", human_time(delta.total_seconds())))


async def setup(bot):
    await bot.add_cog(Logging(bot))
