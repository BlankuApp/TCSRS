"""
User profile management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from postgrest.exceptions import APIError

from app.config import DEFAULT_AI_PROMPTS
from app.dependencies.auth import get_current_user, get_jwt_token, require_admin
from app.models.schemas import UserProfile, UserProfileCreate, UserProfileUpdate
from app.services.database import get_user_scoped_client

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("/", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile: UserProfileCreate,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """
    Create a new user profile.
    Profile creation is explicit - called from frontend after user registration.
    """
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Set default AI prompts if not provided
        ai_prompts = profile.ai_prompts if profile.ai_prompts is not None else DEFAULT_AI_PROMPTS
        
        # Build profile data
        profile_data = {
            "user_id": current_user,
            "username": profile.username,
            "avatar": profile.avatar,
            "ai_prompts": ai_prompts,
            "role": "user"  # Default role, only changeable via database
        }
        
        result = db.table("user_profiles").insert(profile_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create profile")
        
        return UserProfile(**result.data[0])
    
    except HTTPException:
        raise
    except APIError as e:
        # Check for unique constraint violation on username
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=UserProfile)
async def get_current_user_profile(
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Get the current user's profile."""
    try:
        db = get_user_scoped_client(jwt_token)
        
        response = db.table("user_profiles").select("*").eq("user_id", current_user).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Please create a profile first."
            )
        
        return UserProfile(**response.data[0])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/", response_model=UserProfile)
async def update_current_user_profile(
    update: UserProfileUpdate,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Update the current user's profile. Role cannot be changed via API."""
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Build update data (only include non-None fields)
        update_data = {}
        if update.username is not None:
            update_data["username"] = update.username
        if update.avatar is not None:
            update_data["avatar"] = update.avatar
        if update.ai_prompts is not None:
            update_data["ai_prompts"] = update.ai_prompts
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        result = db.table("user_profiles").update(update_data).eq("user_id", current_user).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return UserProfile(**result.data[0])
    
    except HTTPException:
        raise
    except APIError as e:
        # Check for unique constraint violation on username
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_profile_by_id(
    user_id: str,
    current_admin: str = Depends(require_admin),
    jwt_token: str = Depends(get_jwt_token)
):
    """
    Admin only: Get any user's profile by user_id.
    """
    try:
        db = get_user_scoped_client(jwt_token)
        
        response = db.table("user_profiles").select("*").eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return UserProfile(**response.data[0])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{user_id}", response_model=UserProfile)
async def update_user_profile_by_id(
    user_id: str,
    update: UserProfileUpdate,
    current_admin: str = Depends(require_admin),
    jwt_token: str = Depends(get_jwt_token)
):
    """
    Admin only: Update any user's profile by user_id.
    Role cannot be changed via API (manual database update only).
    """
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Build update data (only include non-None fields)
        update_data = {}
        if update.username is not None:
            update_data["username"] = update.username
        if update.avatar is not None:
            update_data["avatar"] = update.avatar
        if update.ai_prompts is not None:
            update_data["ai_prompts"] = update.ai_prompts
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        result = db.table("user_profiles").update(update_data).eq("user_id", user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return UserProfile(**result.data[0])
    
    except HTTPException:
        raise
    except APIError as e:
        # Check for unique constraint violation on username
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
