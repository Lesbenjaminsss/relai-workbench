import asyncio
import os
import shutil
from collections import defaultdict

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands

from utils.helpers import embed, error, success

YT_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
    "default_search": "ytsearch",
}


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = defaultdict(list)
        self.volumes = defaultdict(lambda: 0.5)

    def _ffmpeg(self):
        configured = self.bot.config.get("music", {}).get("ffmpeg_path")
        if configured and os.path.exists(configured):
            return configured
        found = shutil.which("ffmpeg")
        if found:
            return found
        for p in [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        ]:
            if os.path.exists(p):
                return p
        return "ffmpeg"

    async def _get_audio(self, query):
        loop = asyncio.get_event_loop()

        def extract():
            with yt_dlp.YoutubeDL(YT_OPTIONS) as ydl:
                return ydl.extract_info(query, download=False)

        return await loop.run_in_executor(None, extract)

    async def _play_next(self, guild):
        q = self.queues[guild.id]
        vc = guild.voice_client
        if not vc or not q:
            return
        info, requested_by = q.pop(0)
        url = info.get("url")
        if not url:
            return await self._play_next(guild)

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(url, executable=self._ffmpeg(), before_args="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"),
            volume=self.volumes[guild.id],
        )

        def after(err):
            if err:
                print(f"[MUSIC] FFmpeg hatasi: {err}")
            asyncio.run_coroutine_threadsafe(self._play_next(guild), self.bot.loop)

        vc.play(source, after=after)
        title = info.get("title", "Bilinmeyen")
        ch = guild.text_channels[0]
        try:
            await ch.send(embed=success("Şimdi çalıyor", f"**{title}**\nİsteyen: {requested_by.mention if requested_by else 'Bilinmeyen'}"))
        except Exception:
            pass

    @commands.hybrid_command(name="join", description="Sesli kanala katilir.")
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send(embed=error("Hata", "Önce bir sesli kanala katılın."))
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(embed=success("Bağlandı", f"**{channel.name}** kanalına katıldım."))

    @commands.hybrid_command(name="leave", description="Sesli kanaldan ayrilir.")
    async def leave(self, ctx):
        if not ctx.voice_client:
            return await ctx.send(embed=error("Hata", "Bir sesli kanalda değilim."))
        self.queues[ctx.guild.id].clear()
        await ctx.voice_client.disconnect()
        await ctx.send(embed=success("Ayrıldı", "Sesli kanaldan ayrıldım."))

    @commands.hybrid_command(name="play", description="Sarki calar veya kuyruga ekler.")
    @app_commands.describe(sorgu="Şarkı adı veya YouTube URL")
    async def play(self, ctx, *, sorgu: str):
        if not ctx.author.voice:
            return await ctx.send(embed=error("Hata", "Önce bir sesli kanala katılın."))
        await ctx.defer()
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()

        try:
            info = await self._get_audio(sorgu)
        except Exception as exc:
            return await ctx.send(embed=error("Arama hatası", str(exc)[:500]))

        entries = info.get("entries", [info])
        for entry in entries:
            if entry:
                self.queues[ctx.guild.id].append((entry, ctx.author))

        if info.get("entries"):
            title = f"{len(entries)} şarkı"
        else:
            title = info.get("title", "Bilinmeyen")

        await ctx.send(embed=success("Kuyruğa eklendi", f"**{title}**"))
        if not ctx.voice_client.is_playing():
            await self._play_next(ctx.guild)

    @commands.hybrid_command(name="pause", description="Sarkiyi duraklatir.")
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send(embed=success("Duraklatıldı", "Müzik duraklatıldı."))
        else:
            await ctx.send(embed=error("Hata", "Çalan müzik yok."))

    @commands.hybrid_command(name="resume", description="Sarkiyi devam ettirir.")
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send(embed=success("Devam", "Müzik devam ediyor."))
        else:
            await ctx.send(embed=error("Hata", "Duraklatılmış müzik yok."))

    @commands.hybrid_command(name="stop", description="Muzigi durdurur ve kuyrugu temizler.")
    async def stop(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.stop()
        self.queues[ctx.guild.id].clear()
        await ctx.send(embed=success("Durdu", "Müzik durduruldu, kuyruk temizlendi."))

    @commands.hybrid_command(name="skip", description="Sonraki sarkiya gecer.")
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send(embed=success("Atlandı", "Sonraki şarkıya geçildi."))
        else:
            await ctx.send(embed=error("Hata", "Çalan müzik yok."))

    @commands.hybrid_command(name="queue", description="Muzik kuyrugunu gosterir.")
    async def queue(self, ctx):
        q = self.queues[ctx.guild.id]
        if not q:
            return await ctx.send(embed=embed("🎵 Kuyruk", "Kuyruk boş."))
        lines = [f"**{i}.** {info.get('title', 'Bilinmeyen')}" for i, (info, _) in enumerate(q[:15], 1)]
        await ctx.send(embed=embed("🎵 Müzik Kuyruğu", "\n".join(lines)))

    @commands.hybrid_command(name="volume", description="Ses seviyesini ayarlar (0-100).")
    async def volume(self, ctx, seviye: int):
        if seviye < 0 or seviye > 100:
            return await ctx.send(embed=error("Hata", "0-100 arası bir değer girin."))
        self.volumes[ctx.guild.id] = seviye / 100
        if ctx.voice_client and ctx.voice_client.source and hasattr(ctx.voice_client.source, "volume"):
            ctx.voice_client.source.volume = seviye / 100
        await ctx.send(embed=success("Ses", f"Ses seviyesi %{seviye} olarak ayarlandı."))


async def setup(bot):
    await bot.add_cog(Music(bot))
