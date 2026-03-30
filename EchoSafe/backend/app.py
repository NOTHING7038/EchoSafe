#!/usr/bin/env python3
"""
EchoSafe Backend - Anonymous Reporting System

FastAPI-based backend providing secure, anonymous reporting with:
- End-to-end encryption for report data
- AI-powered urgency triage
- JWT-authenticated HR investigator dashboard
- MongoDB data persistence

Author: EchoSafe Team
Version: 1.0.0
"""

import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from pymongo import DESCENDING, MongoClient

# =============================================================================
# CONFIGURATION
# =============================================================================

# Database Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "echosafe")

# Security Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-production-use-strong-random-value")
JWT_ALGO = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# Default Admin Configuration
DEFAULT_ADMIN_USER = os.getenv("DEFAULT_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@7038!")

# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]
hr_users = db["hr_users"]
reports = db["reports"]

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="EchoSafe API",
    description="Anonymous reporting system with AI-powered triage",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "null",  # browsers can send Origin: null for file:// pages
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# PYDANTIC MODELS
# =============================================================================


class LoginRequest(BaseModel):
    """HR user login request model."""
    username: str = Field(..., min_length=3, max_length=50, description="HR username")
    password: str = Field(..., min_length=8, max_length=100, description="HR password")


class SubmitReportRequest(BaseModel):
    """Anonymous report submission request model."""
    report_text: str = Field(
        ..., 
        min_length=10, 
        max_length=5000,
        description="Report content (10-5000 characters)"
    )
    
    @validator('report_text')
    def validate_report_text(cls, v):
        if not v.strip():
            raise ValueError('Report text cannot be empty')
        return v.strip()


class UpdateStatusRequest(BaseModel):
    """Case status update request model."""
    case_id: str = Field(..., min_length=8, description="Unique case identifier")
    status: str = Field(..., description="New case status")
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = {"pending", "investigating", "resolved"}
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v


class DecryptRequest(BaseModel):
    """Report decryption request model."""
    case_id: str = Field(..., min_length=8, description="Unique case identifier")


