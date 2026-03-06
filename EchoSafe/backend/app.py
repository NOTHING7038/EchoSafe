from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import hashlib
import jwt
import bcrypt
import sqlite3
import numpy as np
from datetime import datetime, timedelta
import os
import json
import base64
from io import BytesIO
import re
from collections import defaultdict
import time
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.units import inch

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ CONFIG ============
DB_PATH = "echosafe.db"
SECRET_KEY = "your-secret-key-change-in-prod"
ALGORITHM = "HS256"
AES_KEY_LENGTH = 32  # 256-bit AES
MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_TIMEOUT = 900  # 15 minutes in seconds
MIN_PASSWORD_LENGTH = 8

# Rate limiting storage (in-memory, replace with Redis in production)
login_attempts = defaultdict(list)

def check_rate_limit(username: str) -> bool:
    """Check if user has exceeded login attempt limit"""
    now = time.time()
    # Clean old attempts
    login_attempts[username] = [t for t in login_attempts[username] if now - t < LOGIN_ATTEMPT_TIMEOUT]
    
    if len(login_attempts[username]) >= MAX_LOGIN_ATTEMPTS:
        return False
    return True

def record_login_attempt(username: str):
    """Record a failed login attempt"""
    login_attempts[username].append(time.time())

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets security requirements"""
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"
    
    if not any(char in "!@#$%^&*()-_=+[]{};:',.<>?/" for char in password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

# ============ DEPENDENCIES ============
def get_db():
    """Database dependency injector"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# ============ DATABASE SETUP ============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Reports table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT UNIQUE NOT NULL,
        encrypted_body BLOB NOT NULL,
        iv BLOB NOT NULL,
        urgency_score REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending'
    )
    """)
    
    # HR Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hr_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_locked INTEGER DEFAULT 0,
        failed_attempts INTEGER DEFAULT 0,
        locked_until TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    """)
    
    # Case tokens table (for report access)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS case_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT UNIQUE NOT NULL,
        token TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(case_id) REFERENCES reports(case_id)
    )
    """)
    
    conn.commit()
    conn.close()

init_db()

# ============ MODELS ============
class ReportSubmission(BaseModel):
    report_text: str

class HRLogin(BaseModel):
    username: str
    password: str

class HRRegister(BaseModel):
    username: str
    password: str

class DecryptReportRequest(BaseModel):
    case_id: str

class UpdateStatusRequest(BaseModel):
    case_id: str
    status: str


# ============ ENCRYPTION/DECRYPTION ============
def encrypt_report(text: str, key: bytes) -> tuple:
    """Encrypt report using AES-256-GCM"""
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(text.encode())
    return ciphertext, cipher.nonce

def decrypt_report(ciphertext: bytes, iv: bytes, key: bytes) -> str:
    """Decrypt report using AES-256-GCM"""
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    plaintext = cipher.decrypt(ciphertext)
    return plaintext.decode()

def generate_case_id() -> str:
    """Generate SHA-256 based anonymous Case ID"""
    random_data = get_random_bytes(32)
    case_id = hashlib.sha256(random_data).hexdigest()
    return case_id

# ============ AI TRIAGE ============
def load_ai_model():
    """
    Placeholder for future TensorFlow model loading
    Currently uses keyword-based scoring
    """
    return None

def score_urgency(text: str) -> float:
    """
    Score report urgency from 0.0 to 1.0
    Finds the highest score based on keyword matching.
    """
    # Keyword scores are based on ai_model/train_model.py
    urgency_keywords = {
        # High priority
        "threat": 0.95, "physical": 0.9, "violence": 0.95, "emergency": 0.9,
        "immediate": 0.85, "danger": 0.85, "attack": 0.95, "weapon": 0.95,
        "hurt": 0.9, "killed": 0.95,
        # Medium priority
        "harassment": 0.65, "discrimination": 0.6, "inappropriate": 0.55,
        "conflict": 0.5, "unfair": 0.45, "complaint": 0.5, "issue": 0.4, "problem": 0.35,
        # Low priority
        "minor": 0.3, "small": 0.25, "feedback": 0.2, "suggestion": 0.15,
        "admin": 0.1, "question": 0.1
    }
    
    text_lower = text.lower()
    score = 0.1  # Default lowest priority
    
    for keyword, value in urgency_keywords.items():
        if keyword in text_lower:
            score = max(score, value)
            
    return float(score)

# ============ JWT AUTHENTICATION ============
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/hr/login")

def create_access_token(username: str, expires_delta: timedelta = None) -> str:
    """Create JWT token for HR user"""
    if expires_delta is None:
        expires_delta = timedelta(hours=24)
    
    expire = datetime.utcnow() + expires_delta
    payload = {"sub": username, "exp": expire}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

async def get_current_username(token: str = Depends(oauth2_scheme)) -> str:
    """Verify JWT token and return username"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token: no subject")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============ ROUTES - REPORTER ============
