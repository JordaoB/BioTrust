"""
Authentication API Routes
Handle user registration, login, and session management with persistent sessions
"""

from fastapi import APIRouter, HTTPException, Depends, Response, Request, Header
from backend.database import get_database
from backend.models.session import Session, TokenPair, RefreshTokenRequest
from backend.utils.logger import logger, log_security_event
from pydantic import BaseModel, EmailStr, Field
import hashlib
import secrets
from datetime import datetime, timedelta
from bson import ObjectId
from typing import Optional


router = APIRouter()


# Request/Response Models
class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: str = Field(..., min_length=9, max_length=20)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LogoutRequest(BaseModel):
    access_token: Optional[str] = None


class AuthResponse(BaseModel):
    success: bool
    message: str
    user: dict | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    access_token_expires_at: datetime | None = None
    refresh_token_expires_at: datetime | None = None


# Token configuration
ACCESS_TOKEN_EXPIRE_HOURS = 1  # Short-lived access token
REFRESH_TOKEN_EXPIRE_DAYS = 30  # Long-lived refresh token


def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_token() -> str:
    """Generate secure random token"""
    return secrets.token_urlsafe(48)


async def create_session(user_id: str, email: str, request: Request, db) -> TokenPair:
    """
    Create new session with access and refresh tokens
    Stores session in MongoDB for persistence
    """
    access_token = create_token()
    refresh_token = create_token()
    now = datetime.utcnow()
    
    session_doc = {
        "user_id": user_id,
        "email": email,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "access_token_expires_at": now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "refresh_token_expires_at": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "created_at": now,
        "last_activity": now,
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "is_active": True
    }
    
    await db.sessions.insert_one(session_doc)
    
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=session_doc["access_token_expires_at"],
        refresh_token_expires_at=session_doc["refresh_token_expires_at"]
    )


async def verify_access_token(access_token: str, db) -> dict:
    """
    Verify access token and return session data
    Updates last_activity timestamp
    """
    session = await db.sessions.find_one({
        "access_token": access_token,
        "is_active": True
    })
    
    if not session:
        logger.warning(f"⚠️ Invalid access token attempt | Token: {access_token[:20]}...")
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    
    # Check if access token expired
    if datetime.utcnow() > session["access_token_expires_at"]:
        logger.warning(f"⚠️ Expired access token | User: {session['user_id']}")
        raise HTTPException(
            status_code=401, 
            detail="Access token expired. Use refresh token to get new access token."
        )
    
    # Update last activity
    await db.sessions.update_one(
        {"_id": session["_id"]},
        {"$set": {"last_activity": datetime.utcnow()}}
    )
    
    return session


async def verify_refresh_token(refresh_token: str, db) -> dict:
    """
    Verify refresh token and return session data
    """
    session = await db.sessions.find_one({
        "refresh_token": refresh_token,
        "is_active": True
    })
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Check if refresh token expired
    if datetime.utcnow() > session["refresh_token_expires_at"]:
        # Delete expired session
        await db.sessions.delete_one({"_id": session["_id"]})
        raise HTTPException(status_code=401, detail="Refresh token expired. Please login again.")
    
    return session


