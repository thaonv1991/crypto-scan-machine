"""
Core Security Module
Handles API Key validation and rate limiting.
"""
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from app.core.config import settings
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = getattr(settings, "JWT_SECRET", "super-secret-crypto-key-change-this-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

# OAuth2 for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Clients must pass this header to access our Pro APIs
API_KEY_HEADER = APIKeyHeader(name="X-Scanner-API-Key", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# In a real SaaS, this would check a Database of User Subscriptions.
# For now, we use a Master Key from the environment.
async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """
    Verifies that the incoming request has a valid VIP/Admin API Key.
    """
    master_key = getattr(settings, "MASTER_API_KEY", "pro-vip-key-12345")
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Scanner-API-Key header. Please upgrade to PRO.",
        )
        
    if api_key != master_key:
        # Here we could also check a DB for user-specific keys
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key. Access Denied.",
        )
        
    return api_key