@app.post("/api/submit_report")
async def submit_report(report: ReportSubmission, conn: sqlite3.Connection = Depends(get_db)):
    """
    Anonymous report submission endpoint
    Returns: case_id and access_token
    """
    try:
        # Generate unique case ID
        case_id = generate_case_id()
        
        # Generate encryption key (in production, derive from case_id with salt)
        encryption_key = hashlib.pbkdf2_hmac('sha256', case_id.encode(), b'salt', 100000)[:32]
        
        # Encrypt report
        ciphertext, iv = encrypt_report(report.report_text, encryption_key)
        
        # Score urgency
        urgency = score_urgency(report.report_text)
        
        # Store in database
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO reports (case_id, encrypted_body, iv, urgency_score)
        VALUES (?, ?, ?, ?)
        """, (case_id, ciphertext, iv, urgency))
        conn.commit()
        
        return {
            "success": True,
            "case_id": case_id,
            "message": "Report submitted successfully. Keep this Case ID safe for future reference."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- analytics helper & route --------------------------------------

def _parse_date(dt_str: Optional[str]) -> Optional[str]:
    if not dt_str:
        return None
    try:
        parts = dt_str.split("-")
        if len(parts) != 3:
            return None
        year, month, day = map(int, parts)
        return f"{year:04d}-{month:02d}-{day:02d}"
    except Exception:
        return None


@app.get("/api/hr/analytics")
async def hr_analytics(
    username: str = Depends(get_current_username),
    start: Optional[str] = None,
    end: Optional[str] = None,
    group: str = "day",
    status: Optional[str] = None,
    priority: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Provide aggregated analytics data for HR dashboard.

    Filtering options are passed via query parameters.
    """
    cursor = conn.cursor()
    filters: List[str] = []
    params: List[Any] = []

    sd = _parse_date(start)
    ed = _parse_date(end)
    if sd:
        filters.append("created_at >= ?")
        params.append(sd + " 00:00:00")
    if ed:
        filters.append("created_at <= ?")
        params.append(ed + " 23:59:59")
    if status:
        filters.append("status = ?")
        params.append(status)

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    if group == "week":
        fmt = "%Y-%W"
    elif group == "month":
        fmt = "%Y-%m"
    else:
        fmt = "%Y-%m-%d"

    cursor.execute(
        f"SELECT strftime('{fmt}', created_at) as period, COUNT(*) FROM reports {where_clause} GROUP BY period ORDER BY period",
        params,
    )
    volume = [{"period": r[0], "count": r[1]} for r in cursor.fetchall()]

    cursor.execute(
        f"SELECT status, COUNT(*) FROM reports {where_clause} GROUP BY status",
        params,
    )
    status_data = {r[0]: r[1] for r in cursor.fetchall()}

    cursor.execute(
        f"SELECT CASE WHEN urgency_score > 0.6 THEN 'high' WHEN urgency_score > 0.3 THEN 'medium' ELSE 'low' END as pr, COUNT(*) "
        f"FROM reports {where_clause} GROUP BY pr",
        params,
    )
    priority_data = {r[0]: r[1] for r in cursor.fetchall()}

    top_reporters: List[Any] = []

    return {
        "volume": volume,
        "status": status_data,
        "priority": priority_data,
        "top_reporters": top_reporters,
    }

