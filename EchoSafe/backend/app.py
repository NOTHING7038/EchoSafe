#!/usr/bin/env python3
"""
EchoSafe backend (FastAPI + MongoDB)
"""

import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import DESCENDING, MongoClient


MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "echosafe")
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-production")
JWT_ALGO = "HS256"
JWT_EXPIRE_HOURS = 24
DEFAULT_ADMIN_USER = os.getenv("DEFAULT_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@7038!")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]
hr_users = db["hr_users"]
reports = db["reports"]

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


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = hr_users.find_one({"username": username}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


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
    existing = hr_users.find_one({"username": DEFAULT_ADMIN_USER})
    if existing:
        return
    hr_users.insert_one(
        {
            "username": DEFAULT_ADMIN_USER,
            "password_hash": hash_password(DEFAULT_ADMIN_PASSWORD),
            "created_at": now_utc(),
        }
    )


@app.on_event("startup")
def startup() -> None:
    hr_users.create_index("username", unique=True)
    reports.create_index("case_id", unique=True)
    reports.create_index([("created_at", DESCENDING)])
    ensure_default_admin()


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "EchoSafe API"}


@app.post("/api/hr/register")
def register_hr(body: RegisterRequest) -> dict[str, Any]:
    username = body.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username required")
    if hr_users.find_one({"username": username}):
        raise HTTPException(status_code=409, detail="Username already exists")
    hr_users.insert_one(
        {
            "username": username,
            "password_hash": hash_password(body.password),
            "created_at": now_utc(),
        }
    )
    return {"success": True, "message": "HR user created"}


@app.post("/api/hr/login")
def hr_login(body: LoginRequest) -> dict[str, Any]:
    username = body.username.strip()
    user = hr_users.find_one({"username": username})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = build_token(username)
    return {"success": True, "token": token}


@app.get("/api/hr/dashboard")
def hr_dashboard(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=1000),
    search: str = Query(default=""),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if search.strip():
        s = search.strip()
        query["$or"] = [
            {"case_id": {"$regex": s, "$options": "i"}},
            {"report_text": {"$regex": s, "$options": "i"}},
        ]

    total = reports.count_documents(query)
    skip = (page - 1) * limit
    rows = list(
        reports.find(query, {"_id": 0})
        .sort([("urgency_score", DESCENDING), ("created_at", DESCENDING)])
        .skip(skip)
        .limit(limit)
    )
    for row in rows:
        created_at = row.get("created_at")
        if isinstance(created_at, datetime):
            row["created_at"] = created_at.isoformat()

    pages = (total + limit - 1) // limit if total else 0
    return {
        "investigator": user["username"],
        "reports": rows,
        "pagination": {"page": page, "limit": limit, "total": total, "pages": pages},
    }


@app.post("/api/hr/decrypt_report")
def decrypt_report(body: DecryptRequest, _: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    report = reports.find_one({"case_id": body.case_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Case not found")
    created_at = report.get("created_at")
    if isinstance(created_at, datetime):
        report["created_at"] = created_at.isoformat()
    return {
        "case_id": report["case_id"],
        "report_text": report.get("report_text", ""),
        "created_at": report.get("created_at"),
    }


@app.put("/api/hr/update_status")
def update_status(body: UpdateStatusRequest, _: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    allowed = {"pending", "investigating", "resolved"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")
    res = reports.update_one({"case_id": body.case_id}, {"$set": {"status": body.status}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"success": True}


@app.post("/api/hr/change_password")
def change_password(body: ChangePasswordRequest, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if not verify_password(body.old_password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    hr_users.update_one(
        {"username": user["username"]},
        {"$set": {"password_hash": hash_password(body.new_password)}},
    )
    return {"success": True}


@app.post("/api/hr/logout")
def hr_logout(_: dict[str, Any] = Depends(get_current_user)) -> dict[str, bool]:
    return {"success": True}


@app.get("/api/hr/analytics")
def hr_analytics(
    _: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    items = list(reports.find({}, {"_id": 0}))
    volume_map: dict[str, int] = {}
    status = {"pending": 0, "investigating": 0, "resolved": 0}
    priority = {"high": 0, "medium": 0, "low": 0}

    for r in items:
        created_at = r.get("created_at")
        if isinstance(created_at, datetime):
            key = created_at.strftime("%Y-%m-%d")
        else:
            key = "unknown"
        volume_map[key] = volume_map.get(key, 0) + 1

        st = r.get("status", "pending")
        if st in status:
            status[st] += 1

        us = float(r.get("urgency_score", 0))
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
    doc = {
        "case_id": case_id,
        "report_text": body.report_text.strip(),
        "urgency_score": urgency_score(body.report_text),
        "status": "pending",
        "created_at": now_utc(),
    }
    reports.insert_one(doc)
    return {"success": True, "case_id": case_id}


@app.get("/api/view_report")
def view_report(case_id: str = Query(..., min_length=8)) -> dict[str, Any]:
    report = reports.find_one({"case_id": case_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    created_at = report.get("created_at")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    return {"case_id": report["case_id"], "status": report.get("status", "pending"), "created_at": created_at}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
