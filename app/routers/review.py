"""
Review endpoints for SRS operations.
"""
import json
from datetime import datetime
from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.auth import get_current_user, get_jwt_token
from app.models.schemas import (
    DeckReviewResponse,
    MultipleChoiceCard,
    QAHintCard,
    ReviewCardItem,
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


@router.get("/decks/{deck_id}/cards", response_model=DeckReviewResponse)
async def get_deck_review_cards(
    deck_id: str,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """
    Get up to 100 due cards for review from a deck.
    Returns one card per due topic, ordered by most overdue first.
    All card fields are exposed including answers/correct_index.
    """
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Verify deck exists and user owns it (RLS will handle this)
        deck_response = db.table("decks").select("*").eq("id", deck_id).execute()
        if not deck_response.data:
            raise HTTPException(status_code=404, detail="Deck not found")
        
        # Get due topics (next_review <= now) ordered by most overdue first
        now = datetime.utcnow().isoformat()
        topics_response = (
            db.table("topics")
            .select("*")
            .eq("deck_id", deck_id)
            .lte("next_review", now)
            .order("next_review", desc=False)  # Ascending - most overdue first
            .limit(100)
            .execute()
        )
        
        due_topics = topics_response.data if topics_response.data else []
        
        if not due_topics:
            return DeckReviewResponse(
                cards=[],
                total_due=0,
                deck_id=deck_id
            )
        
        # For each topic, sample one card
        review_cards: List[ReviewCardItem] = []
        for topic in due_topics:
            # Get all cards for this topic
            cards_response = (
                db.table("cards")
                .select("*")
                .eq("topic_id", topic["id"])
                .execute()
            )
            
            cards = cards_response.data if cards_response.data else []
            if not cards:
                continue  # Skip topics with no cards
            
            # Sample one card using weighted sampling
            sampled_card = sample_card(cards)
            if sampled_card:
                review_cards.append(_card_db_to_schema(sampled_card))
        
        return DeckReviewResponse(
            cards=review_cards,
            total_due=len(due_topics),
            deck_id=deck_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cards/{card_id}/submit", response_model=ReviewResponse)
async def submit_card_review(
    card_id: str,
    review: ReviewSubmission,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """
    Submit a review for a specific card.
    Updates the card's parent topic SRS parameters (stability, difficulty, next_review).
    """
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Get the card to retrieve topic_id and intrinsic_weight
        card_response = db.table("cards").select("*").eq("id", card_id).execute()
        if not card_response.data:
            raise HTTPException(status_code=404, detail="Card not found")
        
        card = card_response.data[0]
        topic_id = card["topic_id"]
        intrinsic_weight = card.get("intrinsic_weight", 1.0)
        
        # Get the topic to retrieve current SRS parameters
        topic_response = db.table("topics").select("*").eq("id", topic_id).execute()
        if not topic_response.data:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        topic = topic_response.data[0]
        
        # Process the review and get updated SRS parameters
        updates = process_review(
            topic=topic,
            base_score=review.base_score,
            intrinsic_weight=intrinsic_weight
        )
        
        # Supabase client requires JSON-serializable payloads
        db_updates = {
            key: (value.isoformat() if isinstance(value, datetime) else value)
            for key, value in updates.items()
        }
        
        # Update the topic in the database
        updated_result = db.table("topics").update(db_updates).eq("id", topic_id).execute()
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