@app.get("/api/report/{case_id}")
async def view_report(case_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """
    Retrieve encrypted report (for reporter to verify)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT encrypted_body, iv FROM reports WHERE case_id = ?", (case_id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Report not found")
        
        ciphertext, iv = result
        return {
            "case_id": case_id,
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "iv": base64.b64encode(iv).decode()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ ROUTES - HR DASHBOARD ============
@app.post("/api/hr/register")
async def hr_register(user: HRRegister, conn: sqlite3.Connection = Depends(get_db)):
    """Register HR investigator with password validation"""
    try:
        # Validate input
        if not user.username or len(user.username) < 3:
            raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
        
        if not re.match(r'^[a-zA-Z0-9_.-]+$', user.username):
            raise HTTPException(status_code=400, detail="Username can only contain letters, numbers, dots, hyphens and underscores")
        
        # Validate password strength
        is_strong, message = validate_password_strength(user.password)
        if not is_strong:
            raise HTTPException(status_code=400, detail=message)
        
        password_hash = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt())
        
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO hr_users (username, password_hash, failed_attempts, is_locked)
        VALUES (?, ?, 0, 0)
        """, (user.username, password_hash))
        conn.commit()
        
        return {
            "success": True,
            "message": "HR user registered successfully. You can now login with your credentials."
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/login")
async def hr_login(user: HRLogin, conn: sqlite3.Connection = Depends(get_db)):
    """Login HR investigator with rate limiting and account locking"""
    try:
        # Input validation
        if not user.username or not user.password:
            raise HTTPException(status_code=400, detail="Username and password are required")
        
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, password_hash, is_locked, locked_until, failed_attempts 
        FROM hr_users 
        WHERE username = ?
        """, (user.username,))
        result = cursor.fetchone()
        
        # Check if user exists
        if not result:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        user_id, password_hash, is_locked, locked_until, failed_attempts = result
        
        # Check if account is locked
        if is_locked:
            if locked_until:
                locked_time = datetime.fromisoformat(locked_until)
                if datetime.utcnow() < locked_time:
                    remaining = (locked_time - datetime.utcnow()).seconds
                    raise HTTPException(status_code=423, detail=f"Account locked. Try again in {remaining} seconds")
                else:
                    # Unlock account
                    cursor.execute("""
                    UPDATE hr_users 
                    SET is_locked = 0, failed_attempts = 0, locked_until = NULL 
                    WHERE id = ?
                    """, (user_id,))
                    conn.commit()
            else:
                raise HTTPException(status_code=423, detail="Account is locked. Contact administrator")
        
        # Check rate limiting
        if not check_rate_limit(user.username):
            # Lock account
            lockout_time = datetime.utcnow() + timedelta(seconds=LOGIN_ATTEMPT_TIMEOUT)
            cursor.execute("""
            UPDATE hr_users 
            SET is_locked = 1, locked_until = ? 
            WHERE id = ?
            """, (lockout_time.isoformat(), user_id))
            conn.commit()
            raise HTTPException(status_code=429, detail="Too many failed login attempts. Account locked for 15 minutes")
        
        # Verify password
        if not bcrypt.checkpw(user.password.encode(), password_hash):
            record_login_attempt(user.username)
            cursor.execute("""
            UPDATE hr_users 
            SET failed_attempts = failed_attempts + 1 
            WHERE id = ?
            """, (user_id,))
            conn.commit()
            remaining_attempts = MAX_LOGIN_ATTEMPTS - failed_attempts - 1
            raise HTTPException(status_code=401, detail=f"Invalid username or password. {remaining_attempts} attempts remaining")
        
        # Login successful - reset failed attempts and update last login
        cursor.execute("""
        UPDATE hr_users 
        SET failed_attempts = 0, last_login = CURRENT_TIMESTAMP 
        WHERE id = ?
        """, (user_id,))
        conn.commit()
        
        # Clear rate limit for this user
        if user.username in login_attempts:
            del login_attempts[user.username]
        
        # Create token with expiration
        token = create_access_token(user.username)
        return {
            "success": True,
            "token": token,
            "message": f"Welcome, {user.username}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/logout")
async def hr_logout(username: str = Depends(get_current_username)):
    """Logout HR investigator (client should delete token)"""
    return {
        "success": True,
        "message": "Logged out successfully"
    }

@app.post("/api/hr/change_password")
async def change_password(request: dict, username: str = Depends(get_current_username), conn: sqlite3.Connection = Depends(get_db)):
    """Change password for authenticated user"""
    try:
        old_password = request.get('old_password', '').strip()
        new_password = request.get('new_password', '').strip()
        
        if not old_password or not new_password:
            raise HTTPException(status_code=400, detail="Old and new passwords are required")
        
        # Validate new password strength
        is_strong, message = validate_password_strength(new_password)
        if not is_strong:
            raise HTTPException(status_code=400, detail=f"New password error: {message}")
        
        if old_password == new_password:
            raise HTTPException(status_code=400, detail="New password must be different from old password")
        
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM hr_users WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        password_hash = result[0]
        
        # Verify old password
        if not bcrypt.checkpw(old_password.encode(), password_hash):
            raise HTTPException(status_code=401, detail="Old password is incorrect")
        
        # Update to new password
        new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
        cursor.execute("""
        UPDATE hr_users 
        SET password_hash = ? 
        WHERE username = ?
        """, (new_hash, username))
        conn.commit()
        
        return {
            "success": True,
            "message": "Password changed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hr/dashboard")
async def get_dashboard(username: str = Depends(get_current_username), conn: sqlite3.Connection = Depends(get_db), page: int = 1, limit: int = 20, search: Optional[str] = None):
    """
    Get reports for HR dashboard with pagination
    Requires JWT token
    - page: Page number (1-indexed)
    - limit: Items per page (default 20, max 100)
    """
    try:
        # Validate pagination params
        page = max(1, page)
        limit = min(100, max(1, limit))
        offset = (page - 1) * limit
        
        cursor = conn.cursor()

        # Get total count for pagination info, optionally filtered
        if search:
            cursor.execute("SELECT COUNT(*) FROM reports WHERE case_id LIKE ?", (f"%{search}%",))
            total_count = cursor.fetchone()[0]
            cursor.execute("""
            SELECT case_id, urgency_score, status, created_at 
            FROM reports 
            WHERE case_id LIKE ?
            ORDER BY urgency_score DESC, created_at DESC
            LIMIT ? OFFSET ?
            """, (f"%{search}%", limit, offset))
        else:
            cursor.execute("SELECT COUNT(*) FROM reports")
            total_count = cursor.fetchone()[0]
            cursor.execute("""
            SELECT case_id, urgency_score, status, created_at 
            FROM reports 
            ORDER BY urgency_score DESC, created_at DESC
            LIMIT ? OFFSET ?
            """, (limit, offset))
        reports = cursor.fetchall()
        
        return {
            "investigator": username,
            "reports": [
                {
                    "case_id": r[0],
                    "urgency_score": r[1],
                    "status": r[2],
                    "created_at": r[3]
                }
                for r in reports
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/decrypt_report")
async def decrypt_report_endpoint(request: DecryptReportRequest, username: str = Depends(get_current_username), conn: sqlite3.Connection = Depends(get_db)):
    """
    Decrypt and view full report (HR only)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT encrypted_body, iv FROM reports WHERE case_id = ?", (request.case_id,))
        result = cursor.fetchone()
        
        case_id = request.case_id

        if not result:
            raise HTTPException(status_code=404, detail="Report not found")
        
        ciphertext, iv = result
        
        # Derive key from case_id
        key = hashlib.pbkdf2_hmac('sha256', case_id.encode(), b'salt', 100000)[:32]
        plaintext = decrypt_report(ciphertext, iv, key)
        
        return {
            "case_id": case_id,
            "report_text": plaintext,
            "investigator": username
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/hr/update_status")
async def update_status(request: UpdateStatusRequest, username: str = Depends(get_current_username), conn: sqlite3.Connection = Depends(get_db)):
    """Update report status (pending, investigating, resolved)"""
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE reports SET status = ? WHERE case_id = ?", (request.status, request.case_id))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Case ID {request.case_id} not found")
        
        return {"success": True, "message": f"Status updated to {request.status}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ HEALTH CHECK ============
@app.get("/")
async def root():
    return {"status": "ok", "message": "EchoSafe API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
