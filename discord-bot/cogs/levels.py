import time

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import embed, error, success, xp_for_level

XP_PER_MESSAGE = 15
XP_COOLDOWN = 45


class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        uid = (message.guild.id, message.author.id)
        u = self.bot.db.user(*uid)
        now = time.time()
        if now - u["last_xp"] < XP_COOLDOWN:
            return

        self.bot.db.update_user(*uid, last_xp=int(now))
        leveled, level = self.bot.db.add_xp(*uid, XP_PER_MESSAGE)

        if leveled:
            rewards = self.bot.config.get("level_role_rewards", {})
            role_id = rewards.get(str(level))
            if role_id:
                role = message.guild.get_role(int(role_id))
                if role:
                    try:
                        await message.author.add_roles(role)
                        await message.channel.send(
                            embed=success("Seviye ödülü!", f"{message.author.mention}, {role.name} rolünü kazandın!"),
                            delete_after=10,
                        )
                    except discord.Forbidden:
                        pass
            else:
                await message.channel.send(
                    embed=success("Seviye atladın!", f"{message.author.mention} artık **Seviye {level}**!"),
                    delete_after=8,
                )

    @commands.hybrid_command(name="rank", description="Seviye ve XP bilgilerini gosterir.")
    async def rank(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        u = self.bot.db.user(ctx.guild.id, member.id)
        next_xp = xp_for_level(u["level"] + 1)
        e = embed("Kullanıcı Sıralaması")
        e.set_author(name=str(member), icon_url=member.display_avatar.url)
        e.add_field(name="Seviye", value=str(u["level"]), inline=True)
        e.add_field(name="XP", value=str(u["xp"]), inline=True)
        e.add_field(name="Sonraki seviye", value=f"{next_xp} XP", inline=True)
        e.add_field(name="Uyarı", value=str(u["warnings"]), inline=True)
        progress = min(100, int(u["xp"] / max(1, next_xp) * 100)) if next_xp else 100
        e.add_field(name="İlerleme", value=f"`[{'█' * (progress // 5)}{'░' * (20 - progress // 5)}]` %{progress}", inline=False)
        await ctx.send(embed=e)

    @commands.hybrid_command(name="leaderboard", aliases=["lb"], description="En yuksek seviyeli uyeleri gosterir.")
    async def leaderboard(self, ctx):
        rows = self.bot.db.top_xp(ctx.guild.id, 10)
        if not rows:
            return await ctx.send(embed=error("Bos", "Henüz veri yok."))
        lines = []
        for i, r in enumerate(rows, 1):
            m = ctx.guild.get_member(r["user_id"])
            name = m.display_name if m else f"Kullanıcı {r['user_id']}"
            lines.append(f"**{i}.** {name} — Seviye {r['level']} ({r['xp']} XP)")
        e = embed("🏆 Seviye Sıralaması", "\n".join(lines))
        await ctx.send(embed=e)

    @commands.hybrid_command(name="setxp", description="Bir uyeye XP ekler (yonetici).")
    @commands.has_permissions(administrator=True)
    async def setxp(self, ctx, member: discord.Member, amount: int):
        self.bot.db.add_xp(ctx.guild.id, member.id, amount)
        await ctx.send(embed=success("XP eklendi", f"{member} icin {amount} XP eklendi."))


async def setup(bot):
    await bot.add_cog(Levels(bot))