@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, request: Request, db=Depends(get_database)):
    """
    Register new user account
    Creates user with default home location (Lisboa) and empty cards
    Returns access and refresh tokens
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    logger.info(f"🔑 Registration attempt | Email: {data.email} | IP: {ip_address}")
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": data.email})
    if existing_user:
        logger.warning(f"⚠️ Registration failed | Email already exists: {data.email} | IP: {ip_address}")
        log_security_event(
            event_type="REGISTRATION_FAILED",
            user_id=data.email,
            ip_address=ip_address,
            user_agent=user_agent,
            details="Email already registered",
            severity="WARNING"
        )
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user document
    user_doc = {
        "name": data.name,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "phone": data.phone,
        "home_location": {
            "city": "Lisboa",
            "country": "Portugal",
            "lat": 38.7223,
            "lon": -9.1393
        },
        "account_age_days": 0,
        "average_transaction": 0.0,
        "max_transaction": 0.0,
        "is_verified": False,
        "cards": [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    try:
        result = await db.users.insert_one(user_doc)
        user_id = str(result.inserted_id)
        
        logger.success(f"✅ User registered | ID: {user_id} | Email: {data.email} | Name: {data.name}")
        log_security_event(
            event_type="REGISTRATION_SUCCESS",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=f"New user: {data.name}",
            severity="INFO"
        )
    except Exception as e:
        logger.error(f"❌ Registration error | Email: {data.email} | Error: {str(e)}")
        print(f"Error inserting user: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Create persistent session with tokens
    tokens = await create_session(user_id, data.email, request, db)
    
    # Return user data (without password)
    user_data = {
        "_id": user_id,
        "name": data.name,
        "email": data.email,
        "phone": data.phone,
        "is_verified": False
    }
    
    return AuthResponse(
        success=True,
        message="Account created successfully",
        user=user_data,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_token_expires_at=tokens.access_token_expires_at,
        refresh_token_expires_at=tokens.refresh_token_expires_at
    )


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, request: Request, db=Depends(get_database)):
    """
    Login with email and password
    Returns access and refresh tokens for authenticated requests
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    logger.info(f"🔑 Login attempt | Email: {data.email} | IP: {ip_address}")
    
    # Find user by email
    user = await db.users.find_one({"email": data.email})
    if not user:
        logger.warning(f"⚠️ Login failed | User not found: {data.email} | IP: {ip_address}")
        log_security_event(
            event_type="LOGIN_FAILED",
            user_id=data.email,
            ip_address=ip_address,
            user_agent=user_agent,
            details="User not found",
            severity="WARNING"
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    password_hash = hash_password(data.password)
    stored_password = user.get("password_hash") or user.get("password")  # Support both old and new format
    if stored_password != password_hash:
        logger.warning(f"⚠️ Login failed | Invalid password: {data.email} | IP: {ip_address}")
        log_security_event(
            event_type="LOGIN_FAILED",
            user_id=str(user["_id"]),
            ip_address=ip_address,
            user_agent=user_agent,
            details="Invalid password",
            severity="WARNING"
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create persistent session with tokens
    user_id = str(user["_id"])
    tokens = await create_session(user_id, data.email, request, db)
    
    logger.success(f"✅ Login successful | User: {user['name']} ({user_id}) | Email: {data.email} | IP: {ip_address}")
    log_security_event(
        event_type="LOGIN_SUCCESS",
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=f"User {user['name']} logged in",
        severity="INFO"
    )
    
    # Return user data (without password)
    user_data = {
        "_id": user_id,
        "name": user["name"],
        "email": user["email"],
        "phone": user.get("phone", ""),
        "is_verified": user.get("is_verified", False),
        "cards": user.get("cards", [])
    }
    
    return AuthResponse(
        success=True,
        message="Login successful",
        user=user_data,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_token_expires_at=tokens.access_token_expires_at,
        refresh_token_expires_at=tokens.refresh_token_expires_at
    )


@router.post("/logout")
async def logout(
    data: Optional[LogoutRequest] = None,
    access_token: Optional[str] = None,
    authorization: Optional[str] = Header(default=None),
    db=Depends(get_database)
):
    """
    Logout and invalidate session tokens
    Marks session as inactive in MongoDB
    """
    token = access_token

    if not token and data and data.access_token:
        token = data.access_token

    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        return {"success": True, "message": "No active session token provided"}

    session = await db.sessions.find_one({"access_token": token})
    
    if session:
        # Mark session as inactive instead of deleting (for audit trail)
        await db.sessions.update_one(
            {"_id": session["_id"]},
            {"$set": {"is_active": False, "logged_out_at": datetime.utcnow()}}
        )
        
        logger.info(f"🚪 Logout | User: {session['user_id']} | Email: {session['email']}")
        log_security_event(
            event_type="LOGOUT",
            user_id=session['user_id'],
            ip_address=session.get('ip_address'),
            details="User logged out",
            severity="INFO"
        )
    
    return {"success": True, "message": "Logged out successfully"}


@router.get("/session/{access_token}")
async def verify_session(access_token: str, db=Depends(get_database)):
    """
    Verify if access token is valid and return user data
    Also updates last_activity timestamp
    """
    session = await verify_access_token(access_token, db)
    
    # Get user data
    user = await db.users.find_one({"_id": ObjectId(session["user_id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return user data (without password)
    user_data = {
        "_id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "phone": user.get("phone", ""),
        "is_verified": user.get("is_verified", False),
        "cards": user.get("cards", [])
    }
    
    return {"success": True, "user": user_data}


@router.post("/refresh", response_model=TokenPair)
async def refresh_access_token(data: RefreshTokenRequest, request: Request, db=Depends(get_database)):
    """
    Refresh access token using valid refresh token
    Returns new access token (keeps same refresh token)
    """
    # Verify refresh token
    session = await verify_refresh_token(data.refresh_token, db)
    
    # Generate new access token
    new_access_token = create_token()
    now = datetime.utcnow()
    new_access_expires = now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    # Update session with new access token
    await db.sessions.update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "access_token": new_access_token,
                "access_token_expires_at": new_access_expires,
                "last_activity": now
            }
        }
    )
    
    return TokenPair(
        access_token=new_access_token,
        refresh_token=session["refresh_token"],  # Keep same refresh token
        access_token_expires_at=new_access_expires,
        refresh_token_expires_at=session["refresh_token_expires_at"]
    )


@router.delete("/sessions/cleanup")
async def cleanup_expired_sessions(db=Depends(get_database)):
    """
    Admin endpoint: Clean up expired sessions from database
    Should be called periodically (e.g., daily cron job)
    """
    now = datetime.utcnow()
    
    # Delete sessions where refresh token is expired
    result = await db.sessions.delete_many({
        "refresh_token_expires_at": {"$lt": now}
    })
    
    return {
        "success": True,
        "message": f"Cleaned up {result.deleted_count} expired sessions"
    }


@router.get("/sessions/active")
async def get_active_sessions(access_token: str, db=Depends(get_database)):
    """
    Get all active sessions for current user
    Useful for showing "logged in devices"
    """
    # Verify access token
    session = await verify_access_token(access_token, db)
    
    # Get all active sessions for this user
    sessions = await db.sessions.find({
        "user_id": session["user_id"],
        "is_active": True
    }).to_list(length=100)
    
    # Format session data (without tokens)
    session_list = []
    for sess in sessions:
        session_list.append({
            "_id": str(sess["_id"]),
            "created_at": sess["created_at"],
            "last_activity": sess["last_activity"],
            "ip_address": sess.get("ip_address"),
            "user_agent": sess.get("user_agent"),
            "is_current": sess["access_token"] == access_token
        })
    
    return {
        "success": True,
        "sessions": session_list
    }


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: str, access_token: str, db=Depends(get_database)):
    """
    Revoke a specific session (logout from specific device)
    User can only revoke their own sessions
    """
    # Verify access token
    current_session = await verify_access_token(access_token, db)
    
    # Find session to revoke
    session_to_revoke = await db.sessions.find_one({"_id": ObjectId(session_id)})
    
    if not session_to_revoke:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if user owns this session
    if session_to_revoke["user_id"] != current_session["user_id"]:
        raise HTTPException(status_code=403, detail="Cannot revoke another user's session")
    
    # Mark session as inactive
    await db.sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"is_active": False, "revoked_at": datetime.utcnow()}}
    )
    
    return {"success": True, "message": "Session revoked successfully"}
