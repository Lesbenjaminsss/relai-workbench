import json

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import embed, error, success, save_config

FALLBACK = [
    "Şu an bir API anahtarı tanımlı değil, bu yüzden kısa bir yerel yanıt veriyorum. "
    "Daha iyi cevaplar için config.json içine `ai_api_key` ekleyin.",
]


class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _ask_api(self, soru):
        key = self.bot.config.get("ai_api_key")
        if not key:
            return FALLBACK[0]
        model = self.bot.config.get("ai_model", "gpt-4o-mini")
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Sen yardımcı, samimi ve kısa cevap veren bir Discord botusun. Türkçe cevap ver."},
                {"role": "user", "content": soru},
            ],
            "max_tokens": 500,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as r:
                    data = await r.json()
                    if r.status != 200:
                        return f"API hatası ({r.status}): {str(data)[:300]}"
                    return data["choices"][0]["message"]["content"]
        except Exception as exc:
            return f"API'ye ulaşılamadı: {exc}"

    @commands.hybrid_command(name="ask", description="Yapay zekaya soru sorar.")
    @app_commands.describe(soru="Sorunuz")
    async def ask(self, ctx, *, soru: str):
        await ctx.defer()
        cevap = await self._ask_api(soru)
        e = embed("🤖 Yapay Zeka", cevap[:1900])
        e.set_footer(text=f"İsteyen: {ctx.author}")
        await ctx.send(embed=e)

    @commands.hybrid_command(name="ai-channel", description="Bu kanali AI sohbetine acar/kapatir.")
    @commands.has_permissions(manage_channels=True)
    async def ai_channel(self, ctx):
        cfg = self.bot.config
        chans = [int(x) for x in cfg.get("ai_channels", [])]
        if ctx.channel.id in chans:
            chans.remove(ctx.channel.id)
            durum = "kapatıldı"
        else:
            chans.append(ctx.channel.id)
            durum = "açıldı"
        cfg["ai_channels"] = chans
        save_config(cfg)
        await ctx.send(embed=success("AI kanalı", f"{ctx.channel.mention} için AI sohbeti **{durum}**."))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        if message.channel.id not in [int(x) for x in self.bot.config.get("ai_channels", [])]:
            return
        if message.content.startswith(("!", "/")):
            return
        async with message.channel.typing():
            cevap = await self._ask_api(message.content)
        await message.reply(embed=embed("🤖 AI", cevap[:1900]), allowed_mentions=discord.AllowedMentions.none())


async def setup(bot):
    await bot.add_cog(AI(bot))
