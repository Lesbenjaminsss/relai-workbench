# RelAİ Workbench

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009485?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Electron](https://img.shields.io/badge/Electron-35-2F3246?logo=electron&logoColor=white)](https://www.electronjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-6d8768.svg)](LICENSE)

**A self-hosted AI desk that looks like a human made it.**

RelAİ is a central AI server with a warm, hand-crafted web interface and an Electron Windows client. It runs local [Ollama](https://ollama.com/) models, searches the web when a question needs real facts, reads your files, and keeps chats, users, roles and admin stats in one calm place.

> Documentation: [Türkçe](README.tr.md) · **English** · [Español](README.es.md)

---

## Why it stands out

- **Facts over guessing.** Information queries are sent through DuckDuckGo HTML search *before* the model answers. Pure math is calculated directly.
- **A menu with a fingerprint.** Warm paper, dark "desk" sidebar, serif headings, custom SVG icons, monogram avatars, a real light/dark switch. No robot emoji, no purple gradients.
- **Email verification.** Six-digit codes, 10-minute expiry, 5 attempts, 60-second resend cooldown, and automatic sign-in after verification.
- **One identity, everywhere.** Log in with username *or* email. Sessions, roles, banned users, chat history and file analysis are shared by web and desktop clients.
- **Voice in, voice out.** Browser speech recognition for input, speech synthesis for answers.
- **Optional Discord companion.** Moderation, levels, economy, tickets, welcome messages and music cogs included.

## Stack

| Layer | Technology |
| --- | --- |
| API | FastAPI + Uvicorn |
| Storage | SQLite (users, sessions, chats, files, logs) |
| Model | Ollama (local) |
| Web | Plain HTML / CSS / JavaScript — no framework |
| Desktop | Electron 35 |
| Email | SMTP via `smtp.json` |

## Repository layout

```text
relai-workbench/
├── server/
│   ├── app.py            # API, chat pipeline, forced web search
│   ├── auth.py           # PBKDF2 passwords + bearer sessions
│   ├── db.py             # SQLite schema and queries
│   ├── mailer.py         # SMTP verification codes
│   ├── ollama.py         # local model client
│   ├── tools.py          # web search, calculator, weather
│   ├── static/           # login, app and admin UI
│   └── requirements.txt
├── desktop/              # Electron shell (loads the server URL)
└── discord-bot/          # Optional Discord bot
```

## Quick start

### 1. Install and run the server

```bash
cd server
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Set the environment variables (PowerShell example):

```powershell
$env:OLLAMA_MODEL = 'gemma2:2b'
$env:ADMIN_USERNAME = 'admin'
$env:ADMIN_PASSWORD = 'choose-a-strong-password'
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000>. The admin panel is at `/admin`.

### 2. Pull a model

```bash
ollama pull gemma2:2b
```

`gemma2:2b` is fast on 4 GB RAM. `qwen2.5:3b` is stronger but much slower on small machines.

### 3. Enable real verification emails

```bash
copy server\smtp.example.json server\smtp.json
```

Fill in `host`, `port`, `security`, `username`, `password` and `from`. Gmail needs an **app password**, not the account password. If SMTP is not configured, the six-digit code is shown on the registration screen so you can still test the flow.

### 4. Build the desktop client

```bash
cd desktop
npm install
copy config.example.json config.json
# set "serverUrl" to your server, e.g. http://localhost:8000
npm run build
```

The installer appears in `desktop/dist/`. The Electron window simply loads the web app, so UI updates do not require a rebuild.

### 5. Optional Discord bot

```bash
cd discord-bot
copy config.example.json config.json
# paste your bot token into config.json
pip install -r requirements.txt
python bot.py
```

## API overview

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/register` | Create account + send verification code |
| POST | `/api/verify-email` | Check code, return session token |
| POST | `/api/resend-code` | Request a new code (60 s cooldown) |
| POST | `/api/login` | Sign in with username or email |
| GET | `/api/me` | Current user |
| POST | `/api/chat` | Ask the assistant |
| GET / POST / DELETE | `/api/conversations`, `/api/files` | History and file analysis |
| GET | `/api/admin/stats`, `/api/admin/users` | Admin data |

## Security notes

- Change the default admin password immediately.
- Put HTTPS in front of the server (Caddy or Nginx) before exposing it publicly.
- Never commit `server/data/`, `server/smtp.json`, `desktop/config.json`, `discord-bot/config.json` or any `.env` file. `.gitignore` already covers them.

## License

MIT — see [LICENSE](LICENSE). Made with care, not a template.
