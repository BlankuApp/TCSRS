"""
Card management endpoints.
"""
from typing import List, Union
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import (
    QAHintCard, MultipleChoiceCard, Card,
    QAHintCardCreate, MultipleChoiceCardCreate, CardCreate, CardUpdate
)
from app.services.database import db

router = APIRouter(prefix="/cards", tags=["cards"])


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


@router.post("/", response_model=Union[QAHintCard, MultipleChoiceCard], status_code=status.HTTP_201_CREATED)
async def create_card(card: Union[QAHintCardCreate, MultipleChoiceCardCreate]):
    """Create a new card."""
    try:
        # Verify topic exists
        topic = db.get_topic(card.topic_id)
        if not topic:
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
        
        result = db.create_card(
            topic_id=card.topic_id,
            card_type=card.card_type,
            intrinsic_weight=card.intrinsic_weight,
            card_data=card_data
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create card")
        
        return _card_db_to_schema(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topic/{topic_id}", response_model=List[Union[QAHintCard, MultipleChoiceCard]])
async def get_cards_by_topic(topic_id: str):
    """Get all cards for a topic."""
    try:
        # Verify topic exists
        topic = db.get_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        cards_db = db.get_cards_by_topic(topic_id)
        return [_card_db_to_schema(card) for card in cards_db]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{card_id}", response_model=Union[QAHintCard, MultipleChoiceCard])
async def get_card(card_id: str):
    """Get a specific card by ID."""
    try:
        card = db.get_card(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        return _card_db_to_schema(card)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{card_id}", response_model=Union[QAHintCard, MultipleChoiceCard])
async def update_card(card_id: str, card_update: CardUpdate):
    """Update a card (intrinsic_weight only)."""
    try:
        # Check if card exists
        existing = db.get_card(card_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Card not found")
        
        result = db.update_card(
            card_id=card_id,
            intrinsic_weight=card_update.intrinsic_weight
        )
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update card")
        
        return _card_db_to_schema(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(card_id: str):
    """Delete a card."""
    try:
        # Check if card exists
        existing = db.get_card(card_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Card not found")
        
        success = db.delete_card(card_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete card")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
