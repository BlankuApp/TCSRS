"""
Database service for Supabase operations.
Provides CRUD functions for decks, topics, and cards.
"""
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import json

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")


class DatabaseService:
    """Singleton service for database operations."""
    
    _instance: Optional['DatabaseService'] = None
    _client: Optional[Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    @property
    def client(self) -> Client:
        """Get Supabase client."""
        return self._client
    
    # =====================
    # Deck Operations
    # =====================
    
    def create_deck(self, name: str, user_id: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new deck."""
        data = {
            "name": name,
            "user_id": user_id,
            "description": description
        }
        response = self.client.table("decks").insert(data).execute()
        return response.data[0] if response.data else None
    
    def get_deck(self, deck_id: str) -> Optional[Dict[str, Any]]:
        """Get a deck by ID."""
        response = self.client.table("decks").select("*").eq("id", deck_id).execute()
        return response.data[0] if response.data else None
    
    def get_all_decks(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all decks, optionally filtered by user_id."""
        query = self.client.table("decks").select("*")
        if user_id:
            query = query.eq("user_id", user_id)
        response = query.execute()
        return response.data if response.data else []
    
    def update_deck(self, deck_id: str, name: Optional[str] = None, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update a deck."""
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        
        if not data:
            return self.get_deck(deck_id)
        
        response = self.client.table("decks").update(data).eq("id", deck_id).execute()
        return response.data[0] if response.data else None
    
    def delete_deck(self, deck_id: str) -> bool:
        """Delete a deck and all its topics/cards (CASCADE)."""
        response = self.client.table("decks").delete().eq("id", deck_id).execute()
        return len(response.data) > 0 if response.data else False
    
    # =====================
    # Topic Operations
    # =====================
    
    def create_topic(self, deck_id: str, name: str, stability: float = 24.0, difficulty: float = 5.0) -> Dict[str, Any]:
        """Create a new topic."""
        data = {
            "deck_id": deck_id,
            "name": name,
            "stability": stability,
            "difficulty": difficulty,
            "next_review": datetime.now().isoformat()
        }
        response = self.client.table("topics").insert(data).execute()
        return response.data[0] if response.data else None
    
    def get_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """Get a topic by ID."""
        response = self.client.table("topics").select("*").eq("id", topic_id).execute()
        return response.data[0] if response.data else None
    
    def get_topics_by_deck(self, deck_id: str) -> List[Dict[str, Any]]:
        """Get all topics in a deck."""
        response = self.client.table("topics").select("*").eq("deck_id", deck_id).execute()
        return response.data if response.data else []
    
    def get_due_topics(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get topics that are due for review."""
        query = self.client.table("topics").select("*").lte("next_review", datetime.now().isoformat()).order("next_review")
        if limit:
            query = query.limit(limit)
        response = query.execute()
        return response.data if response.data else []
    
    def update_topic(self, topic_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a topic with arbitrary fields."""
        if not kwargs:
            return self.get_topic(topic_id)
        
        response = self.client.table("topics").update(kwargs).eq("id", topic_id).execute()
        return response.data[0] if response.data else None
    
    def delete_topic(self, topic_id: str) -> bool:
        """Delete a topic and all its cards (CASCADE)."""
        response = self.client.table("topics").delete().eq("id", topic_id).execute()
        return len(response.data) > 0 if response.data else False
    
    # =====================
    # Card Operations
    # =====================
    
    def create_card(self, topic_id: str, card_type: str, intrinsic_weight: float, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new card with polymorphic card_data."""
        data = {
            "topic_id": topic_id,
            "card_type": card_type,
            "intrinsic_weight": intrinsic_weight,
            "card_data": json.dumps(card_data)
        }
        response = self.client.table("cards").insert(data).execute()
        return response.data[0] if response.data else None
    
    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get a card by ID."""
        response = self.client.table("cards").select("*").eq("id", card_id).execute()
        if response.data:
            card = response.data[0]
            # Parse JSONB card_data
            if isinstance(card.get('card_data'), str):
                card['card_data'] = json.loads(card['card_data'])
            return card
        return None
    
    def get_cards_by_topic(self, topic_id: str) -> List[Dict[str, Any]]:
        """Get all cards for a topic."""
        response = self.client.table("cards").select("*").eq("topic_id", topic_id).execute()
        if response.data:
            # Parse JSONB card_data for each card
            for card in response.data:
                if isinstance(card.get('card_data'), str):
                    card['card_data'] = json.loads(card['card_data'])
            return response.data
        return []
    
    def update_card(self, card_id: str, intrinsic_weight: Optional[float] = None, card_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Update a card."""
        data = {}
        if intrinsic_weight is not None:
            data["intrinsic_weight"] = intrinsic_weight
        if card_data is not None:
            data["card_data"] = json.dumps(card_data)
        
        if not data:
            return self.get_card(card_id)
        
        response = self.client.table("cards").update(data).eq("id", card_id).execute()
        if response.data:
            card = response.data[0]
            if isinstance(card.get('card_data'), str):
                card['card_data'] = json.loads(card['card_data'])
            return card
        return None
    
    def delete_card(self, card_id: str) -> bool:
        """Delete a card."""
        response = self.client.table("cards").delete().eq("id", card_id).execute()
        return len(response.data) > 0 if response.data else False


# Singleton instance
db = DatabaseService()
