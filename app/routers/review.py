"""
Review endpoints for SRS operations.
"""
import json
from typing import Union

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.auth import get_current_user, get_jwt_token
from app.models.schemas import (
    MultipleChoiceCard,
    QAHintCard,
    ReviewResponse,
    ReviewSubmission,
)
from app.services.database import get_user_scoped_client
from app.services.srs_engine import process_review, sample_card

router = APIRouter(prefix="/review", tags=["review"])


def _card_db_to_schema(card_db: dict) -> Union[QAHintCard, MultipleChoiceCard]:
    """Convert database card representation to Pydantic schema."""
    card_type = card_db.get("card_type")
    card_data = card_db.get("card_data", {})
    
    # Parse JSONB if needed
    if isinstance(card_data, str):
        card_data = json.loads(card_data)
    
    base_fields = {
        "id": card_db["id"],
        "topic_id": card_db["topic_id"],
        "card_type": card_type,
        "intrinsic_weight": card_db.get("intrinsic_weight", 1.0),
        "created_at": card_db.get("created_at"),
        "updated_at": card_db.get("updated_at")
    }
    
    if card_type == "qa_hint":
        return QAHintCard(
            **base_fields,
            question=card_data.get("question", ""),
            answer=card_data.get("answer", ""),
            hint=card_data.get("hint", "")
        )
    elif card_type == "multiple_choice":
        return MultipleChoiceCard(
            **base_fields,
            question=card_data.get("question", ""),
            choices=card_data.get("choices", []),
            correct_index=card_data.get("correct_index", 0)
        )
    else:
        raise ValueError(f"Unknown card type: {card_type}")


@router.get("/topics/{topic_id}/review-card", response_model=Union[QAHintCard, MultipleChoiceCard])
async def get_review_card(
    topic_id: str,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """
    Get a single card for review from the topic.
    Uses stochastic sampling weighted by intrinsic_weight.
    Returns the full card including answer/correct_index.
    """
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Verify topic exists and user owns it (RLS will handle this)
        topic_response = db.table("topics").select("*").eq("id", topic_id).execute()
        if not topic_response.data:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Get all cards for the topic
        cards_response = db.table("cards").select("*").eq("topic_id", topic_id).execute()
        cards = cards_response.data if cards_response.data else []
        
        if not cards:
            raise HTTPException(status_code=404, detail="No cards found for this topic")
        
        # Sample one card using stochastic weighted sampling
        selected_card = sample_card(cards)
        if not selected_card:
            raise HTTPException(status_code=500, detail="Failed to sample card")
        
        return _card_db_to_schema(selected_card)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topics/{topic_id}/submit-review", response_model=ReviewResponse)
async def submit_review(
    topic_id: str,
    review: ReviewSubmission,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """
    Submit a review for a topic.
    Updates the topic's SRS parameters (stability, difficulty, next_review).
    
    Note: This endpoint updates the topic based on the review, not tied to a specific card.
    The card reviewed should be retrieved first via GET /review/topics/{topic_id}/review-card.
    """
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Verify topic exists and user owns it (RLS will handle this)
        topic_response = db.table("topics").select("*").eq("id", topic_id).execute()
        if not topic_response.data:
            raise HTTPException(status_code=404, detail="Topic not found")
        topic = topic_response.data[0]
        
        # Get cards to determine intrinsic weight of last reviewed card
        # In a real implementation, you'd track which card was just reviewed
        # For now, we'll sample again to get a representative weight
        cards_response = db.table("cards").select("*").eq("topic_id", topic_id).execute()
        cards = cards_response.data if cards_response.data else []
        
        if not cards:
            raise HTTPException(status_code=404, detail="No cards found for this topic")
        
        # Sample card to get intrinsic weight
        # NOTE: In production, you should pass card_id with the review submission
        # to know exactly which card was reviewed
        sampled_card = sample_card(cards)
        intrinsic_weight = sampled_card.get("intrinsic_weight", 1.0)
        
        # Process the review and get updated SRS parameters
        updates = process_review(
            topic=topic,
            base_score=review.base_score,
            intrinsic_weight=intrinsic_weight
        )
        
        # Update the topic in the database
        updated_result = db.table("topics").update(updates).eq("id", topic_id).execute()
        if not updated_result.data:
            raise HTTPException(status_code=500, detail="Failed to update topic")
        
        return ReviewResponse(
            topic_id=topic_id,
            new_stability=updates["stability"],
            new_difficulty=updates["difficulty"],
            next_review=updates["next_review"],
            message=f"Review submitted successfully. Next review scheduled for {updates['next_review'].isoformat()}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
