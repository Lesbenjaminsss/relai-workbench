import json
import os

import discord


def load_config(path="config.json"):
    # utf-8-sig: PowerShell'in ekledigi BOM'u da tolere eder
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_config(cfg, path="config.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def embed(title=None, description=None, color=None, **kwargs):
    e = discord.Embed(
        title=title,
        description=description,
        color=color or discord.Color.blurple(),
        **kwargs,
    )
    return e


def success(title, description=None):
    return embed(title, description, discord.Color.green())


def error(title, description=None):
    return embed(title, description, discord.Color.red())


def warn(title, description=None):
    return embed(title, description, discord.Color.orange())


def level_from_xp(xp):
    return max(0, int((xp ** 0.5) / 10))


def xp_for_level(level):
    return (level * 10) ** 2


def human_time(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}g")
    if hours:
        parts.append(f"{hours}s")
    if minutes:
        parts.append(f"{minutes}dk")
    if seconds or not parts:
        parts.append(f"{seconds}sn")
    return " ".join(parts)


def is_admin(member):
    return member.guild_permissions.administrator
