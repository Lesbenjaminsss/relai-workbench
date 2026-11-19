import re
import time
from collections import defaultdict

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import embed, error, success, warn, is_admin, human_time

LINK_RE = re.compile(r"https?://(?!discord\.com|discord\.gg|cdn\.discordapp\.com)\S+", re.I)
INVITE_RE = re.compile(r"(discord\.gg/|discord\.com/invite/)\S+", re.I)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam = defaultdict(list)

    # ---------------- komutlar ----------------
    @commands.hybrid_command(name="ban", description="Bir uyeyi sunucudan yasaklar.")
    @app_commands.describe(member="Yasaklanacak uye", reason="Sebep")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Sebep belirtilmedi"):
        if member == ctx.author:
            return await ctx.send(embed=error("Hata", "Kendinizi yasaklayamazsiniz."))
        if is_admin(member):
            return await ctx.send(embed=error("Hata", "Bir yoneticinin banini kaldiramazsiniz."))
        await member.ban(reason=f"{ctx.author}: {reason}")
        await ctx.send(embed=success("Uye yasaklandi", f"{member} sunucudan yasaklandi.\nSebep: {reason}"))

    @commands.hybrid_command(name="kick", description="Bir uyeyi sunucudan atar.")
    @app_commands.describe(member="Atilacak uye", reason="Sebep")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Sebep belirtilmedi"):
        if member == ctx.author:
            return await ctx.send(embed=error("Hata", "Kendinizi atamazsiniz."))
        await member.kick(reason=f"{ctx.author}: {reason}")
        await ctx.send(embed=success("Uye atildi", f"{member} sunucudan atildi.\nSebep: {reason}"))

    @commands.hybrid_command(name="mute", description="Bir uyeyi belirli sure sessize alir.")
    @app_commands.describe(member="Uye", minutes="Sure (dakika)", reason="Sebep")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, minutes: int = 10, *, reason: str = "Sebep belirtilmedi"):
        until = discord.utils.utcnow() + __import__("datetime").timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        await ctx.send(embed=success("Sessize alindi", f"{member} {minutes} dakika sessize alindi.\nSebep: {reason}"))

    @commands.hybrid_command(name="unmute", description="Bir uyeyi sessizlikten cikarir.")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        await member.timeout(None)
        await ctx.send(embed=success("Sessizlik kaldirildi", f"{member} artik konusabilir."))

    @commands.hybrid_command(name="warn", description="Bir uyeyi uyarir.")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "Sebep belirtilmedi"):
        self.bot.db.update_user(ctx.guild.id, member.id, warnings=self.bot.db.user(ctx.guild.id, member.id)["warnings"] + 1)
        try:
            await member.send(embed=warn("Uyari aldınız", f"{ctx.guild.name}: {reason}"))
        except discord.Forbidden:
            pass
        await ctx.send(embed=success("Uyari verildi", f"{member} uyarildi.\nSebep: {reason}"))

    @commands.hybrid_command(name="warnings", description="Bir uyenin uyari sayisini gosterir.")
    async def warnings(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        u = self.bot.db.user(ctx.guild.id, member.id)
        await ctx.send(embed=embed("Uyarilar", f"{member} icin toplam **{u['warnings']}** uyari bulunuyor."))

    @commands.hybrid_command(name="clear", aliases=["purge"], description="Kanalda mesaj siler.")
    @app_commands.describe(amount="Silinecek mesaj sayisi (1-100)")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 10):
        amount = max(1, min(100, amount))
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(embed=success("Temizlendi", f"{len(deleted) - 1} mesaj silindi."))
        await msg.delete(delay=4)

    @commands.hybrid_command(name="slowmode", description="Kanalava yavas mod ayarlar.")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        await ctx.channel.edit(slowmode_delay=max(0, min(21600, seconds)))
        await ctx.send(embed=success("Yavas mod", f"Gecikme {seconds} saniye olarak ayarlandi."))

    @commands.hybrid_command(name="lock", description="Kanali kilitlemes (konusmayi kapatir).")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(embed=warn("Kanal kilitlendi", "Artik mesaj gonderilemiyor."))

    @commands.hybrid_command(name="unlock", description="Kilidi acar.")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
        await ctx.send(embed=success("Kilit acildi", "Kanal yeniden kullanilabilir."))

    @commands.hybrid_command(name="automod", description="Otomatik moderasyon ayarlarini gosterir.")
    async def automod_info(self, ctx):
        am = self.bot.config.get("automod", {})
        e = embed("AutoMod Ayarlari")
        e.add_field(name="Durum", value="Acik" if am.get("enabled") else "Kapali", inline=True)
        e.add_field(name="Link engelleme", value=str(am.get("block_links")), inline=True)
        e.add_field(name="Davet engelleme", value=str(am.get("block_invites")), inline=True)
        e.add_field(name="Maksimum etiket", value=str(am.get("max_mentions")), inline=True)
        e.add_field(name="Spam siniri", value=str(am.get("spam_limit")), inline=True)
        e.add_field(name="Yasakli kelime", value=str(len(am.get("banned_words", []))), inline=True)
        await ctx.send(embed=e)

    # ---------------- otomatik moderasyon ----------------
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        am = self.bot.config.get("automod", {})
        if not am.get("enabled", True):
            return
        if is_admin(message.author):
            return

        content = message.content
        reason = None

        words = [w.lower() for w in am.get("banned_words", []) if w]
        if words and any(w in content.lower() for w in words):
            reason = "Yasakli kelime kullanimi"

        if not reason and am.get("block_links") and LINK_RE.search(content):
            reason = "Izin verilmeyen baglanti"

        if not reason and am.get("block_invites") and INVITE_RE.search(content):
            reason = "Davet baglantisi"

        max_mentions = am.get("max_mentions", 5)
        if not reason and len(message.mentions) > max_mentions:
            reason = "Cok fazla etiket"

        if not reason:
            key = (message.guild.id, message.author.id)
            now = time.time()
            recent = [t for t in self.spam[key] if now - t < 5]
            recent.append(now)
            self.spam[key] = recent
            if len(recent) >= am.get("spam_limit", 5):
                reason = "Spam / hizli mesaj"
                self.spam[key] = []

        if reason:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            try:
                await message.channel.send(
                    embed=warn("AutoMod", f"{message.author.mention}, mesajiniz silindi.\nSebep: {reason}"),
                    delete_after=6,
                )
            except discord.Forbidden:
                pass
            u = self.bot.db.user(message.guild.id, message.author.id)
            self.bot.db.update_user(message.guild.id, message.author.id, warnings=u["warnings"] + 1)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
