import os
import re
import secrets
import time

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import auth
import files as file_utils
import mailer
import ollama
import tools as tool_utils
from config import ADMIN_PASSWORD, ADMIN_USERNAME, OLLAMA_MODEL, STATIC_DIR, UPLOAD_DIR
from db import db

app = FastAPI(title="RelAİ", version="1.1.0")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------- modeller ----------------
class LoginIn(BaseModel):
    username: str
    password: str


class RegisterIn(BaseModel):
    username: str
    email: str = ""
    password: str


class VerifyIn(BaseModel):
    email: str
    code: str


class ResendIn(BaseModel):
    email: str


class ConversationIn(BaseModel):
    title: str = "Yeni sohbet"


class ChatIn(BaseModel):
    message: str
    conversation_id: int | None = None
    use_tools: bool = True
    use_files: bool = True


class RoleIn(BaseModel):
    role: str


# ---------------- baslangic ----------------
@app.on_event("startup")
def startup():
    if not db.user_by_name(ADMIN_USERNAME):
        digest, salt = auth.hash_password(ADMIN_PASSWORD)
        db.create_user(ADMIN_USERNAME, digest, salt, role="admin")
        print(f"[INIT] Admin olusturuldu: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")


# ---------------- saglik ----------------
@app.get("/api/health")
async def health():
    status = await ollama.health()
    return {"server": "ok", "ollama": status, "model": OLLAMA_MODEL}


# ---------------- kimlik ----------------
@app.post("/api/register")
def register(data: RegisterIn):
    username = data.username.strip()
    email = data.email.strip().lower()
    if len(username) < 3 or len(data.password) < 4:
        raise HTTPException(400, "Kullanıcı adı en az 3, şifre en az 4 karakter olmalı.")
    if not EMAIL_RE.fullmatch(email):
        raise HTTPException(400, "Geçerli bir e-posta adresi girin.")
    if db.user_by_name(username):
        raise HTTPException(400, "Bu kullanıcı adı zaten kullanılıyor.")
    if db.user_by_email(email):
        raise HTTPException(400, "Bu e-posta adresi zaten kayıtlı.")
    digest, salt = auth.hash_password(data.password)
    uid = db.create_user(username, digest, salt, email=email)
    code = f"{secrets.randbelow(1000000):06d}"
    db.save_code(email, code, minutes=10)
    sent = mailer.send_code(email, code, username)
    db.log(uid, "register")
    return {
        "ok": True,
        "user_id": uid,
        "email": email,
        "email_sent": sent,
        "dev_code": None if sent else code,
    }


@app.post("/api/login")
def login(data: LoginIn):
    user = db.user_by_login(data.username)
    if not user or not auth.verify_password(data.password, user["password_hash"], user["salt"]):
        raise HTTPException(401, "Kullanıcı adı/e-posta veya şifre hatalı.")
    if not user["is_active"]:
        raise HTTPException(403, "Hesap devre dışı.")
    if user["email"] and not user["email_verified"]:
        raise HTTPException(403, {
            "message": "E-posta adresini doğrulaman gerekiyor.",
            "email": user["email"],
            "verify_required": True,
        })
    token = auth.create_session(user["id"])
    db.log(user["id"], "login")
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
        },
    }


@app.post("/api/verify-email")
def verify_email(data: VerifyIn):
    email = data.email.strip().lower()
    rec = db.get_code(email)
    if not rec:
        raise HTTPException(400, "Kod bulunamadı veya süresi doldu. Yeni kod isteyin.")
    if rec["expires_at"] < int(time.time()):
        db.delete_code(email)
        raise HTTPException(400, "Kodun süresi doldu. Yeni kod isteyin.")
    if rec["attempts"] >= 5:
        db.delete_code(email)
        raise HTTPException(400, "Çok fazla yanlış deneme. Yeni kod isteyin.")
    if str(data.code).strip() != rec["code"]:
        db.fail_code(email)
        raise HTTPException(400, "Doğrulama kodu hatalı.")

    user = db.user_by_email(email)
    if not user:
        raise HTTPException(400, "Bu e-postaya ait kayıt bulunamadı.")
    db.mark_email_verified(user["id"])
    db.delete_code(email)
    token = auth.create_session(user["id"])
    db.log(user["id"], "email_verified")
    return {
        "ok": True,
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
        },
    }


