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
) -> str:
    """
    Extract and validate the current user from JWT token.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        User ID (sub claim from JWT)
        
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
    
    return user_id


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


async def get_current_user_with_role(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Tuple[str, str]:
    """
    Extract user ID and role from JWT token.
    For role-based access control.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        Tuple of (user_id, role) where role defaults to 'user'
        
    Raises:
        HTTPException: If token is invalid or expired (401)
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
    
    # Note: Role is stored in user_profiles table, not JWT
    # For now, return a default role. Endpoints will query the database for actual role.
    role = payload.get("role", "user")
    
    return user_id, role


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_token: str = Depends(get_jwt_token)
) -> str:
    """
    Admin-only dependency. Validates user has admin role.
    Queries user_profiles table to verify role.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        jwt_token: Raw JWT token for database queries
        
    Returns:
        User ID if user is admin
        
    Raises:
        HTTPException: If user is not admin (403) or token invalid (401)
    """
    from app.services.database import get_user_scoped_client
    
    token = credentials.credentials
    payload = verify_jwt_token(token)
    
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Query user_profiles table for role
    try:
        db = get_user_scoped_client(jwt_token)
        response = db.table("user_profiles").select("role").eq("user_id", user_id).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile not found. Please create a profile first."
            )
        
        role = response.data[0].get("role", "user")
        
        if role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return user_id
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying admin status: {str(e)}"
        )
