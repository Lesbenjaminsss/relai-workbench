import random
import time

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import embed, error, success, human_time

DAILY_COOLDOWN = 86400
WORK_COOLDOWN = 300


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _coins(self, guild_id, user_id):
        return self.bot.db.user(guild_id, user_id)["coins"]

    @commands.hybrid_command(name="balance", aliases=["bal"], description="Bakiyeni gosterir.")
    async def balance(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        coins = self._coins(ctx.guild.id, member.id)
        await ctx.send(embed=embed("💰 Cüzdan", f"{member.mention} **{coins}** paraya sahip."))

    @commands.hybrid_command(name="daily", description="Gunluk para odulu alirsin.")
    async def daily(self, ctx):
        uid = (ctx.guild.id, ctx.author.id)
        u = self.bot.db.user(*uid)
        now = int(time.time())
        kalan = u["last_daily"] + DAILY_COOLDOWN - now
        if kalan > 0:
            return await ctx.send(embed=error("Bekleme süresi", f"Tekrar almak için {human_time(kalan)} bekleyin."))
        miktar = random.randint(100, 250)
        self.bot.db.update_user(*uid, coins=u["coins"] + miktar, last_daily=now)
        await ctx.send(embed=success("Günlük ödül", f"**{miktar}** para kazandın!"))

    @commands.hybrid_command(name="work", description="Calisip para kazanirsin.")
    async def work(self, ctx):
        uid = (ctx.guild.id, ctx.author.id)
        u = self.bot.db.user(*uid)
        now = int(time.time())
        kalan = u["last_work"] + WORK_COOLDOWN - now
        if kalan > 0:
            return await ctx.send(embed=error("Bekleme süresi", f"Tekrar çalışmak için {human_time(kalan)} bekleyin."))
        miktar = random.randint(10, 45)
        self.bot.db.update_user(*uid, coins=u["coins"] + miktar, last_work=now)
        meslek = random.choice(["Kasada çalıştın", "Orman işçisi oldun", "Balık tuttun", "Kuryelik yaptın"])
        await ctx.send(embed=success("İş", f"{meslek}: **+{miktar}** para"))

    @commands.hybrid_command(name="pay", description="Baska bir uyeye para gonderirsin.")
    async def pay(self, ctx, member: discord.Member, amount: int):
        if member == ctx.author:
            return await ctx.send(embed=error("Hata", "Kendine para gönderemezsin."))
        if amount <= 0:
            return await ctx.send(embed=error("Hata", "Tutar pozitif olmalı."))
        my = self._coins(ctx.guild.id, ctx.author.id)
        if my < amount:
            return await ctx.send(embed=error("Yetersiz bakiye", f"Bakiyen: {my}"))
        self.bot.db.update_user(ctx.guild.id, ctx.author.id, coins=my - amount)
        self.bot.db.update_user(ctx.guild.id, member.id, coins=self._coins(ctx.guild.id, member.id) + amount)
        await ctx.send(embed=success("Transfer", f"{ctx.author.mention} → {member.mention}: **{amount}** para"))

    @commands.hybrid_command(name="shop", description="Magazayi gosterir.")
    async def shop(self, ctx):
        items = self.bot.db.get_shop(ctx.guild.id)
        if not items:
            return await ctx.send(embed=embed("🛒 Mağaza", "Henüz ürün yok. Yönetici `/shopadd` ile ürün ekleyebilir."))
        lines = [f"**{i}.** {it['name']} — {it['price']} para" for i, it in enumerate(items, 1)]
        await ctx.send(embed=embed("🛒 Mağaza", "\n".join(lines)))

    @commands.hybrid_command(name="shopadd", description="Magazaya urun ekler (yonetici).")
    @commands.has_permissions(administrator=True)
    async def shopadd(self, ctx, name: str, price: int):
        self.bot.db.add_shop_item(ctx.guild.id, name, price)
        await ctx.send(embed=success("Eklendi", f"**{name}** mağazaya eklendi ({price} para)."))

    @commands.hybrid_command(name="buy", description="Magazadan urun satin alirsin.")
    async def buy(self, ctx, name: str):
        items = {it["name"].lower(): it for it in self.bot.db.get_shop(ctx.guild.id)}
        item = items.get(name.lower())
        if not item:
            return await ctx.send(embed=error("Bulunamadı", "Böyle bir ürün yok."))
        my = self._coins(ctx.guild.id, ctx.author.id)
        if my < item["price"]:
            return await ctx.send(embed=error("Yetersiz bakiye", f"Bakiyen: {my}"))
        self.bot.db.update_user(ctx.guild.id, ctx.author.id, coins=my - item["price"])
        await ctx.send(embed=success("Satın alındı", f"**{item['name']}** satın alındı."))

    @commands.hybrid_command(name="givecoins", description="Bir uyeye para verir (yonetici).")
    @commands.has_permissions(administrator=True)
    async def givecoins(self, ctx, member: discord.Member, amount: int):
        self.bot.db.update_user(ctx.guild.id, member.id, coins=self._coins(ctx.guild.id, member.id) + amount)
        await ctx.send(embed=success("Para verildi", f"{member} -> {amount} para"))

    @commands.hybrid_command(name="rich", description="En zengin uyeleri gosterir.")
    async def rich(self, ctx):
        rows = self.bot.db.top_coins(ctx.guild.id, 10)
        lines = []
        for i, r in enumerate(rows, 1):
            m = ctx.guild.get_member(r["user_id"])
            name = m.display_name if m else f"Kullanıcı {r['user_id']}"
            lines.append(f"**{i}.** {name} — {r['coins']} para")
        await ctx.send(embed=embed("💎 Zenginler", "\n".join(lines) if lines else "Henüz veri yok."))


async def setup(bot):
    await bot.add_cog(Economy(bot))