@app.post("/api/resend-code")
def resend_code(data: ResendIn):
    email = data.email.strip().lower()
    user = db.user_by_email(email)
    if not user:
        raise HTTPException(404, "Bu e-postaya ait kayıt bulunamadı.")
    if user["email_verified"]:
        raise HTTPException(400, "Bu e-posta zaten doğrulandı.")
    rec = db.get_code(email)
    if rec and int(time.time()) - rec["created_at"] < 60:
        raise HTTPException(429, "Yeni kod için biraz bekleyin (60 sn).")
    code = f"{secrets.randbelow(1000000):06d}"
    db.save_code(email, code, minutes=10)
    sent = mailer.send_code(email, code, user["username"])
    db.log(user["id"], "code_resend")
    return {"ok": True, "email_sent": sent, "dev_code": None if sent else code}


@app.post("/api/logout")
def logout(user=Depends(auth.current_user), authorization: str = ""):
    db.delete_session(authorization.replace("Bearer ", "").strip())
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(auth.current_user)):
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
    }


# ---------------- sohbetler ----------------
@app.get("/api/conversations")
def conversations(user=Depends(auth.current_user)):
    return db.conversations(user["id"])


@app.post("/api/conversations")
def new_conversation(data: ConversationIn, user=Depends(auth.current_user)):
    cid = db.create_conversation(user["id"], data.title or "Yeni sohbet")
    db.log(user["id"], "conversation_create", str(cid))
    return {"id": cid, "title": data.title or "Yeni sohbet"}


@app.get("/api/conversations/{cid}/messages")
def get_messages(cid: int, user=Depends(auth.current_user)):
    if db.conversation_owner(cid) != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Bu sohbete erişim yok.")
    return db.messages(cid)


@app.delete("/api/conversations/{cid}")
def delete_conversation(cid: int, user=Depends(auth.current_user)):
    if db.conversation_owner(cid) != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Bu sohbete erişim yok.")
    db.delete_conversation(cid)
    return {"ok": True}


# ---------------- dosyalar ----------------
@app.post("/api/upload")
async def upload(file: UploadFile = File(...), user=Depends(auth.current_user)):
    if not file_utils.allowed(file.filename or ""):
        raise HTTPException(400, "Desteklenen format: txt, md, csv, log, json, pdf, docx")
    data = file_utils.check_size(await file.read())
    safe = f"u{user['id']}_{int(time.time())}_{os.path.basename(file.filename or 'file')}"
    path = os.path.join(UPLOAD_DIR, safe)
    with open(path, "wb") as f:
        f.write(data)
    text = file_utils.extract(path, file.filename or "")
    fid = db.add_file(user["id"], file.filename or "file", path, text, len(data))
    db.log(user["id"], "upload", file.filename)
    return {"id": fid, "filename": file.filename, "size": len(data), "chars": len(text)}


@app.get("/api/files")
def list_files(user=Depends(auth.current_user)):
    return db.files(user["id"])


@app.delete("/api/files/{fid}")
def remove_file(fid: int, user=Depends(auth.current_user)):
    path = db.delete_file(user["id"], fid)
    if not path:
        raise HTTPException(404, "Dosya bulunamadı.")
    try:
        os.remove(path)
    except OSError:
        pass
    return {"ok": True}


