"""
Admin router for user role management.
Provides endpoints for admins to manage user roles.
"""
import os
from typing import Literal, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from supabase import create_client, Client

from app.dependencies.auth import require_admin
from app.models.schemas import AddCreditsRequest, UserCreditsResponse

router = APIRouter(prefix="/admin", tags=["admin"])


# Initialize Supabase Admin client
def get_admin_client() -> Client:
    """Get Supabase admin client with service role key."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    
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


class UserInfo(BaseModel):
    """User information for admin list view."""
    id: str
    email: str
    username: str
    avatar: Optional[str]
    role: str
    credits: Optional[float]
    total_spent: Optional[float]
    created_at: str


class UserListResponse(BaseModel):
    """Paginated list of users."""
    items: List[UserInfo]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


@router.post("/users/{user_id}/role", response_model=UserRoleResponse)
async def update_user_role(
    user_id: str,
    role_update: UserRoleUpdate,
    current_user: dict = Depends(require_admin)
) -> UserRoleResponse:
    """
    Update a user's role. Admin only.
    
    Updates the user's `user_metadata.role` in Supabase auth.
    
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
        
        # Update user's user_metadata using Supabase Admin API
        response = admin_client.auth.admin.update_user_by_id(
            user_id,
            {"user_metadata": {"role": role_update.role}}
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


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=25, ge=1, le=100, description="Items per page"),
    sort_by: Literal["email", "username", "role", "created_at"] = Query(default="created_at", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="Sort order"),
    role: Optional[Literal["user", "pro", "admin"]] = Query(default=None, description="Filter by role"),
    search: Optional[str] = Query(default=None, description="Search by email or username (case-insensitive)"),
    current_user: dict = Depends(require_admin)
) -> UserListResponse:
    """
    List all users with pagination, filtering, and search. Admin only.
    
    Retrieves all users from Supabase auth and applies filtering, searching,
    sorting, and pagination.
    
    **Query Parameters:**
    - `page`: Page number (1-based, minimum: 1)
    - `page_size`: Items per page (minimum: 1, maximum: 100)
    - `sort_by`: Field to sort by (email, username, role, created_at)
    - `sort_order`: Sort direction (asc or desc)
    - `role`: Filter by user role (user, pro, admin) - optional
    - `search`: Search in email or username (case-insensitive) - optional
    
    **Returns:**
    Paginated list of users with metadata including:
    - User ID, email, username, avatar, role, created_at
    - Total count, current page, total pages
    - Navigation flags (has_next, has_prev)
    
    **Requirements:**
    - Must be authenticated as admin
    
    **Notes:**
    - Username defaults to "User" if not set
    - Avatar can be null if not set
    - Role defaults to "user" if not set in user_metadata
    - Search is case-insensitive and matches substrings in email or username
    """
    try:
        admin_client = get_admin_client()
        
        # Fetch all users from Supabase
        # Note: list_users() returns paginated results, but we'll fetch all
        # and apply our own filtering/pagination for consistency
        all_users = []
        page_num = 1
        per_page = 1000  # Supabase max per page
        
        while True:
            response = admin_client.auth.admin.list_users(page=page_num, per_page=per_page)
            if not response:
                break
            
            users_batch = response if isinstance(response, list) else getattr(response, 'users', [])
            if not users_batch:
                break
                
            all_users.extend(users_batch)
            
            # If we got fewer users than per_page, we've reached the end
            if len(users_batch) < per_page:
                break
            
            page_num += 1
        
        # Convert to UserInfo objects and apply filters
        user_list = []
        for user in all_users:
            # Extract user data
            user_id = user.id
            email = user.email or ""
            
            # Extract from user_metadata
            raw_user_meta = getattr(user, 'user_metadata', {}) or {}
            username = raw_user_meta.get('username', 'User')
            avatar = raw_user_meta.get('avatar')
            user_role = raw_user_meta.get('role', 'user')
            
            # Extract role from user_metadata
            raw_user_meta = getattr(user, 'user_metadata', {}) or {}
            
            # Extract created_at and convert to string
            created_at_raw = getattr(user, 'created_at', '')
            created_at = created_at_raw.isoformat() if hasattr(created_at_raw, 'isoformat') else str(created_at_raw)
            
            # Extract credits and total_spent from user_metadata
            credits = raw_user_meta.get('credits', 0.0)
            total_spent = raw_user_meta.get('total_spent', 0.0)
            
            # Apply role filter
            if role and user_role != role:
                continue
            
            # Apply search filter (case-insensitive substring match)
            if search:
                search_lower = search.lower()
                if search_lower not in email.lower() and search_lower not in username.lower():
                    continue
            
            user_list.append(UserInfo(
                id=user_id,
                email=email,
                username=username,
                avatar=avatar,
                role=user_role,
                credits=credits,
                total_spent=total_spent,
                created_at=created_at
            ))
        
        # Sort the filtered results
        reverse = (sort_order == "desc")
        if sort_by == "email":
            user_list.sort(key=lambda u: u.email.lower(), reverse=reverse)
        elif sort_by == "username":
            user_list.sort(key=lambda u: u.username.lower(), reverse=reverse)
        elif sort_by == "role":
            user_list.sort(key=lambda u: u.role, reverse=reverse)
        elif sort_by == "created_at":
            user_list.sort(key=lambda u: u.created_at, reverse=reverse)
        
        # Calculate pagination
        total = len(user_list)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        
        # Validate page number
        if page > total_pages and total > 0:
            page = total_pages
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_users = user_list[start_idx:end_idx]
        
        return UserListResponse(
            items=paginated_users,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list users: {str(e)}"
        )


