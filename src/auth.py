from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from src.config import get_settings
from src.database import get_user_by_email, update_user, create_password_reset_token, get_valid_reset_token, invalidate_reset_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
from src.services.email_service import email_service

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
settings = get_settings()

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    # Simply encode the data without adding expiry
    encoded_jwt = jwt.encode(data, settings.jwt_secret_key, algorithm=settings.algorithm)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if not email:
            raise JWTError
    except (JWTError, AttributeError):
        raise credentials_exception
    
    user = await get_user_by_email(email)
    if user is None:
        raise credentials_exception
        
    # Ensure we return a properly structured dictionary
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "created_at": user["created_at"]
    }

def generate_reset_token() -> str:
    """Generate a secure random token for password reset"""
    return secrets.token_urlsafe(32)

async def request_password_reset(email: str):
    """Handle password reset request"""
    user = await get_user_by_email(email)
    if not user:
        # Return success even if email doesn't exist to prevent email enumeration
        return {"message": "If your email is registered, you will receive a password reset link"}
    
    # Generate token and set expiration
    token = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    # Store token in database
    await create_password_reset_token(user["id"], token, expires_at)
    
    # Send reset email using the email service
    await email_service.send_password_reset_email(email, token)
    
    return {"message": "If your email is registered, you will receive a password reset link"}

async def reset_password(reset_token: str, new_password: str):
    """
    Reset user's password using the reset token
    
    Args:
        reset_token: The password reset token
        new_password: The new password to set
        
    Returns:
        dict: A message indicating success
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    # Verify token
    token_data = await get_valid_reset_token(reset_token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Hash new password
    password_hash = get_password_hash(new_password)
    
    # Update user's password
    await update_user(token_data["user_id"], {"password_hash": password_hash})
    
    # Invalidate the token
    await invalidate_reset_token(reset_token)
    
    return {"message": "Password has been reset successfully"}