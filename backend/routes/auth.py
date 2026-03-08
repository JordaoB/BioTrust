"""
Authentication API Routes
Handle user registration and login
"""

from fastapi import APIRouter, HTTPException, Depends, Response
from backend.database import get_database
from pydantic import BaseModel, EmailStr, Field
import hashlib
import secrets
from datetime import datetime, timedelta
from bson import ObjectId


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


class AuthResponse(BaseModel):
    success: bool
    message: str
    user: dict | None = None
    session_token: str | None = None


# Simple session storage (in-memory for demo - use Redis in production)
active_sessions = {}


def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_session_token() -> str:
    """Generate secure session token"""
    return secrets.token_urlsafe(32)


@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, db=Depends(get_database)):
    """
    Register new user account
    Creates user with default home location (Lisboa) and empty cards
    """
    # Check if email already exists
    existing_user = await db.users.find_one({"email": data.email})
    if existing_user:
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
    except Exception as e:
        print(f"Error inserting user: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Create session
    session_token = create_session_token()
    active_sessions[session_token] = {
        "user_id": user_id,
        "email": data.email,
        "expires_at": datetime.utcnow() + timedelta(hours=24)
    }
    
    # Return user data (without password)
    user_data = {
        "_id": user_id,
        "name": data.name,
        "email": data.email,
        "phone": data.phone,
        "balance": 1000.0,
        "is_verified": False
    }
    
    return AuthResponse(
        success=True,
        message="Account created successfully",
        user=user_data,
        session_token=session_token
    )


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db=Depends(get_database)):
    """
    Login with email and password
    Returns session token for authenticated requests
    """
    # Find user by email
    user = await db.users.find_one({"email": data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    password_hash = hash_password(data.password)
    stored_password = user.get("password_hash") or user.get("password")  # Support both old and new format
    if stored_password != password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create session
    session_token = create_session_token()
    user_id = str(user["_id"])
    active_sessions[session_token] = {
        "user_id": user_id,
        "email": data.email,
        "expires_at": datetime.utcnow() + timedelta(hours=24)
    }
    
    # Return user data (without password)
    user_data = {
        "_id": user_id,
        "name": user["name"],
        "email": user["email"],
        "phone": user.get("phone", ""),
        "balance": user.get("balance", 0.0),
        "is_verified": user.get("is_verified", False),
        "cards": user.get("cards", [])
    }
    
    return AuthResponse(
        success=True,
        message="Login successful",
        user=user_data,
        session_token=session_token
    )


@router.post("/logout")
async def logout(session_token: str):
    """
    Logout and invalidate session token
    """
    if session_token in active_sessions:
        del active_sessions[session_token]
    
    return {"success": True, "message": "Logged out successfully"}


@router.get("/session/{session_token}")
async def verify_session(session_token: str, db=Depends(get_database)):
    """
    Verify if session token is valid and return user data
    """
    if session_token not in active_sessions:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    session = active_sessions[session_token]
    
    # Check expiration
    if datetime.utcnow() > session["expires_at"]:
        del active_sessions[session_token]
        raise HTTPException(status_code=401, detail="Session expired")
    
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
        "balance": user.get("balance", 0.0),
        "is_verified": user.get("is_verified", False),
        "cards": user.get("cards", [])
    }
    
    return {"success": True, "user": user_data}