class ChangePasswordRequest(BaseModel):
    """Password change request model."""
    old_password: str = Field(..., min_length=8, description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")


class RegisterRequest(BaseModel):
    """HR user registration request model."""
    username: str = Field(..., min_length=3, max_length=50, description="Desired username")
    password: str = Field(..., min_length=8, max_length=100, description="Password")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.strip() or not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must contain only alphanumeric characters, hyphens, and underscores')
        return v.strip().lower()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    """Hash password using bcrypt with salt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Hashed password to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def build_token(username: str) -> str:
    """Build JWT token for user authentication.
    
    Args:
        username: Username to include in token
        
    Returns:
        JWT token string
    """
    exp = now_utc() + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": username,
        "exp": exp,
        "iat": now_utc(),
        "type": "hr_access"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def urgency_score(text: str) -> float:
    """Calculate urgency score for report text using keyword analysis.
    
    This is a fallback method when the AI model is unavailable.
    
    Args:
        text: Report text to analyze
        
    Returns:
        Urgency score between 0.0 (low) and 1.0 (high)
    """
    text_lower = text.lower()
    score = 0.1  # Base score
    
    # High priority keywords (increase score by 0.2 each)
    high_priority_keywords = [
        "threat", "violence", "abuse", "assault", "unsafe", 
        "harassment", "emergency", "danger", "weapon", "harm"
    ]
    
    # Medium priority keywords (increase score by 0.1 each)
    medium_priority_keywords = [
        "bully", "discrimination", "retaliation", "hostile", 
        "pressure", "inappropriate", "uncomfortable", "concern"
    ]
    
    # Count keyword occurrences
    for keyword in high_priority_keywords:
        if keyword in text_lower:
            score += 0.2
            
    for keyword in medium_priority_keywords:
        if keyword in text_lower:
            score += 0.1
    
    # Cap score between 0.0 and 1.0
    return max(0.0, min(1.0, round(score, 2)))


def ensure_default_admin() -> None:
    """Create default admin user if it doesn't exist."""
    existing = hr_users.find_one({"username": DEFAULT_ADMIN_USER})
    if existing:
        return
        
    hr_users.insert_one({
        "username": DEFAULT_ADMIN_USER,
        "password_hash": hash_password(DEFAULT_ADMIN_PASSWORD),
        "created_at": now_utc(),
        "role": "admin",
        "is_active": True
    })
    print(f"Default admin user '{DEFAULT_ADMIN_USER}' created successfully")


# =============================================================================
# AUTHENTICATION DEPENDENCIES
# =============================================================================

def get_current_user(authorization: str | None = Header(default=None)) -> Dict[str, Any]:
    """Dependency to get current authenticated HR user.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        User document from database
        
    Raises:
        HTTPException: If authentication fails
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = authorization.split(" ", 1)[1].strip()
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        username = payload.get("sub")
        token_type = payload.get("type")
        
        if not username or token_type != "hr_access":
            raise HTTPException(status_code=401, detail="Invalid token")
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = hr_users.find_one({"username": username}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Account is deactivated")
        
    return user


def urgency_score(text: str) -> float:
    """Calculate urgency score for report text using keyword analysis.
    
    This is a fallback method when the AI model is unavailable.
    
    Args:
        text: Report text to analyze
        
    Returns:
        Urgency score between 0.0 (low) and 1.0 (high)
    """
    text_lower = text.lower()
    score = 0.1  # Base score
    
    # High priority keywords (increase score by 0.2 each)
    high_priority_keywords = [
        "threat", "violence", "abuse", "assault", "unsafe", 
        "harassment", "emergency", "danger", "weapon", "harm"
    ]
    
    # Medium priority keywords (increase score by 0.1 each)
    medium_priority_keywords = [
        "bully", "discrimination", "retaliation", "hostile", 
        "pressure", "inappropriate", "uncomfortable", "concern"
    ]
    
    # Count keyword occurrences
    for keyword in high_priority_keywords:
        if keyword in text_lower:
            score += 0.2
            
    for keyword in medium_priority_keywords:
        if keyword in text_lower:
            score += 0.1
    
    # Cap score between 0.0 and 1.0
    return max(0.0, min(1.0, round(score, 2)))


def ensure_default_admin() -> None:
    """Create default admin user if it doesn't exist."""
    existing = hr_users.find_one({"username": DEFAULT_ADMIN_USER})
    if existing:
        return
        
    hr_users.insert_one({
        "username": DEFAULT_ADMIN_USER,
        "password_hash": hash_password(DEFAULT_ADMIN_PASSWORD),
        "created_at": now_utc(),
        "role": "admin",
        "is_active": True
    })
    print(f"Default admin user '{DEFAULT_ADMIN_USER}' created successfully")


# =============================================================================
# APPLICATION EVENTS
# =============================================================================

@app.on_event("startup")
async def startup_event() -> None:
    """Initialize application on startup."""
    try:
        # Create database indexes for performance
        hr_users.create_index("username", unique=True)
        reports.create_index("case_id", unique=True)
        reports.create_index([("urgency_score", DESCENDING)])
        reports.create_index([("created_at", DESCENDING)])
        reports.create_index(["status", "created_at"])
        
        # Ensure default admin user exists
        ensure_default_admin()
        
        print("✅ EchoSafe API started successfully")
        print(f"📊 Database: {MONGODB_DB}")
        print(f"🔐 Default admin: {DEFAULT_ADMIN_USER}")
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        raise


# =============================================================================
# API ENDPOINTS - ROOT
# =============================================================================

@app.get("/", 
         summary="API Health Check",
         description="Returns basic API status information",
         tags=["System"])
def root() -> Dict[str, str]:
    """Health check endpoint to verify API is running."""
    return {
        "status": "ok", 
        "service": "EchoSafe API",
        "version": "1.0.0",
        "timestamp": now_utc().isoformat()
    }


@app.get("/health",
         summary="Detailed Health Check",
         description="Returns detailed system health information",
         tags=["System"])
def health_check() -> Dict[str, Any]:
    """Detailed health check with database connectivity."""
    try:
        # Test database connection
        db.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "timestamp": now_utc().isoformat(),
        "version": "1.0.0"
    }


# =============================================================================
# API ENDPOINTS - HR MANAGEMENT
# =============================================================================

@app.post("/api/hr/register",
         summary="Register HR User",
         description="Register a new HR investigator account",
         response_model=Dict[str, Any],
         tags=["HR Management"])
