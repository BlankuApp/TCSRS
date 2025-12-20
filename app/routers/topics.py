"""
Topic management endpoints.
"""
from typing import List
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import Topic, TopicCreate, TopicUpdate
from app.services.database import db

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("/", response_model=Topic, status_code=status.HTTP_201_CREATED)
async def create_topic(topic: TopicCreate):
    """Create a new topic."""
    try:
        # Verify deck exists
        deck = db.get_deck(topic.deck_id)
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        
        result = db.create_topic(
            deck_id=topic.deck_id,
            name=topic.name,
            stability=topic.stability,
            difficulty=topic.difficulty
        )
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create topic")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deck/{deck_id}", response_model=List[Topic])
async def get_topics_by_deck(deck_id: str):
    """Get all topics in a deck."""
    try:
        # Verify deck exists
        deck = db.get_deck(deck_id)
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        
        topics = db.get_topics_by_deck(deck_id)
        return topics
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/due", response_model=List[Topic])
async def get_due_topics(limit: int = None):
    """Get topics that are due for review."""
    try:
        topics = db.get_due_topics(limit=limit)
        return topics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topic_id}", response_model=Topic)
async def get_topic(topic_id: str):
    """Get a specific topic by ID."""
    try:
        topic = db.get_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        return topic
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{topic_id}", response_model=Topic)
async def update_topic(topic_id: str, topic_update: TopicUpdate):
    """Update a topic."""
    try:
        # Check if topic exists
        existing = db.get_topic(topic_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Build update dict from non-None fields
        update_data = {}
        if topic_update.name is not None:
            update_data["name"] = topic_update.name
        if topic_update.stability is not None:
            update_data["stability"] = topic_update.stability
        if topic_update.difficulty is not None:
            update_data["difficulty"] = topic_update.difficulty
        
        result = db.update_topic(topic_id=topic_id, **update_data)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update topic")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(topic_id: str):
    """Delete a topic and all its cards."""
    try:
        # Check if topic exists
        existing = db.get_topic(topic_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        success = db.delete_topic(topic_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete topic")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
