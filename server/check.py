import os
import sqlite3
import sys

import config

print("=== AI SERVER KONTROL ===")
print("Python       :", sys.version.split()[0])
print("Veritabani   :", config.DB_PATH, "->", "var" if os.path.exists(config.DB_PATH) else "yok")
print("Ollama URL   :", config.OLLAMA_URL)
print("Model        :", config.OLLAMA_MODEL)
print("Port         :", config.PORT)
print("Statik dosya :", config.STATIC_DIR)

for mod in ["fastapi", "uvicorn", "aiohttp", "pypdf", "docx", "bs4", "jwt"]:
    try:
        __import__(mod)
        print(f"Paket {mod:12s}: OK")
    except Exception as exc:
        print(f"Paket {mod:12s}: EKSIK ({exc})")

try:
    c = sqlite3.connect(config.DB_PATH)
    for table in ["users", "conversations", "messages", "files", "usage_log"]:
        n = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"Tablo {table:14s}: {n} kayit")
    c.close()
except Exception as exc:
    print("DB HATA:", exc)