@router.post("/users/{user_id}/credits/add", response_model=UserCreditsResponse)
async def add_credits(
    user_id: str,
    request: AddCreditsRequest,
    current_user: dict = Depends(require_admin)
) -> UserCreditsResponse:
    """
    Add credits to a user's account. Admin only.
    
    Updates the user's `user_metadata.credits` in Supabase auth.
    Credits are rounded to 6 decimal places for precision.
    
    **Requirements:**
    - Must be authenticated as admin
    - Target user must exist in Supabase auth
    - Credits amount must be positive
    
    **Note:** Credits are stored with 6 decimal precision to match cost_usd format.
    """
    try:
        admin_client = get_admin_client()
        
        # Get current user data to retrieve existing credits and total_spent
        user_response = admin_client.auth.admin.get_user_by_id(user_id)
        
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} not found"
            )
        
        user_metadata = user_response.user.user_metadata or {}
        current_credits = user_metadata.get('credits', 0.0)
        total_spent = user_metadata.get('total_spent', 0.0)
        
        # Add credits and round to 6 decimal places
        new_credits = round(current_credits + request.credits, 6)
        
        # Update user_metadata with new credits
        update_response = admin_client.auth.admin.update_user_by_id(
            user_id,
            {"user_metadata": {"credits": new_credits}}
        )
        
        if not update_response:
            raise HTTPException(
                status_code=500,
                detail="Failed to update user credits"
            )
        
        return UserCreditsResponse(
            user_id=user_id,
            credits=new_credits,
            total_spent=total_spent,
            message=f"Successfully added {request.credits} credits. New balance: {new_credits}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add credits: {str(e)}"
        )


@router.get("/users/{user_id}/credits", response_model=UserCreditsResponse)
async def get_user_credits(
    user_id: str,
    current_user: dict = Depends(require_admin)
) -> UserCreditsResponse:
    """
    Get a user's credits information. Admin only.
    
    Retrieves the user's current credits and total_spent from Supabase auth.
    
    **Requirements:**
    - Must be authenticated as admin
    - Target user must exist in Supabase auth
    
    **Returns:**
    - user_id: User's unique identifier
    - credits: Current available credits (6 decimal precision)
    - total_spent: Total credits spent by user (6 decimal precision)
    """
    try:
        admin_client = get_admin_client()
        
        # Get user data
        user_response = admin_client.auth.admin.get_user_by_id(user_id)
        
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} not found"
            )
        
        user_metadata = user_response.user.user_metadata or {}
        credits = user_metadata.get('credits', 0.0)
        total_spent = user_metadata.get('total_spent', 0.0)
        
        return UserCreditsResponse(
            user_id=user_id,
            credits=credits,
            total_spent=total_spent,
            message="Credits retrieved successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve credits: {str(e)}"
        )
