"""
Admin router for user role management.
Provides endpoints for admins to manage user roles.
"""
import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client

from app.dependencies.auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


# Initialize Supabase Admin client
def get_admin_client() -> Client:
    """Get Supabase admin client with service role key."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_service_key:
        raise HTTPException(
            status_code=500,
            detail="Supabase admin credentials not configured"
        )
    
    return create_client(supabase_url, supabase_service_key)


class UserRoleUpdate(BaseModel):
    """Schema for updating a user's role."""
    role: Literal["user", "pro", "admin"] = "user"


class UserRoleResponse(BaseModel):
    """Response after updating a user's role."""
    user_id: str
    role: str
    message: str


@router.post("/users/{user_id}/role", response_model=UserRoleResponse)
async def update_user_role(
    user_id: str,
    role_update: UserRoleUpdate,
    current_user: dict = Depends(require_admin)
) -> UserRoleResponse:
    """
    Update a user's role. Admin only.
    
    Updates the user's `app_metadata.role` in Supabase auth.
    
    **Allowed Roles:**
    - `user`: Default role (free tier)
    - `pro`: Premium user with server-side AI keys
    - `admin`: Administrator with full access
    
    **Requirements:**
    - Must be authenticated as admin
    - Target user must exist in Supabase auth
    
    **Note:** Role changes take effect immediately but require the user
    to refresh their JWT token (re-login) to see the changes.
    """
    try:
        admin_client = get_admin_client()
        
        # Update user's app_metadata using Supabase Admin API
        response = admin_client.auth.admin.update_user_by_id(
            user_id,
            {"app_metadata": {"role": role_update.role}}
        )
        
        if not response:
            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} not found"
            )
        
        return UserRoleResponse(
            user_id=user_id,
            role=role_update.role,
            message=f"Role updated to '{role_update.role}' successfully. User must re-login for changes to take effect."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update user role: {str(e)}"
        )
