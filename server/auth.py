import hashlib
import hmac
import secrets
import time

from fastapi import Depends, HTTPException, Header

from config import SESSION_HOURS
from db import db


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 210000
    ).hex()
    return digest, salt


def verify_password(password, digest, salt):
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, digest)


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    db.create_session(token, user_id, int(time.time()) + SESSION_HOURS * 3600)
    return token


def current_user(authorization: str = Header(default="")):
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(401, "Giriş yapmanız gerekiyor.")
    uid = db.session_user(token)
    if not uid:
        raise HTTPException(401, "Oturum süresi doldu.")
    user = db.user_by_id(uid)
    if not user or not user["is_active"]:
        raise HTTPException(403, "Hesap devre dışı.")
    return user


def admin_user(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin yetkisi gerekiyor.")
    return user
