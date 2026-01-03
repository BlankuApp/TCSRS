"""
JWT authentication dependencies for FastAPI routes.
"""
import os
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

security = HTTPBearer()


def verify_jwt_token(token: str) -> dict:
    """
    Verify and decode a Supabase JWT token.
    
    Args:
        token: The JWT token string
        
    Returns:
        Decoded JWT payload
        
    Raises:
        HTTPException: If token is invalid or expired (401)
    """
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    
    if not jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret not configured"
        )
    
    try:
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=[jwt_algorithm],
            options={"verify_aud": False}  # Supabase tokens don't require aud verification
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Extract and validate the current user from JWT token.
    Returns user_id and role from JWT user_metadata.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        Dict with 'user_id' and 'role' (defaults to 'user' if not in JWT)
        
    Raises:
        HTTPException: If token is missing, invalid, or expired (401)
    """
    token = credentials.credentials
    payload = verify_jwt_token(token)
    
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract role from user_metadata (set by Supabase auth trigger)
    user_metadata = payload.get("user_metadata", {})
    role = user_metadata.get("role", "user")
    
    return {"user_id": user_id, "role": role}


async def get_jwt_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract the raw JWT token from the Authorization header.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        Raw JWT token string
    """
    return credentials.credentials


async def require_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Admin-only dependency. Validates user has admin role from JWT.
    
    Args:
        current_user: User dict with user_id and role from JWT
        
    Returns:
        User dict if user is admin
        
    Raises:
        HTTPException: If user is not admin (403) or token invalid (401)
    """
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user
