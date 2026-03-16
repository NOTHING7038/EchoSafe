#!/usr/bin/env python3
"""
EchoSafe backend (FastAPI + MongoDB)
"""

import hashlib
import sqlite3
import os
import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
import base64

import bcrypt
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Hash import SHA256

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.getenv("DATABASE_URL", os.path.join(BASE_DIR, "echosafe.db"))
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-production")
JWT_ALGO = "HS256"
JWT_EXPIRE_HOURS = 24
# This salt is used for deriving encryption keys. It's not a secret but should be static.
ENCRYPTION_SALT = b"\xbf\x82\xf1\x11\x8f\x9a\x1a\xf8\x1e\x96\x95\x1e\xde\xd3\x99\x43"

DEFAULT_ADMIN_USER = os.getenv("DEFAULT_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@7038!")

app = FastAPI(title="EchoSafe API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "null",  # browsers can send Origin: null for file:// pages
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class OTPRequest(BaseModel):
    email: str

class OTPVerify(BaseModel):
    email: str
    otp: str


class OTPRequest(BaseModel):
    email: str

class OTPVerify(BaseModel):
    email: str
    otp: str


class SubmitReportRequest(BaseModel):
    report_text: str = Field(min_length=5)


class UpdateStatusRequest(BaseModel):
    case_id: str
    status: str


class DecryptRequest(BaseModel):
    case_id: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    username: str
    password: str = Field(min_length=8)


def now_utc() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def build_token(username: str) -> str:
    exp = now_utc() + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": username, "exp": exp}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def get_current_user(
    authorization: str | None = Header(default=None), token: str | None = Query(default=None)
) -> dict[str, Any]:
    if authorization and authorization.startswith("Bearer "):
        token_str = authorization.split(" ", 1)[1].strip()
    elif token:
        token_str = token
    else:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token")

    try:
        payload = jwt.decode(token_str, JWT_SECRET, algorithms=[JWT_ALGO])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    with sqlite3.connect(DATABASE_URL) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hr_users WHERE username = ?", (username,))
        user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)


def get_encryption_key(case_id: str) -> bytes:
    return PBKDF2(case_id, ENCRYPTION_SALT, dkLen=32, count=1000000, hmac_hash_module=SHA256)


def encrypt_text(text: str, key: bytes) -> dict[str, str]:
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(text.encode("utf-8"))
    return {
        "iv": base64.b64encode(cipher.nonce).decode("utf-8"),
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
        "tag": base64.b64encode(tag).decode("utf-8"),
    }


def decrypt_text(encrypted_data: dict[str, str], key: bytes) -> str:
    try:
        iv = base64.b64decode(encrypted_data["iv"])
        ciphertext = base64.b64decode(encrypted_data["ciphertext"])
        tag = base64.b64decode(encrypted_data["tag"])
        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")
    except (ValueError, KeyError):
        raise HTTPException(status_code=500, detail="Decryption failed")


def urgency_score(text: str) -> float:
    text_l = text.lower()
    score = 0.1
    high = ["threat", "violence", "abuse", "assault", "unsafe", "harassment"]
    medium = ["bully", "discrimination", "retaliation", "hostile", "pressure"]
    for kw in high:
        if kw in text_l:
            score += 0.2
    for kw in medium:
        if kw in text_l:
            score += 0.1
    return max(0.0, min(1.0, round(score, 2)))


def ensure_default_admin() -> None:
    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM hr_users WHERE username = ?", (DEFAULT_ADMIN_USER,))
        if cursor.fetchone():
            return

        cursor.execute(
            "INSERT INTO hr_users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (
                DEFAULT_ADMIN_USER,
                hash_password(DEFAULT_ADMIN_PASSWORD),
                now_utc().isoformat(),
            ),
        )
        conn.commit()
        print(f"Created default admin user: {DEFAULT_ADMIN_USER}")


