import asyncio
import os
import sys

import discord
from discord.ext import commands

from utils.db import Database
from utils.helpers import load_config, error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
cfg = load_config(CONFIG_PATH)

intents = discord.Intents.all()
intents.message_content = True
intents.members = True
intents.presences = True


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(cfg.get("command_prefix", "!")),
            intents=intents,
            help_command=None,
            description="Kapsamli Discord otomasyon botu",
        )
        self.config = cfg
        self.db = Database(os.path.join(BASE_DIR, "data", "bot.db"))
        self.start_time = discord.utils.utcnow()

    async def setup_hook(self):
        cogs = [
            "cogs.moderation",
            "cogs.welcome",
            "cogs.levels",
            "cogs.economy",
            "cogs.tickets",
            "cogs.music",
            "cogs.logging",
            "cogs.fun",
            "cogs.ai",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"[COG] Yuklendi: {cog}")
            except Exception as exc:
                print(f"[COG] HATA {cog}: {exc}")

        # Kalici (persistent) gorusunleri geri yukle
        try:
            from cogs.tickets import TicketCloseView, TicketPanelView

            self.add_view(TicketPanelView(self))
            c = self.db.conn.cursor()
            c.execute("SELECT channel_id FROM tickets WHERE status = 'open'")
            for row in c.fetchall():
                self.add_view(TicketCloseView(self, row["channel_id"]))
        except Exception as exc:
            print(f"[VIEW] Ticket view hatasi: {exc}")

        try:
            from cogs.welcome import RoleMenuView

            for panel in self.db.get_panels("rolemenu:"):
                role_ids = panel.get("data", {}).get("roles", [])
                self.add_view(
                    RoleMenuView(self, int(panel["message_id"]), role_ids)
                )
        except Exception as exc:
            print(f"[VIEW] Role menu view hatasi: {exc}")

    async def on_ready(self):
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} sunucu | /help",
            )
        )
        try:
            synced = await self.tree.sync()
            print(f"[READY] {self.user} | {len(synced)} slash komut senkronize edildi.")
        except Exception as exc:
            print(f"[READY] Sync hatasi: {exc}")
        print(f"[READY] {self.user} (ID: {self.user.id}) hazir.")

    async def on_command_error(self, ctx, exc):
        if isinstance(exc, commands.CommandNotFound):
            return
        if isinstance(exc, commands.MissingPermissions):
            return await ctx.send(embed=error("Yetki yok", "Bu komut için izniniz yok."))
        if isinstance(exc, commands.NotOwner):
            return await ctx.send(embed=error("Yetki yok", "Sadece bot sahibi kullanabilir."))
        if isinstance(exc, commands.CommandOnCooldown):
            return await ctx.send(
                embed=error("Bekleme süresi", f"Tekrar denemek için {exc.retry_after:.1f} saniye bekleyin.")
            )
        await ctx.send(embed=error("Hata", str(exc)[:1000]))

    async def on_tree_error(self, interaction, command, exc):
        e = error("Komut hatası", str(exc)[:1000])
        if interaction.response.is_done():
            await interaction.followup.send(embed=e, ephemeral=True)
        else:
            await interaction.response.send_message(embed=e, ephemeral=True)


def main():
    token = cfg.get("token", "")
    if not token or token.startswith("PASTE_"):
        print("=" * 60)
        print("HATA: config.json icine bot token'inizi yazin!")
        print("Dosya: " + CONFIG_PATH)
        print("Token almak icin: https://discord.com/developers/applications")
        print("=" * 60)
        sys.exit(1)

    bot = Bot()
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("HATA: Token gecersiz. discord.com/developers adresinden yeni token alin.")
        sys.exit(1)


if __name__ == "__main__":
    main()
