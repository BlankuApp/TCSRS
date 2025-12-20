"""
Topic management endpoints.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user, get_jwt_token
from app.models.schemas import Topic, TopicCreate, TopicUpdate
from app.services.database import get_user_scoped_client

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("/", response_model=Topic, status_code=status.HTTP_201_CREATED)
async def create_topic(
    topic: TopicCreate,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Create a new topic."""
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Verify deck exists and user owns it (RLS will handle this)
        deck_response = db.table("decks").select("*").eq("id", topic.deck_id).execute()
        if not deck_response.data:
            raise HTTPException(status_code=404, detail="Deck not found")
        
        result = db.table("topics").insert({
            "deck_id": topic.deck_id,
            "name": topic.name,
            "stability": topic.stability,
            "difficulty": topic.difficulty,
            "next_review": datetime.now().isoformat()
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create topic")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deck/{deck_id}", response_model=List[Topic])
async def get_topics_by_deck(
    deck_id: str,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Get all topics in a deck."""
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Verify deck exists and user owns it (RLS will handle this)
        deck_response = db.table("decks").select("*").eq("id", deck_id).execute()
        if not deck_response.data:
            raise HTTPException(status_code=404, detail="Deck not found")
        
        response = db.table("topics").select("*").eq("deck_id", deck_id).execute()
        return response.data if response.data else []
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/due", response_model=List[Topic])
async def get_due_topics(
    limit: int = None,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Get topics that are due for review for the authenticated user."""
    try:
        db = get_user_scoped_client(jwt_token)
        query = db.table("topics").select("*").lte("next_review", datetime.now().isoformat()).order("next_review")
        if limit:
            query = query.limit(limit)
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topic_id}", response_model=Topic)
async def get_topic(
    topic_id: str,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Get a specific topic by ID."""
    try:
        db = get_user_scoped_client(jwt_token)
        response = db.table("topics").select("*").eq("id", topic_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Topic not found")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{topic_id}", response_model=Topic)
async def update_topic(
    topic_id: str,
    topic_update: TopicUpdate,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Update a topic."""
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Build update dict from non-None fields
        update_data = {}
        if topic_update.name is not None:
            update_data["name"] = topic_update.name
        if topic_update.stability is not None:
            update_data["stability"] = topic_update.stability
        if topic_update.difficulty is not None:
            update_data["difficulty"] = topic_update.difficulty
        
        if not update_data:
            # No updates, just fetch and return
            response = db.table("topics").select("*").eq("id", topic_id).execute()
            if not response.data:
                raise HTTPException(status_code=404, detail="Topic not found")
            return response.data[0]
        
        result = db.table("topics").update(update_data).eq("id", topic_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Topic not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: str,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Delete a topic and all its cards."""
    try:
        db = get_user_scoped_client(jwt_token)
        result = db.table("topics").delete().eq("id", topic_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Topic not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
