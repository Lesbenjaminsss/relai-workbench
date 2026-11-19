import os
import sqlite3
import time

from config import DB_PATH


class DB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt          TEXT NOT NULL,
                role          TEXT DEFAULT 'user',
                is_active     INTEGER DEFAULT 1,
                created_at    INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                title      TEXT DEFAULT 'Yeni sohbet',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                conv_id    INTEGER NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS files (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                filename    TEXT NOT NULL,
                path        TEXT NOT NULL,
                text        TEXT,
                size        INTEGER,
                created_at  INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS usage_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                action     TEXT NOT NULL,
                detail     TEXT,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS email_codes (
                email      TEXT PRIMARY KEY,
                code       TEXT NOT NULL,
                attempts   INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            );
            """
        )
        # Eski veritabanlarina eposta sutunlari ekle (mevcut kayitlar korunur)
        cols = {row[1] for row in self.conn.execute("PRAGMA table_info(users)").fetchall()}
        if "email" not in cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        if "email_verified" not in cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0")
            # Onceki kayitlar zaten onayli sayilir
            self.conn.execute("UPDATE users SET email_verified = 1")
        self.conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email "
            "ON users(email) WHERE email IS NOT NULL AND email != ''"
        )
        self.conn.commit()

    # ---------------- kullanici ----------------
    def user_by_name(self, username):
        r = self.conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(r) if r else None

    def user_by_email(self, email):
        r = self.conn.execute(
            "SELECT * FROM users WHERE lower(COALESCE(email,'')) = ?",
            (str(email or "").strip().lower(),),
        ).fetchone()
        return dict(r) if r else None

    def user_by_login(self, identifier):
        q = str(identifier or "").strip().lower()
        r = self.conn.execute(
            "SELECT * FROM users WHERE lower(username) = ? "
            "OR lower(COALESCE(email,'')) = ? LIMIT 1",
            (q, q),
        ).fetchone()
        return dict(r) if r else None

    def user_by_id(self, uid):
        r = self.conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        return dict(r) if r else None

    def create_user(self, username, password_hash, salt, role="user", email=None,
                    email_verified=False):
        c = self.conn.execute(
            "INSERT INTO users (username, email, email_verified, password_hash, salt, role, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                username,
                (email or "").strip().lower() or None,
                int(bool(email_verified)),
                password_hash,
                salt,
                role,
                int(time.time()),
            ),
        )
        self.conn.commit()
        return c.lastrowid

    def mark_email_verified(self, uid):
        self.conn.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (uid,))
        self.conn.commit()

    def list_users(self):
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT id, username, email, email_verified, role, is_active, created_at "
                "FROM users ORDER BY id"
            ).fetchall()
        ]

    # ---------------- e-posta doğrulama ----------------
    def save_code(self, email, code, minutes=10):
        now = int(time.time())
        self.conn.execute(
            "INSERT OR REPLACE INTO email_codes (email, code, attempts, created_at, expires_at) "
            "VALUES (?,?,0,?,?)",
            (email.lower(), code, now, now + minutes * 60),
        )
        self.conn.commit()

    def get_code(self, email):
        r = self.conn.execute(
            "SELECT * FROM email_codes WHERE email = ?", (str(email or "").lower(),)
        ).fetchone()
        return dict(r) if r else None

    def fail_code(self, email):
        self.conn.execute(
            "UPDATE email_codes SET attempts = attempts + 1 WHERE email = ?",
            (str(email or "").lower(),),
        )
        self.conn.commit()

    def delete_code(self, email):
        self.conn.execute("DELETE FROM email_codes WHERE email = ?", (str(email or "").lower(),))
        self.conn.commit()

    def set_user_role(self, uid, role):
        self.conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, uid))
        self.conn.commit()

    def set_user_active(self, uid, active):
        self.conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (int(active), uid))
        self.conn.commit()

    # ---------------- oturum ----------------
    def create_session(self, token, user_id, expires_at):
        self.conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
            (token, user_id, int(time.time()), expires_at),
        )
        self.conn.commit()

    def session_user(self, token):
        r = self.conn.execute(
            "SELECT user_id FROM sessions WHERE token = ? AND expires_at > ?",
            (token, int(time.time())),
        ).fetchone()
        return r["user_id"] if r else None

    def delete_session(self, token):
        self.conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        self.conn.commit()

    # ---------------- sohbet ----------------
    def conversations(self, user_id):
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
        ]

    def create_conversation(self, user_id, title="Yeni sohbet"):
        now = int(time.time())
        c = self.conn.execute(
            "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?,?,?,?)",
            (user_id, title, now, now),
        )
        self.conn.commit()
        return c.lastrowid

    def conversation_owner(self, conv_id):
        r = self.conn.execute("SELECT user_id FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        return r["user_id"] if r else None

    def touch_conversation(self, conv_id, title=None):
        if title:
            self.conn.execute(
                "UPDATE conversations SET updated_at = ?, title = ? WHERE id = ?",
                (int(time.time()), title[:80], conv_id),
            )
        else:
            self.conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (int(time.time()), conv_id),
            )
        self.conn.commit()

    def delete_conversation(self, conv_id):
        self.conn.execute("DELETE FROM messages WHERE conv_id = ?", (conv_id,))
        self.conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        self.conn.commit()

    def messages(self, conv_id, limit=100):
        rows = self.conn.execute(
            "SELECT role, content, created_at FROM messages WHERE conv_id = ? ORDER BY id DESC LIMIT ?",
            (conv_id, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def add_message(self, conv_id, role, content):
        self.conn.execute(
            "INSERT INTO messages (conv_id, role, content, created_at) VALUES (?,?,?,?)",
            (conv_id, role, content, int(time.time())),
        )
        self.conn.commit()

    # ---------------- dosya ----------------
    def add_file(self, user_id, filename, path, text, size):
        c = self.conn.execute(
            "INSERT INTO files (user_id, filename, path, text, size, created_at) VALUES (?,?,?,?,?,?)",
            (user_id, filename, path, text, size, int(time.time())),
        )
        self.conn.commit()
        return c.lastrowid

    def files(self, user_id):
        return [
            {k: v for k, v in dict(r).items() if k != "text"}
            for r in self.conn.execute(
                "SELECT * FROM files WHERE user_id = ? ORDER BY id DESC", (user_id,)
            ).fetchall()
        ]

    def file_texts(self, user_id):
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT id, filename, text FROM files WHERE user_id = ?", (user_id,)
            ).fetchall()
        ]

    def delete_file(self, uid, file_id):
        r = self.conn.execute(
            "SELECT path FROM files WHERE id = ? AND user_id = ?", (file_id, uid)
        ).fetchone()
        if not r:
            return None
        self.conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
        self.conn.commit()
        return r["path"]

    # ---------------- log / istatistik ----------------
    def log(self, user_id, action, detail=""):
        self.conn.execute(
            "INSERT INTO usage_log (user_id, action, detail, created_at) VALUES (?,?,?,?)",
            (user_id, action, detail[:500], int(time.time())),
        )
        self.conn.commit()

    def stats(self):
        def one(sql):
            return self.conn.execute(sql).fetchone()[0]

        return {
            "users": one("SELECT COUNT(*) FROM users"),
            "conversations": one("SELECT COUNT(*) FROM conversations"),
            "messages": one("SELECT COUNT(*) FROM messages"),
            "files": one("SELECT COUNT(*) FROM files"),
            "requests": one("SELECT COUNT(*) FROM usage_log WHERE action='chat'"),
            "tool_calls": one("SELECT COUNT(*) FROM usage_log WHERE action LIKE 'tool:%'"),
            "active_users_24h": one(
                "SELECT COUNT(DISTINCT user_id) FROM usage_log WHERE created_at > %d"
                % (int(time.time()) - 86400)
            ),
            "recent": [
                dict(r)
                for r in self.conn.execute(
                    "SELECT u.username, l.action, l.detail, l.created_at FROM usage_log l "
                    "LEFT JOIN users u ON u.id = l.user_id ORDER BY l.id DESC LIMIT 20"
                ).fetchall()
            ],
        }


db = DB()