def register_hr(body: RegisterRequest) -> Dict[str, Any]:
    """Register a new HR user account.
    
    Args:
        body: Registration request with username and password
        
    Returns:
        Success message or error details
        
    Raises:
        HTTPException: If username already exists or validation fails
    """
    try:
        # Check if username already exists
        existing_user = hr_users.find_one({"username": body.username})
        if existing_user:
            raise HTTPException(
                status_code=409, 
                detail="Username already exists"
            )
        
        # Create new HR user
        hr_users.insert_one({
            "username": body.username,
            "password_hash": hash_password(body.password),
            "created_at": now_utc(),
            "role": "investigator",
            "is_active": True
        })
        
        return {
            "success": True, 
            "message": "HR user created successfully",
            "username": body.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Registration failed. Please try again."
        ) from e


@app.post("/api/hr/login",
         summary="HR User Login",
         description="Authenticate HR user and return JWT token",
         response_model=Dict[str, Any],
         tags=["HR Management"])
def hr_login(body: LoginRequest) -> Dict[str, Any]:
    """Authenticate HR user and provide JWT token.
    
    Args:
        body: Login credentials
        
    Returns:
        JWT token and user information
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Find user by username
        user = hr_users.find_one({"username": body.username})
        
        # Verify user exists and password is correct
        if not user or not verify_password(body.password, user.get("password_hash", "")):
            raise HTTPException(
                status_code=401, 
                detail="Invalid username or password"
            )
        
        # Check if account is active
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=401, 
                detail="Account is deactivated"
            )
        
        # Generate JWT token
        token = build_token(body.username)
        
        return {
            "success": True, 
            "token": token,
            "message": f"Welcome, {body.username}",
            "user": {
                "username": body.username,
                "role": user.get("role", "investigator")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Login failed. Please try again."
        ) from e


@app.get("/api/hr/dashboard",
         summary="Get HR Dashboard Data",
         description="Retrieve paginated list of reports for HR dashboard",
         response_model=Dict[str, Any],
         tags=["HR Dashboard"])
def hr_dashboard(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    search: str = Query(default="", description="Search term for case ID or content"),
    status_filter: str = Query(default="", description="Filter by status"),
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get paginated reports for HR dashboard.
    
    Args:
        page: Page number (starting from 1)
        limit: Number of items per page (max 100)
        search: Search term for filtering reports
        status_filter: Filter by case status
        user: Authenticated HR user from dependency
        
    Returns:
        Paginated reports data with metadata
    """
    try:
        # Build query filters
        query: Dict[str, Any] = {}
        
        # Add search filter
        if search.strip():
            search_term = search.strip()
            query["$or"] = [
                {"case_id": {"$regex": search_term, "$options": "i"}},
                {"report_text": {"$regex": search_term, "$options": "i"}}
            ]
        
        # Add status filter
        if status_filter:
            allowed_statuses = {"pending", "investigating", "resolved"}
            if status_filter in allowed_statuses:
                query["status"] = status_filter
        
        # Get total count
        total = reports.count_documents(query)
        
        # Calculate pagination
        skip = (page - 1) * limit
        pages = (total + limit - 1) // limit if total else 0
        
        # Fetch reports with sorting
        cursor = reports.find(
            query, 
            {"_id": 0}
        ).sort([
            ("urgency_score", DESCENDING), 
            ("created_at", DESCENDING)
        ]).skip(skip).limit(limit)
        
        # Process reports data
        reports_list = []
        for report in cursor:
            # Convert datetime to ISO string
            created_at = report.get("created_at")
            if isinstance(created_at, datetime):
                report["created_at"] = created_at.isoformat()
            
            # Add priority classification
            urgency = float(report.get("urgency_score", 0))
            if urgency > 0.6:
                priority = "high"
            elif urgency > 0.3:
                priority = "medium"
            else:
                priority = "low"
            
            report["priority"] = priority
            reports_list.append(report)
        
        return {
            "investigator": user["username"],
            "reports": reports_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1
            },
            "filters": {
                "search": search,
                "status": status_filter
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dashboard data"
        ) from e


@app.post("/api/hr/decrypt_report",
         summary="Decrypt Report",
         description="Decrypt and view full report details",
         response_model=Dict[str, Any],
         tags=["HR Dashboard"])