# ---------------- sohbet / AI ----------------
@app.post("/api/chat")
async def chat(data: ChatIn, user=Depends(auth.current_user)):
    message = data.message.strip()
    if not message:
        raise HTTPException(400, "Mesaj boş olamaz.")

    cid = data.conversation_id
    if not cid:
        cid = db.create_conversation(user["id"], message[:60])
    elif db.conversation_owner(cid) != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Bu sohbete erişim yok.")

    db.add_message(cid, "user", message)

    system = (
        "Sen RelAİ adlı, Türkçe konuşan, yardımcı ve kısa cevap veren bir yapay zeka asistanısın. "
        "Cevaplarında markdown kullanabilirsin. "
        + (tool_utils.TOOL_DESCRIPTIONS if data.use_tools else "")
    )
    if data.use_files:
        context = file_utils.relevant_context(db.file_texts(user["id"]), message)
        if context:
            system += "\n\nKullanıcının yüklediği dosyalardan ilgili içerik:\n" + context[:6000]

    history = [{"role": m["role"], "content": m["content"]} for m in db.messages(cid)[-6:]]
    messages = [{"role": "system", "content": system}] + history

    math_only = bool(re.fullmatch(r"[0-9\s\+\-\*/\(\)\.]+", message)) and any(c in message for c in "+-*/")
    if data.use_tools and math_only:
        name, result = await tool_utils.run_tool({"tool": "calculator", "args": {"expression": message}})
        db.add_message(cid, "assistant", result)
        db.touch_conversation(cid, message[:60])
        db.log(user["id"], "tool:calculator", message[:200])
        return {"answer": result, "conversation_id": cid, "tool": {"tool": name, "result": result}}
    tool_used = None
    web_forced = False
    if data.use_tools and not math_only:
        needs_search = (len(message) > 12 or "?" in message)
        if needs_search:
            name, web_result = await tool_utils.run_tool({"tool": "web_search", "args": {"query": message, "limit": 3}})
            if web_result and "bulunamad" not in web_result and "hatas" not in web_result:
                system += "\n\nINTERNET SEARCH RESULTS (use these facts; answer in Turkish):\n" + web_result[:1200]
                messages[0]["content"] = system
                tool_used = {"tool": "web_search", "result": web_result[:500]}
                messages.append({"role": "user", "content": "Use the internet search results above. Answer in Turkish. Do not output JSON."})
                web_forced = True
    try:
        first = await ollama.chat(messages)
        call = tool_utils.parse_tool_call(first) if (data.use_tools and not web_forced) else None
        if call:
            name, result = await tool_utils.run_tool(call)
            tool_used = {"tool": name, "result": result}
            db.log(user["id"], f"tool:{name}", str(call.get("args", {})))
            messages.append({"role": "assistant", "content": first})
            messages.append(
                {
                    "role": "user",
                    "content": f"Aracın sonucu: {result}\nBu sonucu kullanarak kullanıcıya doğal ve kısa bir cevap ver. JSON kullanma.",
                }
            )
            answer = await ollama.chat(messages)
        else:
            answer = first
    except Exception as exc:
        answer = f"Üzgünüm, bir hata oluştu: {exc}"

    db.add_message(cid, "assistant", answer)
    db.touch_conversation(cid, message[:60])
    db.log(user["id"], "chat", message[:200])
    return {"answer": answer, "conversation_id": cid, "tool": tool_used}


# ---------------- admin ----------------
@app.get("/api/admin/stats")
def admin_stats(admin=Depends(auth.admin_user)):
    return db.stats()


@app.get("/api/admin/users")
def admin_users(admin=Depends(auth.admin_user)):
    return db.list_users()


@app.post("/api/admin/users/{uid}/role")
def admin_set_role(uid: int, data: RoleIn, admin=Depends(auth.admin_user)):
    if data.role not in ("user", "admin"):
        raise HTTPException(400, "Rol sadece user veya admin olabilir.")
    db.set_user_role(uid, data.role)
    return {"ok": True}


@app.post("/api/admin/users/{uid}/active")
def admin_set_active(uid: int, active: bool, admin=Depends(auth.admin_user)):
    db.set_user_active(uid, active)
    return {"ok": True}


# ---------------- arayuz ----------------
@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/admin")
def admin_page():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
