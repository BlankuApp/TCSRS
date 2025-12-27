"""
Review endpoints for SRS operations.
"""
import json
import random
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.auth import get_current_user, get_jwt_token
from app.models.schemas import (
    DeckReviewResponse,
    ReviewCardItem,
    ReviewResponse,
    ReviewSubmission,
)
from app.services.database import get_user_scoped_client
from app.services.srs_engine import process_review, sample_card

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/decks/{deck_id}/cards", response_model=DeckReviewResponse)
async def get_deck_review_cards(
    deck_id: str,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """
    Get up to 100 due cards for review from a deck.
    Returns one card per due topic (with card_index), ordered by most overdue first.
    All card fields are exposed including answers/correct_index.
    """
    try:
        db = get_user_scoped_client(jwt_token)

        # Verify deck exists and user owns it (RLS will handle this)
        deck_response = db.table("decks").select("*").eq("id", deck_id).execute()
        if not deck_response.data:
            raise HTTPException(status_code=404, detail="Deck not found")

        # Get due topics (next_review <= now) with embedded cards, ordered by most overdue first
        now = datetime.now().isoformat()
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

        # For each topic, sample one card from its cards array
        review_cards: List[ReviewCardItem] = []
        for topic in due_topics:
            cards = topic.get('cards', [])

            # Parse JSONB if string
            if isinstance(cards, str):
                cards = json.loads(cards)

            if not cards:
                continue  # Skip topics with no cards

            # Sample one card using weighted sampling
            sampled_card_dict = sample_card(cards)
            if sampled_card_dict:
                # Find the index of the sampled card
                card_index = cards.index(sampled_card_dict)

                review_cards.append(ReviewCardItem(
                    card_index=card_index,
                    topic_id=topic["id"],
                    card_type=sampled_card_dict["card_type"],
                    intrinsic_weight=sampled_card_dict["intrinsic_weight"],
                    card_data=sampled_card_dict["card_data"]
                ))

        return DeckReviewResponse(
            cards=review_cards,
            total_due=len(due_topics),
            deck_id=deck_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decks/{deck_id}/practice", response_model=DeckReviewResponse)
async def get_deck_practice_cards(
    deck_id: str,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """
    Get up to 100 random cards from a deck for practice purposes.
    Returns one card per topic (with card_index), in random order.
    All card fields are exposed including answers/correct_index.
    This endpoint is for practice only and does not affect SRS scheduling.
    """
    try:
        db = get_user_scoped_client(jwt_token)

        # Verify deck exists and user owns it (RLS will handle this)
        deck_response = db.table("decks").select("*").eq("id", deck_id).execute()
        if not deck_response.data:
            raise HTTPException(status_code=404, detail="Deck not found")

        # Get all topics from the deck (no date filtering)
        topics_response = (
            db.table("topics")
            .select("*")
            .eq("deck_id", deck_id)
            .execute()
        )

        all_topics = topics_response.data if topics_response.data else []

        if not all_topics:
            return DeckReviewResponse(
                cards=[],
                total_due=0,
                deck_id=deck_id
            )

        # Shuffle topics randomly and take up to 100
        random.shuffle(all_topics)
        selected_topics = all_topics[:100]

        # For each topic, sample one card from its cards array
        practice_cards: List[ReviewCardItem] = []
        for topic in selected_topics:
            cards = topic.get('cards', [])

            # Parse JSONB if string
            if isinstance(cards, str):
                cards = json.loads(cards)

            if not cards:
                continue  # Skip topics with no cards

            # Sample one card using weighted sampling
            sampled_card_dict = sample_card(cards)
            if sampled_card_dict:
                # Find the index of the sampled card
                card_index = cards.index(sampled_card_dict)

                practice_cards.append(ReviewCardItem(
                    card_index=card_index,
                    topic_id=topic["id"],
                    card_type=sampled_card_dict["card_type"],
                    intrinsic_weight=sampled_card_dict["intrinsic_weight"],
                    card_data=sampled_card_dict["card_data"]
                ))

        return DeckReviewResponse(
            cards=practice_cards,
            total_due=len(practice_cards),
            deck_id=deck_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topics/{topic_id}/cards/{index}/submit", response_model=ReviewResponse)
async def submit_card_review(
    topic_id: str,
    index: int,
    review: ReviewSubmission,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """
    Submit a review for a specific card (identified by topic_id and card index).
    Updates the topic's SRS parameters (stability, difficulty, next_review).
    """
    try:
        db = get_user_scoped_client(jwt_token)

        # Get the topic with its cards
        topic_response = db.table("topics").select("*").eq("id", topic_id).execute()
        if not topic_response.data:
            raise HTTPException(status_code=404, detail="Topic not found")

        topic = topic_response.data[0]
        cards = topic.get('cards', [])

        # Parse JSONB if string
        if isinstance(cards, str):
            cards = json.loads(cards)

        # Validate card index
        if index < 0 or index >= len(cards):
            raise HTTPException(status_code=404, detail=f"Card at index {index} not found")

        # Get the card's intrinsic weight
        card = cards[index]
        intrinsic_weight = card.get("intrinsic_weight", 1.0)

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
