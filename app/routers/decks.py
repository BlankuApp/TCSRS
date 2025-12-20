"""
Deck management endpoints.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user, get_jwt_token
from app.models.schemas import Deck, DeckCreate, DeckUpdate
from app.services.database import get_user_scoped_client

router = APIRouter(prefix="/decks", tags=["decks"])


@router.post("/", response_model=Deck, status_code=status.HTTP_201_CREATED)
async def create_deck(
    deck: DeckCreate,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Create a new deck."""
    try:
        db = get_user_scoped_client(jwt_token)
        result = db.table("decks").insert({
            "name": deck.name,
            "description": deck.description,
            "user_id": current_user
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create deck")
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Deck])
async def get_all_decks(
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Get all decks for the authenticated user."""
    try:
        db = get_user_scoped_client(jwt_token)
        response = db.table("decks").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deck_id}", response_model=Deck)
async def get_deck(
    deck_id: str,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Get a specific deck by ID."""
    try:
        db = get_user_scoped_client(jwt_token)
        response = db.table("decks").select("*").eq("id", deck_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Deck not found")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{deck_id}", response_model=Deck)
async def update_deck(
    deck_id: str,
    deck_update: DeckUpdate,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Update a deck."""
    try:
        db = get_user_scoped_client(jwt_token)
        
        # Build update data
        data = {}
        if deck_update.name is not None:
            data["name"] = deck_update.name
        if deck_update.description is not None:
            data["description"] = deck_update.description
        
        if not data:
            # No updates, just fetch and return
            response = db.table("decks").select("*").eq("id", deck_id).execute()
            if not response.data:
                raise HTTPException(status_code=404, detail="Deck not found")
            return response.data[0]
        
        result = db.table("decks").update(data).eq("id", deck_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Deck not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deck(
    deck_id: str,
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
):
    """Delete a deck and all its topics/cards."""
    try:
        db = get_user_scoped_client(jwt_token)
        result = db.table("decks").delete().eq("id", deck_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Deck not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
