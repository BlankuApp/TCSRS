"""
Deck management endpoints.
"""
from typing import List
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import Deck, DeckCreate, DeckUpdate
from app.services.database import db

router = APIRouter(prefix="/decks", tags=["decks"])


@router.post("/", response_model=Deck, status_code=status.HTTP_201_CREATED)
async def create_deck(deck: DeckCreate):
    """Create a new deck."""
    try:
        result = db.create_deck(
            name=deck.name,
            user_id=deck.user_id,
            description=deck.description
        )
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create deck")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Deck])
async def get_all_decks(user_id: str = None):
    """Get all decks, optionally filtered by user_id."""
    try:
        decks = db.get_all_decks(user_id=user_id)
        return decks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deck_id}", response_model=Deck)
async def get_deck(deck_id: str):
    """Get a specific deck by ID."""
    try:
        deck = db.get_deck(deck_id)
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        return deck
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{deck_id}", response_model=Deck)
async def update_deck(deck_id: str, deck_update: DeckUpdate):
    """Update a deck."""
    try:
        # Check if deck exists
        existing = db.get_deck(deck_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Deck not found")
        
        result = db.update_deck(
            deck_id=deck_id,
            name=deck_update.name,
            description=deck_update.description
        )
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update deck")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deck(deck_id: str):
    """Delete a deck and all its topics/cards."""
    try:
        # Check if deck exists
        existing = db.get_deck(deck_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Deck not found")
        
        success = db.delete_deck(deck_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete deck")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
