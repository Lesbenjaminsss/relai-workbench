import asyncio
import random
import time

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import embed, error, success, human_time

CEVAPLAR = [
    "Evet, kesinlikle.", "Hayır.", "Belki, tekrar dene.", "Kesinlikle hayır.",
    "Şansın iyi görünüyor, evet.", "Soru biraz bulanık, tekrar sor.", "Evet ama emin değilim.",
    "Kader hayır diyor.", "Tabii ki!", "Bana sorarsan hayır.",
]


class PollView(discord.ui.View):
    def __init__(self, soru, secenekler):
        super().__init__(timeout=300)
        self.soru = soru
        self.secenekler = secenekler
        self.oylar = {s: 0 for s in secenekler}
        self.voters = set()

        for s in secenekler[:5]:
            btn = discord.ui.Button(label=s[:80], style=discord.ButtonStyle.primary)
            btn.callback = self._make_callback(s)
            self.add_item(btn)

    def _make_callback(self, secenek):
        async def cb(interaction):
            if interaction.user.id in self.voters:
                return await interaction.response.send_message("Zaten oy verdin.", ephemeral=True)
            self.voters.add(interaction.user.id)
            self.oylar[secenek] += 1
            await interaction.response.send_message(f"Oyun alındı: **{secenek}**", ephemeral=True)
        return cb

    @discord.ui.button(label="Sonuçlar", style=discord.ButtonStyle.success, row=1)
    async def sonuclar(self, interaction, button):
        e = embed("📊 Anket Sonuçları", self.soru)
        for s, n in self.oylar.items():
            e.add_field(name=s, value=f"{n} oy", inline=False)
        await interaction.response.send_message(embed=e)


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="8ball", description="Soruna cevap verir.")
    async def eightball(self, ctx, *, soru: str):
        await ctx.send(embed=embed("🎱 8-Ball", f"**Soru:** {soru}\n**Cevap:** {random.choice(CEVAPLAR)}"))

    @commands.hybrid_command(name="coinflip", description="Yazı tura atar.")
    async def coinflip(self, ctx):
        sonuc = random.choice(["🪙 Yazı", "🪙 Tura"])
        await ctx.send(embed=success("Yazı Tura", f"Sonuç: **{sonuc}**"))

    @commands.hybrid_command(name="dice", description="Zar atar.")
    async def dice(self, ctx, sides: int = 6):
        sides = max(2, min(100, sides))
        await ctx.send(embed=success("🎲 Zar", f"**{random.randint(1, sides)}** ({sides} yüzlü)"))

    @commands.hybrid_command(name="poll", description="Anket olusturur.")
    @app_commands.describe(soru="Anket sorusu", secenekler="Virgülle ayrilmis 2-5 secenek")
    async def poll(self, ctx, soru: str, secenekler: str):
        opts = [s.strip() for s in secenekler.split(",") if s.strip()][:5]
        if len(opts) < 2:
            return await ctx.send(embed=error("Hata", "En az 2 seçenek gerekir."))
        view = PollView(soru, opts)
        e = embed("📊 Anket", f"**{soru}**\n\n" + "\n".join(f"• {o}" for o in opts))
        await ctx.send(embed=e, view=view)

    @commands.hybrid_command(name="giveaway", description="Cekilis baslatir.")
    @app_commands.describe(sure="Sure (dakika)", odul="Odul", kazanan="Kazanan sayisi")
    async def giveaway(self, ctx, sure: int, odul: str, kazanan: int = 1):
        if sure < 1 or kazanan < 1:
            return await ctx.send(embed=error("Hata", "Süre ve kazanan sayısı pozitif olmalı."))
        e = embed("🎉 Çekiliş", f"**Ödül:** {odul}\n**Kazanan:** {kazanan}\n**Bitiş:** {human_time(sure * 60)}")
        e.add_field(name="Katılım", value="🎊 emojiyle tepki verin!", inline=False)
        msg = await ctx.send(embed=e)
        await msg.add_reaction("🎊")
        await ctx.send(embed=success("Başlatıldı", f"Çekiliş {sure} dakika sürecek."), ephemeral=True)

        await asyncio.sleep(min(sure * 60, 3600 * 24))
        try:
            msg = await ctx.channel.fetch_message(msg.id)
            users = []
            for reaction in msg.reactions:
                if str(reaction.emoji) == "🎊":
                    users = [u async for u in reaction.users() if not u.bot]
            if not users:
                return await ctx.send(embed=error("Çekiliş", "Katılımcı yok."))
            winners = random.sample(users, min(kazanan, len(users)))
            mentions = ", ".join(w.mention for w in winners)
            await ctx.send(embed=success("🎉 Çekiliş sonucu", f"**Ödül:** {odul}\n**Kazananlar:** {mentions}"))
        except Exception as exc:
            await ctx.send(embed=error("Çekiliş hatası", str(exc)[:300]))

    @commands.hybrid_command(name="help", description="Tum komutlari gosterir.")
    async def help_cmd(self, ctx):
        e = embed("🤖 Bot Komutları", "Tüm komutlar hem `/komut` hem `!komut` olarak kullanılabilir.")
        kategoriler = {
            "🛡️ Moderasyon": "ban, kick, mute, unmute, warn, warnings, clear, slowmode, lock, unlock, automod",
            "👋 Karşılama": "setupwelcome, reactionrole, rolemenu",
            "📈 Seviye": "rank, leaderboard, setxp",
            "💰 Ekonomi": "balance, daily, work, pay, shop, shopadd, buy, givecoins, rich",
            "🎫 Ticket": "setup-ticket, ticket-kapat",
            "🎵 Müzik": "join, leave, play, pause, resume, stop, skip, queue, volume",
            "📊 Log/İstatistik": "stats, uptime",
            "🎮 Eğlence": "8ball, coinflip, dice, poll, giveaway, help",
            "🤖 Yapay Zeka": "ask, ai-channel",
        }
        for kat, komutlar in kategoriler.items():
            e.add_field(name=kat, value=komutlar, inline=False)
        e.set_footer(text=f"Toplam {len(self.bot.commands)} komut yüklü")
        await ctx.send(embed=e)


async def setup(bot):
    await bot.add_cog(Fun(bot))
