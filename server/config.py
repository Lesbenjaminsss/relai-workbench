import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "ai_server.db")
SECRET_FILE = os.path.join(DATA_DIR, "secret.key")

if os.path.exists(SECRET_FILE):
    with open(SECRET_FILE, "r", encoding="utf-8") as f:
        SECRET_KEY = f.read().strip()
else:
    SECRET_KEY = secrets.token_urlsafe(48)
    with open(SECRET_FILE, "w", encoding="utf-8") as f:
        f.write(SECRET_KEY)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma2:2b")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
MAX_FILE_MB = 10
SESSION_HOURS = 24 * 7
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me")
