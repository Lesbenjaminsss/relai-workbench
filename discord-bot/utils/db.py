import os
import json
import sqlite3
import time


class Database:
    """Basit SQLite tabanli kalici veri katmani."""

    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                guild_id   INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                xp         INTEGER DEFAULT 0,
                level      INTEGER DEFAULT 0,
                coins      INTEGER DEFAULT 0,
                warnings   INTEGER DEFAULT 0,
                last_xp    INTEGER DEFAULT 0,
                last_daily INTEGER DEFAULT 0,
                last_work  INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                guild_id INTEGER PRIMARY KEY,
                data     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tickets (
                channel_id INTEGER PRIMARY KEY,
                guild_id   INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                opened_at  INTEGER NOT NULL,
                status     TEXT DEFAULT 'open'
            );

            CREATE TABLE IF NOT EXISTS panels (
                name      TEXT PRIMARY KEY,
                guild_id  INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                data      TEXT
            );

            CREATE TABLE IF NOT EXISTS reaction_roles (
                guild_id  INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                emoji     TEXT NOT NULL,
                role_id   INTEGER NOT NULL,
                PRIMARY KEY (guild_id, message_id, emoji)
            );

            CREATE TABLE IF NOT EXISTS economy_shop (
                guild_id INTEGER NOT NULL,
                name     TEXT NOT NULL,
                price    INTEGER NOT NULL,
                PRIMARY KEY (guild_id, name)
            );
            """
        )
        self.conn.commit()

    # ---------- kullanicilar ----------
    def user(self, guild_id, user_id):
        c = self.conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO users (guild_id, user_id) VALUES (?, ?)",
            (guild_id, user_id),
        )
        c.execute(
            "SELECT * FROM users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        return dict(c.fetchone())

    def update_user(self, guild_id, user_id, **fields):
        if not fields:
            return
        c = self.conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO users (guild_id, user_id) VALUES (?, ?)",
            (guild_id, user_id),
        )
        keys = list(fields.keys())
        sets = ", ".join("{}=?".format(k) for k in keys)
        values = [fields[k] for k in keys] + [guild_id, user_id]
        c.execute(
            "UPDATE users SET {} WHERE guild_id = ? AND user_id = ?".format(sets),
            values,
        )
        self.conn.commit()

    def add_xp(self, guild_id, user_id, amount):
        u = self.user(guild_id, user_id)
        old_level = u["level"]
        xp = u["xp"] + amount
        level = int(xp ** 0.5 / 10)
        if level < 0:
            level = 0
        self.update_user(guild_id, user_id, xp=xp, level=level)
        return level > old_level, level

    def top_xp(self, guild_id, limit=10):
        c = self.conn.cursor()
        c.execute(
            "SELECT user_id, xp, level FROM users WHERE guild_id = ? ORDER BY xp DESC LIMIT ?",
            (guild_id, limit),
        )
        return [dict(r) for r in c.fetchall()]

    def top_coins(self, guild_id, limit=10):
        c = self.conn.cursor()
        c.execute(
            "SELECT user_id, coins FROM users WHERE guild_id = ? ORDER BY coins DESC LIMIT ?",
            (guild_id, limit),
        )
        return [dict(r) for r in c.fetchall()]

    # ---------- ayarlar ----------
    def get_settings(self, guild_id):
        c = self.conn.cursor()
        c.execute("SELECT data FROM settings WHERE guild_id = ?", (guild_id,))
        row = c.fetchone()
        if row:
            try:
                return json.loads(row["data"])
            except Exception:
                return {}
        return {}

    def set_settings(self, guild_id, data):
        c = self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO settings (guild_id, data) VALUES (?, ?)",
            (guild_id, json.dumps(data)),
        )
        self.conn.commit()

    # ---------- ticket ----------
    def add_ticket(self, channel_id, guild_id, user_id):
        c = self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO tickets (channel_id, guild_id, user_id, opened_at, status) VALUES (?,?,?,?,'open')",
            (channel_id, guild_id, user_id, int(time.time())),
        )
        self.conn.commit()

    def get_ticket(self, channel_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM tickets WHERE channel_id = ?", (channel_id,))
        r = c.fetchone()
        return dict(r) if r else None

    def close_ticket(self, channel_id):
        c = self.conn.cursor()
        c.execute("UPDATE tickets SET status='closed' WHERE channel_id = ?", (channel_id,))
        self.conn.commit()

    # ---------- paneller ----------
    def set_panel(self, name, guild_id, message_id, data=None):
        c = self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO panels (name, guild_id, message_id, data) VALUES (?,?,?,?)",
            (name, guild_id, message_id, json.dumps(data or {})),
        )
        self.conn.commit()

    def get_panels(self, prefix=None):
        c = self.conn.cursor()
        if prefix:
            c.execute("SELECT * FROM panels WHERE name LIKE ?", (prefix + "%",))
        else:
            c.execute("SELECT * FROM panels")
        return [dict(r) for r in c.fetchall()]

    def delete_panel(self, name):
        self.conn.cursor().execute("DELETE FROM panels WHERE name = ?", (name,))
        self.conn.commit()

    # ---------- reaction roller ----------
    def add_reaction_role(self, guild_id, message_id, emoji, role_id):
        c = self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO reaction_roles (guild_id, message_id, emoji, role_id) VALUES (?,?,?,?)",
            (guild_id, message_id, str(emoji), role_id),
        )
        self.conn.commit()

    def get_reaction_roles(self, guild_id, message_id):
        c = self.conn.cursor()
        c.execute(
            "SELECT * FROM reaction_roles WHERE guild_id = ? AND message_id = ?",
            (guild_id, message_id),
        )
        return [dict(r) for r in c.fetchall()]

    # ---------- magaza ----------
    def add_shop_item(self, guild_id, name, price):
        c = self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO economy_shop (guild_id, name, price) VALUES (?,?,?)",
            (guild_id, name, price),
        )
        self.conn.commit()

    def get_shop(self, guild_id):
        c = self.conn.cursor()
        c.execute("SELECT name, price FROM economy_shop WHERE guild_id = ?", (guild_id,))
        return [dict(r) for r in c.fetchall()]

    def remove_shop_item(self, guild_id, name):
        self.conn.cursor().execute(
            "DELETE FROM economy_shop WHERE guild_id = ? AND name = ?", (guild_id, name)
        )
        self.conn.commit()
