"""
Card management endpoints.
"""
import json
from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user, get_jwt_token
from app.models.schemas import (
    CardUpdate,
    MultipleChoiceCard,
    MultipleChoiceCardCreate,
    QAHintCard,
    QAHintCardCreate,
)
from app.services.database import get_user_scoped_client

router = APIRouter(prefix="/cards", tags=["cards"])


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


@router.post("/", response_model=Union[QAHintCard, MultipleChoiceCard], status_code=status.HTTP_201_CREATED)
async def create_card(
    card: Union[QAHintCardCreate, MultipleChoiceCardCreate],
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Create a new card."""
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Verify topic exists and user owns it (RLS will handle this)
        topic_response = db.table("topics").select("*").eq("id", card.topic_id).execute()
        if not topic_response.data:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Build card_data dict based on card type
        if card.card_type == "qa_hint":
            card_data = {
                "question": card.question,
                "answer": card.answer,
                "hint": card.hint
            }
        elif card.card_type == "multiple_choice":
            card_data = {
                "question": card.question,
                "choices": card.choices,
                "correct_index": card.correct_index
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid card type")
        
        result = db.table("cards").insert({
            "topic_id": card.topic_id,
            "card_type": card.card_type,
            "intrinsic_weight": card.intrinsic_weight,
            "card_data": json.dumps(card_data)
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create card")
        
        return _card_db_to_schema(result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topic/{topic_id}", response_model=List[Union[QAHintCard, MultipleChoiceCard]])
async def get_cards_by_topic(
    topic_id: str,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Get all cards for a topic."""
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Verify topic exists and user owns it (RLS will handle this)
        topic_response = db.table("topics").select("*").eq("id", topic_id).execute()
        if not topic_response.data:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        response = db.table("cards").select("*").eq("topic_id", topic_id).execute()
        cards_db = response.data if response.data else []
        return [_card_db_to_schema(card) for card in cards_db]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{card_id}", response_model=Union[QAHintCard, MultipleChoiceCard])
async def get_card(
    card_id: str,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Get a specific card by ID."""
    try:
        db = get_user_scoped_client(jwt_token)
        response = db.table("cards").select("*").eq("id", card_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Card not found")
        return _card_db_to_schema(response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{card_id}", response_model=Union[QAHintCard, MultipleChoiceCard])
async def update_card(
    card_id: str,
    card_update: CardUpdate,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Update a card (intrinsic_weight only)."""
    try:
        db = get_user_scoped_client(jwt_token)
        
        if card_update.intrinsic_weight is None:
            # No update, just fetch and return
            response = db.table("cards").select("*").eq("id", card_id).execute()
            if not response.data:
                raise HTTPException(status_code=404, detail="Card not found")
            return _card_db_to_schema(response.data[0])
        
        result = db.table("cards").update({
            "intrinsic_weight": card_update.intrinsic_weight
        }).eq("id", card_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Card not found")
        
        return _card_db_to_schema(result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    card_id: str,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Delete a card."""
    try:
        db = get_user_scoped_client(jwt_token)
        result = db.table("cards").delete().eq("id", card_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Card not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
