"""
Review endpoints for SRS operations.
"""
from typing import Union
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import (
    QAHintCard, MultipleChoiceCard,
    ReviewSubmission, ReviewResponse
)
from app.services.database import db
from app.services.srs_engine import sample_card, process_review

router = APIRouter(prefix="/review", tags=["review"])


def _card_db_to_schema(card_db: dict) -> Union[QAHintCard, MultipleChoiceCard]:
    """Convert database card representation to Pydantic schema."""
    card_type = card_db.get("card_type")
    card_data = card_db.get("card_data", {})
    
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
async def get_review_card(topic_id: str):
    """
    Get a single card for review from the topic.
    Uses stochastic sampling weighted by intrinsic_weight.
    Returns the full card including answer/correct_index.
    """
    try:
        # Verify topic exists
        topic = db.get_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Get all cards for the topic
        cards = db.get_cards_by_topic(topic_id)
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
async def submit_review(topic_id: str, review: ReviewSubmission):
    """
    Submit a review for a topic.
    Updates the topic's SRS parameters (stability, difficulty, next_review).
    
    Note: This endpoint updates the topic based on the review, not tied to a specific card.
    The card reviewed should be retrieved first via GET /review/topics/{topic_id}/review-card.
    """
    try:
        # Verify topic exists
        topic = db.get_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Get cards to determine intrinsic weight of last reviewed card
        # In a real implementation, you'd track which card was just reviewed
        # For now, we'll sample again to get a representative weight
        cards = db.get_cards_by_topic(topic_id)
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
        updated_topic = db.update_topic(topic_id=topic_id, **updates)
        if not updated_topic:
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
