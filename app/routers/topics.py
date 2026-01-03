"""
Topic management endpoints with embedded cards operations.
"""
import json
from datetime import datetime
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import get_current_user, get_jwt_token
from app.models.schemas import (
    CardCreate,
    CardCreateBatch,
    CardItem,
    CardUpdate,
    MultipleChoiceCardCreate,
    QAHintCardCreate,
    Topic,
    TopicCreate,
    TopicListResponse,
    TopicUpdate,
)
from app.services.database import get_user_scoped_client

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("/", response_model=Topic, status_code=status.HTTP_201_CREATED)
async def create_topic(
    topic: TopicCreate,
    current_user: dict = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Create a new topic with optional initial cards."""
    try:
        db = get_user_scoped_client(jwt_token)

        # Verify deck exists and user owns it (RLS will handle this)
        deck_response = db.table("decks").select("*").eq("id", topic.deck_id).execute()
        if not deck_response.data:
            raise HTTPException(status_code=404, detail="Deck not found")

        # Serialize cards to JSONB-compatible format
        cards_json = [card.model_dump() for card in topic.cards]

        result = db.table("topics").insert({
            "deck_id": topic.deck_id,
            "name": topic.name,
            "stability": topic.stability,
            "difficulty": topic.difficulty,
            "next_review": datetime.now().isoformat(),
            "cards": json.dumps(cards_json)
        }).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create topic")

        # Parse cards from JSONB
        topic_data = result.data[0]
        if isinstance(topic_data.get('cards'), str):
            topic_data['cards'] = json.loads(topic_data['cards'])

        return topic_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deck/{deck_id}", response_model=TopicListResponse)
async def get_topics_by_deck(
    deck_id: str,
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=25, ge=1, le=100, description="Number of items per page"),
    sort_by: Literal["name", "difficulty", "stability", "next_review", "last_reviewed", "created_at", "updated_at"] = Query(default="name", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query(default="asc", description="Sort direction"),
    current_user: dict = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Get topics in a deck with pagination and sorting."""
    try:
        db = get_user_scoped_client(jwt_token)

        # Verify deck exists and user owns it (RLS will handle this)
        deck_response = db.table("decks").select("*").eq("id", deck_id).execute()
        if not deck_response.data:
            raise HTTPException(status_code=404, detail="Deck not found")

        # Get total count
        count_response = db.table("topics").select("*", count="exact").eq("deck_id", deck_id).execute()
        total = count_response.count if count_response.count is not None else 0

        # Calculate pagination
        start = (page - 1) * page_size
        end = start + page_size - 1

        # Query with sorting and pagination
        query = db.table("topics").select("*").eq("deck_id", deck_id)
        query = query.order(sort_by, desc=(sort_order == "desc"))
        query = query.range(start, end)
        response = query.execute()

        if response.data:
            # Parse cards JSONB for each topic
            for topic in response.data:
                if isinstance(topic.get('cards'), str):
                    topic['cards'] = json.loads(topic['cards'])

        # Calculate pagination metadata
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        
        return {
            "items": response.data if response.data else [],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/due", response_model=List[Topic])
async def get_due_topics(
    limit: int = None,
    current_user: dict = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Get topics that are due for review for the authenticated user."""
    try:
        db = get_user_scoped_client(jwt_token)
        query = db.table("topics").select("*").lte("next_review", datetime.now().isoformat()).order("next_review")
        if limit:
            query = query.limit(limit)
        response = query.execute()

        if response.data:
            # Parse cards JSONB for each topic
            for topic in response.data:
                if isinstance(topic.get('cards'), str):
                    topic['cards'] = json.loads(topic['cards'])

        return response.data if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topic_id}", response_model=Topic)
async def get_topic(
    topic_id: str,
    current_user: dict = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Get a specific topic by ID with its cards."""
    try:
        db = get_user_scoped_client(jwt_token)
        response = db.table("topics").select("*").eq("id", topic_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Topic not found")

        topic = response.data[0]
        # Parse cards JSONB
        if isinstance(topic.get('cards'), str):
            topic['cards'] = json.loads(topic['cards'])

        return topic
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{topic_id}", response_model=Topic)
async def update_topic(
    topic_id: str,
    topic_update: TopicUpdate,
    current_user: dict = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Update a topic (including replacing entire cards array if provided)."""
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
        if topic_update.cards is not None:
            # Serialize cards to JSONB
            cards_json = [card.model_dump() for card in topic_update.cards]
            update_data["cards"] = json.dumps(cards_json)

        if not update_data:
            # No updates, just fetch and return
            response = db.table("topics").select("*").eq("id", topic_id).execute()
            if not response.data:
                raise HTTPException(status_code=404, detail="Topic not found")
            topic = response.data[0]
            if isinstance(topic.get('cards'), str):
                topic['cards'] = json.loads(topic['cards'])
            return topic

        result = db.table("topics").update(update_data).eq("id", topic_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Topic not found")

        topic = result.data[0]
        # Parse cards JSONB
        if isinstance(topic.get('cards'), str):
            topic['cards'] = json.loads(topic['cards'])

        return topic
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: str,
    current_user: dict = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Delete a topic and all its embedded cards."""
    try:
        db = get_user_scoped_client(jwt_token)
        result = db.table("topics").delete().eq("id", topic_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Topic not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================
# Card Operations (JSONB Array Manipulation)
# =====================

def _build_card_item(card: CardCreate, batch_index: int) -> dict:
    """
    Build a card item dict from CardCreate schema.
    
    Args:
        card: CardCreate instance (QAHintCardCreate or MultipleChoiceCardCreate)
        batch_index: Index of card in batch for error context
        
    Returns:
        dict: Card item ready for JSONB storage
        
    Raises:
        HTTPException: If card validation fails
    """
    try:
        # Build card item based on type
        if isinstance(card, QAHintCardCreate):
            card_data = {
                "question": card.question,
                "answer": card.answer,
                "hint": card.hint
            }
        elif isinstance(card, MultipleChoiceCardCreate):
            # Validate correct_index bounds
            if card.correct_index < 0 or card.correct_index >= len(card.choices):
                raise ValueError(f"correct_index must be between 0 and {len(card.choices) - 1}")
            
            card_data = {
                "question": card.question,
                "choices": card.choices,
                "correct_index": card.correct_index,
                "explanation": card.explanation
            }
        else:
            raise ValueError("Invalid card type")

        return {
            "card_type": card.card_type,
            "intrinsic_weight": card.intrinsic_weight,
            "card_data": card_data
        }
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Card at index {batch_index}: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Card at index {batch_index}: Invalid card data - {str(e)}"
        )


@router.post("/{topic_id}/cards", response_model=CardItem, status_code=status.HTTP_201_CREATED)
async def add_card_to_topic(
    topic_id: str,
    card: CardCreate,
    current_user: dict = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Add a new card to a topic's cards array."""
    try:
        db = get_user_scoped_client(jwt_token)

        # Fetch the topic
        response = db.table("topics").select("*").eq("id", topic_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Topic not found")

        topic = response.data[0]
        cards = topic.get('cards', [])

        # Parse JSONB if string
        if isinstance(cards, str):
            cards = json.loads(cards)

        # Check limit
        if len(cards) >= 25:
            raise HTTPException(status_code=400, detail="Topic already has maximum of 25 cards")

        # Build card using helper
        new_card = _build_card_item(card, 0)

        # Append to cards array
        cards.append(new_card)

        # Update topic with new cards array
        update_result = db.table("topics").update({
            "cards": json.dumps(cards)
        }).eq("id", topic_id).execute()

        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to add card")

        return CardItem(**new_card)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{topic_id}/cards/batch", response_model=Topic, status_code=status.HTTP_201_CREATED)
async def add_cards_batch_to_topic(
    topic_id: str,
    batch: CardCreateBatch,
    current_user: dict = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Add multiple cards to a topic's cards array in batch mode."""
    try:
        db = get_user_scoped_client(jwt_token)

        # Fetch the topic
        response = db.table("topics").select("*").eq("id", topic_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Topic not found")

        topic = response.data[0]
        cards = topic.get('cards', [])

        # Parse JSONB if string
        if isinstance(cards, str):
            cards = json.loads(cards)

        # Determine starting cards based on mode
        if batch.mode == "replace":
            cards = []
            # Validate limit for replace mode
            if len(batch.cards) > 25:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot add {len(batch.cards)} cards. Maximum 25 cards per topic."
                )
        else:  # append mode
            # Validate limit for append mode
            total_cards = len(cards) + len(batch.cards)
            if total_cards > 25:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot add {len(batch.cards)} cards. Topic has {len(cards)} cards, would exceed limit of 25 (total would be {total_cards})."
                )

        # Build all cards using helper with index tracking
        new_cards = []
        for idx, card in enumerate(batch.cards):
            new_card = _build_card_item(card, idx)
            new_cards.append(new_card)

        # Append all new cards to array
        cards.extend(new_cards)

        # Update topic with new cards array
        update_result = db.table("topics").update({
            "cards": json.dumps(cards)
        }).eq("id", topic_id).execute()

        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to add cards")

        # Parse cards from response
        updated_topic = update_result.data[0]
        if isinstance(updated_topic.get('cards'), str):
            updated_topic['cards'] = json.loads(updated_topic['cards'])

        return updated_topic
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topic_id}/cards", response_model=List[CardItem])
async def get_topic_cards(
    topic_id: str,
    current_user: dict = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Get all cards for a topic."""
    try:
        db = get_user_scoped_client(jwt_token)

        response = db.table("topics").select("cards").eq("id", topic_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Topic not found")

        cards = response.data[0].get('cards', [])

        # Parse JSONB if string
        if isinstance(cards, str):
            cards = json.loads(cards)

        return [CardItem(**card) for card in cards]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{topic_id}/cards/{index}", response_model=CardItem)
async def update_card_in_topic(
    topic_id: str,
    index: int,
    card_update: CardUpdate,
    current_user: dict = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Update a card's properties at a specific index."""
    try:
        db = get_user_scoped_client(jwt_token)

        # Fetch the topic
        response = db.table("topics").select("*").eq("id", topic_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Topic not found")

        topic = response.data[0]
        cards = topic.get('cards', [])

        # Parse JSONB if string
        if isinstance(cards, str):
            cards = json.loads(cards)

        # Check index bounds
        if index < 0 or index >= len(cards):
            raise HTTPException(status_code=404, detail=f"Card at index {index} not found")

        card = cards[index]
        card_type = card.get('card_type')
        card_data = card.get('card_data', {})

        # Update intrinsic weight if provided
        if card_update.intrinsic_weight is not None:
            card['intrinsic_weight'] = card_update.intrinsic_weight

        # Update question if provided (applies to both card types)
        if card_update.question is not None:
            card_data['question'] = card_update.question

        # Update QA-specific fields
        if card_type == 'qa_hint':
            if card_update.answer is not None:
                card_data['answer'] = card_update.answer
            if card_update.hint is not None:
                card_data['hint'] = card_update.hint

        # Update Multiple Choice-specific fields
        if card_type == 'multiple_choice':
            if card_update.choices is not None:
                card_data['choices'] = card_update.choices
            if card_update.correct_index is not None:
                # Validate correct_index bounds
                choices = card_update.choices if card_update.choices is not None else card_data.get('choices', [])
                if card_update.correct_index < 0 or card_update.correct_index >= len(choices):
                    raise HTTPException(
                        status_code=400,
                        detail=f"correct_index must be between 0 and {len(choices) - 1}"
                    )
                card_data['correct_index'] = card_update.correct_index
            if card_update.explanation is not None:
                card_data['explanation'] = card_update.explanation

        card['card_data'] = card_data
        cards[index] = card

        # Update topic with modified cards array
        update_result = db.table("topics").update({
            "cards": json.dumps(cards)
        }).eq("id", topic_id).execute()

        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to update card")

        return CardItem(**cards[index])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{topic_id}/cards/{index}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card_from_topic(
    topic_id: str,
    index: int,
    current_user: dict = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Delete a card at a specific index from a topic's cards array."""
    try:
        db = get_user_scoped_client(jwt_token)

        # Fetch the topic
        response = db.table("topics").select("*").eq("id", topic_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Topic not found")

        topic = response.data[0]
        cards = topic.get('cards', [])

        # Parse JSONB if string
        if isinstance(cards, str):
            cards = json.loads(cards)

        # Check index bounds
        if index < 0 or index >= len(cards):
            raise HTTPException(status_code=404, detail=f"Card at index {index} not found")

        # Remove card at index
        cards.pop(index)

        # Update topic with modified cards array
        update_result = db.table("topics").update({
            "cards": json.dumps(cards)
        }).eq("id", topic_id).execute()

        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to delete card")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