def init_db() -> None:
    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hr_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            encrypted_report TEXT NOT NULL,
            iv TEXT NOT NULL,
            auth_tag TEXT NOT NULL,
            urgency_score REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hr_otps (
            email TEXT PRIMARY KEY,
            otp_code TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hr_otps (
            email TEXT PRIMARY KEY,
            otp_code TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )""")
        conn.commit()


@app.on_event("startup")
def startup() -> None:
    try:
        print("--- 🚀 Initializing Database... ---")
        init_db()
        print("--- ✅ Database Initialized. ---")
        print("--- 👤 Ensuring default admin user... ---")
        ensure_default_admin()
        print("--- ✅ Admin user check complete. ---")
    except Exception as e:
        print(f"\n🔥🔥🔥 A FATAL ERROR OCCURRED ON STARTUP 🔥🔥🔥")
        import traceback
        traceback.print_exc()


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "EchoSafe API"}


def send_otp_email(email: str, otp: str) -> None:
    # For this MVP, we print to the console. 
    # In production, integrate smtplib or an email API like SendGrid here.
    print(f"\n{'='*50}")
    print(f"📧 EMAIL SENT TO: {email}")
    print(f"🔑 YOUR ONE-TIME PASSWORD IS: {otp}")
    print(f"{'='*50}\n")


@app.post("/api/hr/request_otp")
def request_otp(body: OTPRequest) -> dict[str, Any]:
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
        
    otp = f"{random.randint(100000, 999999)}"
    expires = (now_utc() + timedelta(minutes=10)).isoformat()
    
    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO hr_otps (email, otp_code, expires_at) VALUES (?, ?, ?)",
            (email, otp, expires)
        )
        conn.commit()
        
    send_otp_email(email, otp)
    return {"success": True, "message": f"OTP sent to {email}"}


@app.post("/api/hr/verify_otp")
def verify_otp(body: OTPVerify) -> dict[str, Any]:
    email = body.email.strip().lower()
    
    with sqlite3.connect(DATABASE_URL) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hr_otps WHERE email = ?", (email,))
        record = cursor.fetchone()
        
        if not record:
            raise HTTPException(status_code=401, detail="No OTP requested for this email")
        if record["otp_code"] != body.otp:
            raise HTTPException(status_code=401, detail="Invalid OTP code")
        if record["expires_at"] < now_utc().isoformat():
            raise HTTPException(status_code=401, detail="OTP has expired")
            
        # OTP is valid, clear it
        cursor.execute("DELETE FROM hr_otps WHERE email = ?", (email,))
        
        # Check if user exists, if not create them
        cursor.execute("SELECT * FROM hr_users WHERE username = ?", (email,))
        user = cursor.fetchone()
        if not user:
            cursor.execute(
                "INSERT INTO hr_users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (email, "OTP_LOGIN", now_utc().isoformat())
            )
        conn.commit()
        
    token = build_token(email)
    return {"success": True, "token": token}


def send_otp_email(email: str, otp: str) -> None:
    # For this MVP, we print to the console. 
    # In production, integrate smtplib or an email API like SendGrid here.
    print(f"\n{'='*50}")
    print(f"📧 EMAIL SENT TO: {email}")
    print(f"🔑 YOUR ONE-TIME PASSWORD IS: {otp}")
    print(f"{'='*50}\n")


@app.post("/api/hr/request_otp")
def request_otp(body: OTPRequest) -> dict[str, Any]:
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
        
    otp = f"{random.randint(100000, 999999)}"
    expires = (now_utc() + timedelta(minutes=10)).isoformat()
    
    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO hr_otps (email, otp_code, expires_at) VALUES (?, ?, ?)",
            (email, otp, expires)
        )
        conn.commit()
        
    send_otp_email(email, otp)
    return {"success": True, "message": f"OTP sent to {email}"}


@app.post("/api/hr/verify_otp")
def verify_otp(body: OTPVerify) -> dict[str, Any]:
    email = body.email.strip().lower()
    
    with sqlite3.connect(DATABASE_URL) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hr_otps WHERE email = ?", (email,))
        record = cursor.fetchone()
        
        if not record:
            raise HTTPException(status_code=401, detail="No OTP requested for this email")
        if record["otp_code"] != body.otp:
            raise HTTPException(status_code=401, detail="Invalid OTP code")
        if record["expires_at"] < now_utc().isoformat():
            raise HTTPException(status_code=401, detail="OTP has expired")
            
        # OTP is valid, clear it
        cursor.execute("DELETE FROM hr_otps WHERE email = ?", (email,))
        
        # Check if user exists, if not create them
        cursor.execute("SELECT * FROM hr_users WHERE username = ?", (email,))
        user = cursor.fetchone()
        if not user:
            cursor.execute(
                "INSERT INTO hr_users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (email, "OTP_LOGIN", now_utc().isoformat())
            )
        conn.commit()
        
    token = build_token(email)
    return {"success": True, "token": token}


@app.get("/api/hr/dashboard")
def hr_dashboard(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=1000),
    search: str = Query(default=""),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    base_query = "FROM reports"
    where_clause = ""
    params: list[Any] = []

    if search.strip():
        s = search.strip()
        # Full-text search on encrypted data is not possible. Only search by case_id.
        where_clause = "WHERE case_id LIKE ?"
        params.append(f"%{s}%")

    with sqlite3.connect(DATABASE_URL) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        total_cursor = cursor.execute(f"SELECT COUNT(*) {base_query} {where_clause}", params)
        total = total_cursor.fetchone()[0]

        skip = (page - 1) * limit
        query = f"""
            SELECT case_id, urgency_score, status, created_at
            {base_query} {where_clause}
            ORDER BY urgency_score DESC, created_at DESC
            LIMIT ? OFFSET ?
        """
        rows_cursor = cursor.execute(query, (*params, limit, skip))
        rows = [dict(row) for row in rows_cursor.fetchall()]

    pages = (total + limit - 1) // limit if total else 0
    return {
        "investigator": user["username"],
        "reports": rows,
        "pagination": {"page": page, "limit": limit, "total": total, "pages": pages},
    }


@app.post("/api/hr/decrypt_report")
def decrypt_report(body: DecryptRequest, _: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    with sqlite3.connect(DATABASE_URL) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE case_id = ?", (body.case_id,))
        report = cursor.fetchone()

    if not report:
        raise HTTPException(status_code=404, detail="Case not found")

    key = get_encryption_key(report["case_id"])
    encrypted_data = {
        "iv": report["iv"],
        "ciphertext": report["encrypted_report"],
        "tag": report["auth_tag"],
    }
    decrypted_text = decrypt_text(encrypted_data, key)

    return {
        "case_id": report["case_id"],
        "report_text": decrypted_text,
        "created_at": report["created_at"],
    }


@app.put("/api/hr/update_status")
def update_status(body: UpdateStatusRequest, _: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    allowed = {"pending", "investigating", "resolved"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")

    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE reports SET status = ? WHERE case_id = ?", (body.status, body.case_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Case not found")
        conn.commit()
    return {"success": True}


@app.post("/api/hr/change_password")
def change_password(body: ChangePasswordRequest, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if not verify_password(body.old_password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        new_hash = hash_password(body.new_password)
        cursor.execute("UPDATE hr_users SET password_hash = ? WHERE username = ?", (new_hash, user["username"]))
        conn.commit()
    return {"success": True}


@app.post("/api/hr/logout")
def hr_logout(_: dict[str, Any] = Depends(get_current_user)) -> dict[str, bool]:
    return {"success": True}


@app.get("/api/hr/analytics")
def hr_analytics(
    _: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    with sqlite3.connect(DATABASE_URL) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT created_at, status, urgency_score FROM reports")
        items = cursor.fetchall()

    volume_map: dict[str, int] = {}
    status = {"pending": 0, "investigating": 0, "resolved": 0}
    priority = {"high": 0, "medium": 0, "low": 0}

    for r in items:
        key = r["created_at"][:10]  # YYYY-MM-DD
        volume_map[key] = volume_map.get(key, 0) + 1

        st = r["status"]
        if st in status:
            status[st] += 1

        us = float(r["urgency_score"])
        if us > 0.6:
            priority["high"] += 1
        elif us > 0.3:
            priority["medium"] += 1
        else:
            priority["low"] += 1

    volume = [{"period": k, "count": volume_map[k]} for k in sorted(volume_map.keys())]
    return {"volume": volume, "status": status, "priority": priority, "top_reporters": []}


@app.post("/api/submit_report")
def submit_report(body: SubmitReportRequest) -> dict[str, Any]:
    case_id = hashlib.sha256(f"{uuid.uuid4()}-{now_utc().isoformat()}".encode("utf-8")).hexdigest()
    report_text = body.report_text.strip()

    key = get_encryption_key(case_id)
    encrypted_data = encrypt_text(report_text, key)

    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reports (case_id, encrypted_report, iv, auth_tag, urgency_score, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                encrypted_data["ciphertext"],
                encrypted_data["iv"],
                encrypted_data["tag"],
                urgency_score(report_text),
                "pending",
                now_utc().isoformat(),
            ),
        )
        conn.commit()

    return {"success": True, "case_id": case_id}


@app.get("/api/view_report")
def view_report(case_id: str = Query(..., min_length=8)) -> dict[str, Any]:
    with sqlite3.connect(DATABASE_URL) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE case_id = ?", (case_id,))
        report = cursor.fetchone()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "case_id": report["case_id"],
        "status": report["status"],
        "created_at": report["created_at"],
        "encrypted_report": report["encrypted_report"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