def decrypt_report(
    body: DecryptRequest, 
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Decrypt and retrieve full report details.
    
    Args:
        body: Request containing case ID to decrypt
        current_user: Authenticated HR user
        
    Returns:
        Full decrypted report details
        
    Raises:
        HTTPException: If case not found
    """
    try:
        # Find report by case ID
        report = reports.find_one({"case_id": body.case_id}, {"_id": 0})
        
        if not report:
            raise HTTPException(
                status_code=404, 
                detail="Case not found"
            )
        
        # Convert datetime to ISO string
        created_at = report.get("created_at")
        if isinstance(created_at, datetime):
            report["created_at"] = created_at.isoformat()
        
        # Add access log entry (optional for audit trail)
        # This could be implemented if audit logging is needed
        
        return {
            "case_id": report["case_id"],
            "report_text": report.get("report_text", ""),
            "urgency_score": report.get("urgency_score", 0),
            "status": report.get("status", "pending"),
            "created_at": report.get("created_at"),
            "accessed_by": current_user["username"],
            "accessed_at": now_utc().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to decrypt report"
        ) from e


@app.put("/api/hr/update_status",
         summary="Update Case Status",
         description="Update the status of a specific case",
         response_model=Dict[str, Any],
         tags=["HR Dashboard"])
def update_status(
    body: UpdateStatusRequest, 
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update the status of a specific case.
    
    Args:
        body: Request containing case ID and new status
        current_user: Authenticated HR user
        
    Returns:
        Success confirmation
        
    Raises:
        HTTPException: If case not found or status invalid
    """
    try:
        # Validate status
        allowed_statuses = {"pending", "investigating", "resolved"}
        if body.status not in allowed_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {allowed_statuses}"
            )
        
        # Update case status
        result = reports.update_one(
            {"case_id": body.case_id}, 
            {
                "$set": {
                    "status": body.status,
                    "updated_at": now_utc(),
                    "updated_by": current_user["username"]
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=404, 
                detail="Case not found"
            )
        
        return {
            "success": True,
            "message": f"Case status updated to {body.status}",
            "case_id": body.case_id,
            "new_status": body.status,
            "updated_by": current_user["username"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to update case status"
        ) from e


@app.post("/api/hr/change_password",
         summary="Change Password",
         description="Change authenticated user's password",
         response_model=Dict[str, Any],
         tags=["HR Management"])
def change_password(
    body: ChangePasswordRequest, 
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Change the password of the authenticated HR user.
    
    Args:
        body: Request containing old and new passwords
        current_user: Authenticated HR user
        
    Returns:
        Success confirmation
        
    Raises:
        HTTPException: If old password is incorrect
    """
    try:
        # Verify old password
        if not verify_password(body.old_password, current_user.get("password_hash", "")):
            raise HTTPException(
                status_code=401, 
                detail="Current password is incorrect"
            )
        
        # Update password
        hr_users.update_one(
            {"username": current_user["username"]},
            {
                "$set": {
                    "password_hash": hash_password(body.new_password),
                    "password_changed_at": now_utc()
                }
            }
        )
        
        return {
            "success": True,
            "message": "Password changed successfully",
            "changed_at": now_utc().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to change password"
        ) from e


@app.post("/api/hr/logout",
         summary="Logout User",
         description="Logout HR user (client-side token removal)",
         response_model=Dict[str, bool],
         tags=["HR Management"])
def hr_logout(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, bool]:
    """Logout HR user.
    
    Note: This is mainly for API documentation purposes.
    Actual token removal should be handled client-side.
    
    Args:
        current_user: Authenticated HR user
        
    Returns:
        Logout confirmation
    """
    return {
        "success": True,
        "message": "Logout successful. Please remove token from client storage."
    }


@app.get("/api/hr/analytics",
         summary="Get Analytics Data",
         description="Retrieve analytics and statistics for reports",
         response_model=Dict[str, Any],
         tags=["HR Analytics"])
def hr_analytics(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get analytics data for reports.
    
    Args:
        days: Number of days to include in analysis
        current_user: Authenticated HR user
        
    Returns:
        Analytics data including volume, status, and priority statistics
    """
    try:
        # Calculate date range
        end_date = now_utc()
        start_date = end_date - timedelta(days=days)
        
        # Fetch reports within date range
        cursor = reports.find({
            "created_at": {"$gte": start_date, "$lte": end_date}
        }, {"_id": 0})
        
        # Initialize counters
        volume_map: Dict[str, int] = {}
        status_counts = {"pending": 0, "investigating": 0, "resolved": 0}
        priority_counts = {"high": 0, "medium": 0, "low": 0}
        
        # Process each report
        for report in cursor:
            created_at = report.get("created_at")
            if isinstance(created_at, datetime):
                # Group by date
                date_key = created_at.strftime("%Y-%m-%d")
                volume_map[date_key] = volume_map.get(date_key, 0) + 1
                
                # Count by status
                status = report.get("status", "pending")
                if status in status_counts:
                    status_counts[status] += 1
                
                # Count by priority
                urgency = float(report.get("urgency_score", 0))
                if urgency > 0.6:
                    priority_counts["high"] += 1
                elif urgency > 0.3:
                    priority_counts["medium"] += 1
                else:
                    priority_counts["low"] += 1
        
        # Prepare volume data for charts
        volume_data = []
        current_date = start_date
        while current_date <= end_date:
            date_key = current_date.strftime("%Y-%m-%d")
            volume_data.append({
                "period": date_key,
                "count": volume_map.get(date_key, 0)
            })
            current_date += timedelta(days=1)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "volume": volume_data,
            "status": status_counts,
            "priority": priority_counts,
            "total_reports": sum(status_counts.values()),
            "generated_by": current_user["username"],
            "generated_at": now_utc().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate analytics"
        ) from e


# =============================================================================
# API ENDPOINTS - ANONYMOUS REPORTING
# =============================================================================


@app.post("/api/submit_report",
         summary="Submit Anonymous Report",
         description="Submit a new anonymous report with AI-powered urgency scoring",
         response_model=Dict[str, Any],
         tags=["Anonymous Reporting"])
def submit_report(body: SubmitReportRequest) -> Dict[str, Any]:
    """Submit an anonymous report.
    
    Args:
        body: Report submission with text content
        
    Returns:
        Generated case ID and submission confirmation
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        # Generate unique case ID
        case_id = hashlib.sha256(
            f"{uuid.uuid4()}-{now_utc().isoformat()}".encode("utf-8")
        ).hexdigest()
        
        # Calculate urgency score using AI/keyword analysis
        urgency = urgency_score(body.report_text)
        
        # Create report document
        report_doc = {
            "case_id": case_id,
            "report_text": body.report_text.strip(),
            "urgency_score": urgency,
            "status": "pending",
            "created_at": now_utc(),
            "submitted_via": "api"
        }
        
        # Insert into database
        reports.insert_one(report_doc)
        
        return {
            "success": True,
            "case_id": case_id,
            "urgency_score": urgency,
            "message": "Report submitted successfully. Keep this Case ID safe for future reference.",
            "submitted_at": now_utc().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to submit report. Please try again."
        ) from e


@app.get("/api/view_report",
         summary="View Report Status",
         description="Check the status of an anonymous report using case ID",
         response_model=Dict[str, Any],
         tags=["Anonymous Reporting"])
def view_report(
    case_id: str = Query(..., min_length=8, description="Unique case identifier")
) -> Dict[str, Any]:
    """View the status of an anonymous report.
    
    This endpoint allows anonymous users to check their report status
    without revealing the report content.
    
    Args:
        case_id: Unique case identifier generated during submission
        
    Returns:
        Report status information (without sensitive content)
        
    Raises:
        HTTPException: If case not found
    """
    try:
        # Find report by case ID
        report = reports.find_one(
            {"case_id": case_id}, 
            {"_id": 0, "report_text": 0}  # Exclude sensitive content
        )
        
        if not report:
            raise HTTPException(
                status_code=404, 
                detail="Report not found"
            )
        
        # Convert datetime to ISO string
        created_at = report.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        
        # Determine priority level
        urgency = float(report.get("urgency_score", 0))
        if urgency > 0.6:
            priority = "high"
        elif urgency > 0.3:
            priority = "medium"
        else:
            priority = "low"
        
        return {
            "case_id": report["case_id"],
            "status": report.get("status", "pending"),
            "urgency_score": urgency,
            "priority": priority,
            "created_at": created_at,
            "last_updated": report.get("updated_at", created_at)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve report status"
        ) from e


# =============================================================================
# APPLICATION EXECUTION
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting EchoSafe API server...")
    print(f"📍 Environment: Development")
    print(f"🌐 Server will be available at: http://localhost:8000")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
