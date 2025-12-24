"""
Database service for Supabase operations.
Provides CRUD functions for decks, topics (with embedded cards), and user profiles.
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")


def get_user_scoped_client(jwt_token: str) -> Client:
    """
    Create a Supabase client with the user's JWT token for RLS enforcement.

    Args:
        jwt_token: The user's JWT token from authentication

    Returns:
        Supabase client configured with user's JWT
    """
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    # Set the JWT token for RLS enforcement
    supabase.postgrest.auth(jwt_token)
    return supabase


def _parse_topic_cards(topic: Dict[str, Any]) -> Dict[str, Any]:
    """Parse cards JSONB field in topic if it's a string."""
    if isinstance(topic.get('cards'), str):
        topic['cards'] = json.loads(topic['cards'])
    return topic


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

    def create_deck(self, name: str, user_id: str, prompt: str) -> Dict[str, Any]:
        """Create a new deck."""
        data = {
            "name": name,
            "user_id": user_id,
            "prompt": prompt
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

    def update_deck(self, deck_id: str, name: Optional[str] = None, prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update a deck."""
        data = {}
        if name is not None:
            data["name"] = name
        if prompt is not None:
            data["prompt"] = prompt

        if not data:
            return self.get_deck(deck_id)

        response = self.client.table("decks").update(data).eq("id", deck_id).execute()
        return response.data[0] if response.data else None

    def delete_deck(self, deck_id: str) -> bool:
        """Delete a deck and all its topics (CASCADE)."""
        response = self.client.table("decks").delete().eq("id", deck_id).execute()
        return len(response.data) > 0 if response.data else False

    # =====================
    # Topic Operations (with embedded cards)
    # =====================

    def create_topic(
        self,
        deck_id: str,
        name: str,
        stability: float = 24.0,
        difficulty: float = 5.0,
        cards: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Create a new topic with optional initial cards."""
        data = {
            "deck_id": deck_id,
            "name": name,
            "stability": stability,
            "difficulty": difficulty,
            "next_review": datetime.now().isoformat(),
            "cards": json.dumps(cards if cards is not None else [])
        }
        response = self.client.table("topics").insert(data).execute()
        if response.data:
            return _parse_topic_cards(response.data[0])
        return None

    def get_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """Get a topic by ID with parsed cards."""
        response = self.client.table("topics").select("*").eq("id", topic_id).execute()
        if response.data:
            return _parse_topic_cards(response.data[0])
        return None

    def get_topics_by_deck(self, deck_id: str) -> List[Dict[str, Any]]:
        """Get all topics in a deck with parsed cards."""
        response = self.client.table("topics").select("*").eq("deck_id", deck_id).execute()
        if response.data:
            return [_parse_topic_cards(topic) for topic in response.data]
        return []

    def get_due_topics(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get topics that are due for review with parsed cards."""
        query = self.client.table("topics").select("*").lte("next_review", datetime.now().isoformat()).order("next_review")
        if limit:
            query = query.limit(limit)
        response = query.execute()
        if response.data:
            return [_parse_topic_cards(topic) for topic in response.data]
        return []

    def update_topic(self, topic_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a topic with arbitrary fields. Serializes cards if provided."""
        if not kwargs:
            return self.get_topic(topic_id)

        # Serialize cards if provided
        if 'cards' in kwargs:
            kwargs['cards'] = json.dumps(kwargs['cards'])

        response = self.client.table("topics").update(kwargs).eq("id", topic_id).execute()
        if response.data:
            return _parse_topic_cards(response.data[0])
        return None

    def delete_topic(self, topic_id: str) -> bool:
        """Delete a topic."""
        response = self.client.table("topics").delete().eq("id", topic_id).execute()
        return len(response.data) > 0 if response.data else False

    # =====================
    # Card Array Operations (Helpers for JSONB manipulation)
    # =====================

    def append_card_to_topic(self, topic_id: str, card: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Append a card to a topic's cards array."""
        topic = self.get_topic(topic_id)
        if not topic:
            return None

        cards = topic.get('cards', [])
        if len(cards) >= 25:
            raise ValueError("Topic already has maximum of 25 cards")

        cards.append(card)
        return self.update_topic(topic_id, cards=cards)

    def update_card_in_topic(self, topic_id: str, index: int, card_updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a card at a specific index in a topic's cards array."""
        topic = self.get_topic(topic_id)
        if not topic:
            return None

        cards = topic.get('cards', [])
        if index < 0 or index >= len(cards):
            raise IndexError(f"Card index {index} out of bounds")

        # Update the card
        cards[index].update(card_updates)
        return self.update_topic(topic_id, cards=cards)

    def delete_card_from_topic(self, topic_id: str, index: int) -> Optional[Dict[str, Any]]:
        """Delete a card at a specific index from a topic's cards array."""
        topic = self.get_topic(topic_id)
        if not topic:
            return None

        cards = topic.get('cards', [])
        if index < 0 or index >= len(cards):
            raise IndexError(f"Card index {index} out of bounds")

        # Remove the card
        cards.pop(index)
        return self.update_topic(topic_id, cards=cards)


# Singleton instance
db = DatabaseService()
