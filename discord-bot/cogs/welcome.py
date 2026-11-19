import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import embed, error, success

ROLE_SELECT_PREFIX = "rolemenu:"


class RoleMenuView(discord.ui.View):
    def __init__(self, bot, message_id, role_ids):
        super().__init__(timeout=None)
        self.bot = bot
        self.message_id = message_id
        self.role_ids = role_ids

        options = []
        for rid in role_ids:
            guild = bot.get_guild(self._guild_id_from_db(message_id))
            role = guild.get_role(int(rid)) if guild else None
            options.append(
                discord.SelectOption(
                    label=role.name if role else f"Rol {rid}",
                    value=str(rid),
                    description="Rolü almak için seçin",
                )
            )

        if options:
            select = discord.ui.Select(
                placeholder="Almak istediginiz rolleri secin",
                min_values=1,
                max_values=min(len(options), 25),
                options=options[:25],
                custom_id=f"{ROLE_SELECT_PREFIX}{message_id}",
            )
            select.callback = self._on_select
            self.add_item(select)

    def _guild_id_from_db(self, message_id):
        for p in self.bot.db.get_panels("rolemenu:"):
            if int(p["message_id"]) == message_id:
                return int(p["guild_id"])
        return 0

    async def _on_select(self, interaction):
        added, removed = [], []
        for value in interaction.data["values"]:
            role = interaction.guild.get_role(int(value))
            if not role:
                continue
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                removed.append(role.name)
            else:
                await interaction.user.add_roles(role)
                added.append(role.name)
        msg = "Rol güncellendi."
        if added:
            msg += "\nEklenen: " + ", ".join(added)
        if removed:
            msg += "\nKaldırılan: " + ", ".join(removed)
        await interaction.response.send_message(embed=success("Roller", msg), ephemeral=True)


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        cfg = self.bot.config
        channel_id = cfg.get("welcome_channel_id")
        role_id = cfg.get("welcome_role_id")

        if role_id:
            role = member.guild.get_role(int(role_id))
            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    pass

        if channel_id:
            channel = member.guild.get_channel(int(channel_id))
            if channel:
                e = embed(
                    "Hoş geldin! 🎉",
                    f"{member.mention}, **{member.guild.name}** sunucusuna katıldı.\n"
                    f"Şu anda sunucuda **{member.guild.member_count}** üye bulunuyor.",
                    discord.Color.green(),
                )
                e.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=e)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        rows = self.bot.db.get_reaction_roles(payload.guild_id, payload.message_id)
        for row in rows:
            if str(row["emoji"]) == str(payload.emoji):
                guild = self.bot.get_guild(payload.guild_id)
                role = guild.get_role(row["role_id"]) if guild else None
                member = guild.get_member(payload.user_id) if guild else None
                if role and member:
                    try:
                        await member.add_roles(role)
                    except discord.Forbidden:
                        pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        rows = self.bot.db.get_reaction_roles(payload.guild_id, payload.message_id)
        for row in rows:
            if str(row["emoji"]) == str(payload.emoji):
                guild = self.bot.get_guild(payload.guild_id)
                role = guild.get_role(row["role_id"]) if guild else None
                member = guild.get_member(payload.user_id) if guild else None
                if role and member:
                    try:
                        await member.remove_roles(role)
                    except discord.Forbidden:
                        pass

    @commands.hybrid_command(name="setupwelcome", description="Karsilama kanalini ve rolunu ayarlar.")
    @commands.has_permissions(administrator=True)
    async def setupwelcome(self, ctx, channel: discord.TextChannel, role: discord.Role = None):
        cfg = self.bot.config
        cfg["welcome_channel_id"] = channel.id
        if role:
            cfg["welcome_role_id"] = role.id
        from utils.helpers import save_config
        save_config(cfg)
        await ctx.send(embed=success("Ayarlandı", f"Karşılama kanalı: {channel.mention}" + (f"\nOtomatik rol: {role.name}" if role else "")))

    @commands.hybrid_command(name="reactionrole", description="Bir mesaja reaksiyon rolu baglar.")
    @app_commands.describe(message_id="Mesaj ID", emoji="Emoji", role="Rol")
    @commands.has_permissions(administrator=True)
    async def reactionrole(self, ctx, message_id: str, emoji: str, role: discord.Role):
        try:
            mid = int(message_id)
        except ValueError:
            return await ctx.send(embed=error("Hata", "Geçerli bir mesaj ID'si girin."))
        self.bot.db.add_reaction_role(ctx.guild.id, mid, emoji, role.id)
        await ctx.send(embed=success("Bağlandı", f"{emoji} → {role.name}"))

    @commands.hybrid_command(name="rolemenu", description="Secilebilir roller menusu olusturur.")
    @commands.has_permissions(administrator=True)
    async def rolemenu(self, ctx, roller: str):
        """Roller: virgülle ayrilmis rol ID'leri veya etiketleri."""
        role_ids = []
        for parca in roller.split(","):
            parca = parca.strip()
            if not parca:
                continue
            rid = parca.replace("<@&", "").replace(">", "")
            if rid.isdigit():
                role_ids.append(int(rid))
        if not role_ids:
            return await ctx.send(embed=error("Hata", "En az bir rol ID'si verin."))

        e = embed("Rol Menüsü", "Aşağıdaki menüden almak istediğiniz rolleri seçin.")
        msg = await ctx.send(embed=e)
        view = RoleMenuView(self.bot, msg.id, role_ids)
        await msg.edit(view=view)
        self.bot.db.set_panel(f"rolemenu:{msg.id}", ctx.guild.id, msg.id, {"roles": role_ids})
        self.bot.add_view(view)
        await ctx.send(embed=success("Oluşturuldu", f"Rol menüsü oluşturuldu: {msg.jump_url}"), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
