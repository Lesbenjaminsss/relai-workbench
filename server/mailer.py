"""SMTP ile doğrulama kodu gönderir.

Ayarlar C:\\AIServer\\smtp.json dosyasindan okunur:
{
  "host": "smtp.gmail.com",
  "port": 587,
  "security": "starttls",
  "username": "sizin@adres.com",
  "password": "uygulama sifresi",
  "from": "RelAI <sizin@adres.com>"
}
"""
import json
import os
import smtplib
import ssl
from email.message import EmailMessage

from config import BASE_DIR

CONFIG_PATH = os.path.join(BASE_DIR, "smtp.json")


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def enabled():
    c = load_config()
    if not all(c.get(k) for k in ("host", "username", "password")):
        return False
    # Ornek dosyadaki yer tutucular gercek ayar sayilmasin
    placeholders = ("SIZIN", "APP_SIFRESI", "ornek", "example")
    values = " ".join(str(c.get(k) or "") for k in ("username", "password", "host"))
    return not any(p.lower() in values.lower() for p in placeholders)


def send_code(email, code, username, minutes=10):
    """Kodu gonderir. SMTP ayarli degilse False dondurur."""
    c = load_config()
    if not enabled():
        return False

    security = str(c.get("security") or "starttls").lower()
    port = int(c.get("port") or (465 if security == "ssl" else 587))
    sender = c.get("from") or c["username"]

    msg = EmailMessage()
    msg["Subject"] = "RelAİ doğrulama kodu"
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(
        f"Merhaba {username},\n\n"
        f"RelAİ hesabını doğrulamak için doğrulama kodun: {code}\n"
        f"Bu kod {minutes} dakika geçerlidir.\n\n"
        f"Bu kodu sen istemediysen e-postayı yok sayabilirsin.\n\n"
        f"RelAİ"
    )

    context = ssl.create_default_context()
    try:
        if security == "ssl":
            with smtplib.SMTP_SSL(c["host"], port, timeout=15, context=context) as server:
                server.login(c["username"], c["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(c["host"], port, timeout=15) as server:
                server.starttls(context=context)
                server.login(c["username"], c["password"])
                server.send_message(msg)
    except Exception as exc:
        print(f"[MAIL] Gonderilemedi: {exc}")
        return False
    return True
