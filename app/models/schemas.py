"""
Pydantic models and schemas for the Topic-Centric SRS API.
All text fields in cards support Markdown formatting.
"""
from datetime import datetime
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


class Deck(BaseModel):
    """Represents a deck containing topics."""
    id: str
    name: str
    prompt: str
    user_id: str  # Owner of the deck
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DeckCreate(BaseModel):
    """Schema for creating a new deck."""
    name: str = Field(..., min_length=1, max_length=255)
    prompt: str = Field(..., min_length=1)


class DeckUpdate(BaseModel):
    """Schema for updating a deck."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    prompt: Optional[str] = Field(None, min_length=1)


# =====================
# Card Item Models (no id/timestamps, stored as JSONB in topics)
# =====================

class CardItem(BaseModel):
    """
    Base card item stored in topics.cards JSONB array.
    Contains only card_type, intrinsic_weight, and card_data.
    """
    card_type: Literal["qa_hint", "multiple_choice"]
    intrinsic_weight: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Intrinsic weight representing card importance (0.5-2.0)"
    )
    card_data: Dict = Field(..., description="Type-specific card data (question, answer, choices, etc.)")


class QAHintCardData(BaseModel):
    """Data structure for QA Hint card type."""
    question: str = Field(..., min_length=1, description="Question text (Markdown supported)")
    answer: str = Field(..., min_length=1, description="Answer text (Markdown supported)")
    hint: str = Field(default="", description="Optional hint text (Markdown supported)")


class MultipleChoiceCardData(BaseModel):
    """Data structure for Multiple Choice card type."""
    question: str = Field(..., min_length=1, description="Question text (Markdown supported)")
    choices: List[str] = Field(..., min_items=2, description="List of answer choices (Markdown supported)")
    correct_index: int = Field(..., ge=0, description="Index of the correct answer (0-based)")
    explanation: str = Field(default="", description="Explanation for the correct answer, shown after user answers (Markdown supported)")

    @field_validator('correct_index')
    @classmethod
    def validate_correct_index(cls, v, info):
        """Ensure correct_index is within bounds of choices list."""
        if 'choices' in info.data:
            choices = info.data['choices']
            if v < 0 or v >= len(choices):
                raise ValueError(f"correct_index must be between 0 and {len(choices) - 1}")
        return v


# =====================
# Topic Models
# =====================

class Topic(BaseModel):
    """Represents a topic with SRS parameters and embedded cards."""
    id: str
    deck_id: str
    name: str
    stability: float = Field(default=24.0, gt=0, description="Memory stability in hours")
    difficulty: float = Field(default=5.0, ge=1, le=10, description="Topic difficulty (1-10)")
    next_review: datetime
    last_reviewed: Optional[datetime] = None
    cards: List[CardItem] = Field(default_factory=list, description="Array of cards (max 25)")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('cards')
    @classmethod
    def validate_cards_limit(cls, v):
        """Ensure cards array doesn't exceed 25 items."""
        if len(v) > 25:
            raise ValueError("Topic cannot have more than 25 cards")
        return v


class TopicCreate(BaseModel):
    """Schema for creating a new topic."""
    deck_id: str
    name: str = Field(..., min_length=1, max_length=255)
    stability: float = Field(default=24.0, gt=0, description="Memory stability in hours")
    difficulty: float = Field(default=5.0, ge=1, le=10, description="Topic difficulty (1-10)")
    cards: List[CardItem] = Field(default_factory=list, description="Initial cards (optional, max 25)")

    @field_validator('cards')
    @classmethod
    def validate_cards_limit(cls, v):
        """Ensure cards array doesn't exceed 25 items."""
        if len(v) > 25:
            raise ValueError("Topic cannot have more than 25 cards")
        return v


class TopicUpdate(BaseModel):
    """Schema for updating a topic."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    stability: Optional[float] = Field(None, gt=0)
    difficulty: Optional[float] = Field(None, ge=1, le=10)
    cards: Optional[List[CardItem]] = Field(None, description="Update entire cards array (max 25)")

    @field_validator('cards')
    @classmethod
    def validate_cards_limit(cls, v):
        """Ensure cards array doesn't exceed 25 items."""
        if v is not None and len(v) > 25:
            raise ValueError("Topic cannot have more than 25 cards")
        return v


class TopicListResponse(BaseModel):
    """Paginated response for topics list."""
    items: List[Topic] = Field(..., description="List of topics on current page")
    total: int = Field(..., description="Total number of topics in the deck")
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


# =====================
# Card Create Schemas (for adding cards to topics)
# =====================


class QAHintCardCreate(BaseModel):
    """Schema for creating a QA Hint card to add to a topic."""
    card_type: Literal["qa_hint"] = "qa_hint"
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    hint: str = Field(default="")
    intrinsic_weight: float = Field(default=1.0, ge=0.5, le=2.0)


class MultipleChoiceCardCreate(BaseModel):
    """Schema for creating a Multiple Choice card to add to a topic."""
    card_type: Literal["multiple_choice"] = "multiple_choice"
    question: str = Field(..., min_length=1)
    choices: List[str] = Field(..., min_items=2)
    correct_index: int = Field(..., ge=0)
    explanation: str = Field(default="", description="Explanation for the correct answer (Markdown supported)")
    intrinsic_weight: float = Field(default=1.0, ge=0.5, le=2.0)

    @field_validator('correct_index')
    @classmethod
    def validate_correct_index(cls, v, info):
        """Ensure correct_index is within bounds of choices list."""
        if 'choices' in info.data:
            choices = info.data['choices']
            if v < 0 or v >= len(choices):
                raise ValueError(f"correct_index must be between 0 and {len(choices) - 1}")
        return v


CardCreate = Union[QAHintCardCreate, MultipleChoiceCardCreate]


class CardUpdate(BaseModel):
    """Schema for updating a card's properties."""
    intrinsic_weight: Optional[float] = Field(None, ge=0.5, le=2.0)
    question: Optional[str] = Field(None, min_length=1)
    answer: Optional[str] = Field(None, min_length=1, description="QA cards only")
    hint: Optional[str] = Field(None, description="QA cards only")
    choices: Optional[List[str]] = Field(None, min_items=2, description="Multiple Choice only")
    correct_index: Optional[int] = Field(None, ge=0, description="Multiple Choice only")
    explanation: Optional[str] = Field(None, description="Multiple Choice only")


class CardCreateBatch(BaseModel):
    """Schema for batch adding cards to a topic."""
    cards: List[CardCreate] = Field(..., min_items=1, max_items=25, description="List of cards to add (1-25)")
    mode: Literal["append", "replace"] = Field(default="append", description="append: add to existing cards, replace: clear and add new cards")


# =====================
# Review Models
# =====================

class ReviewCardItem(BaseModel):
    """Card item for review with card index."""
    card_index: int = Field(..., description="Index of the card in the topic's cards array")
    topic_id: str = Field(..., description="ID of the parent topic")
    card_type: Literal["qa_hint", "multiple_choice"]
    intrinsic_weight: float
    card_data: Dict = Field(..., description="Card content (question, answer, choices, etc.)")


class ReviewSubmission(BaseModel):
    """Schema for submitting a review response."""
    base_score: int = Field(..., ge=0, le=3, description="0=Again, 1=Hard, 2=Good, 3=Easy")


class ReviewResponse(BaseModel):
    """Response after submitting a review."""
    topic_id: str
    new_stability: float
    new_difficulty: float
    next_review: datetime
    message: str


class DeckReviewResponse(BaseModel):
    """Response containing cards to review from a deck."""
    cards: List[ReviewCardItem] = Field(..., description="List of cards to review (max 100)")
    total_due: int = Field(..., description="Total number of due topics in the deck")
    deck_id: str = Field(..., description="ID of the deck being reviewed")


# =====================
# User Profile Models
# =====================


class UserProfile(BaseModel):
    """Represents a user profile."""
    user_id: str
    username: str
    avatar: Optional[str] = None
    role: str = Field(default="user", description="User role: 'user' or 'admin'")
    ai_prompts: dict = Field(default_factory=dict, description="Custom AI prompts dictionary")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserProfileCreate(BaseModel):
    """Schema for creating a new user profile."""
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")
    avatar: Optional[str] = Field(None, description="Avatar URL")
    ai_prompts: Optional[dict] = Field(None, description="Custom AI prompts (defaults to DEFAULT_AI_PROMPTS)")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Ensure username contains only alphanumeric characters and underscores."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Username must contain only alphanumeric characters, underscores, and hyphens")
        return v
    
    @field_validator('avatar')
    @classmethod
    def validate_avatar_url(cls, v):
        """Basic URL validation for avatar."""
        if v is not None and v != "":
            if not (v.startswith('http://') or v.startswith('https://')):
                raise ValueError("Avatar must be a valid HTTP/HTTPS URL")
        return v


class UserProfileUpdate(BaseModel):
    """Schema for updating a user profile."""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username (3-50 characters)")
    avatar: Optional[str] = Field(None, description="Avatar URL")
    ai_prompts: Optional[dict] = Field(None, description="Custom AI prompts dictionary")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Ensure username contains only alphanumeric characters and underscores."""
        if v is not None and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Username must contain only alphanumeric characters, underscores, and hyphens")
        return v
    
    @field_validator('avatar')
    @classmethod
    def validate_avatar_url(cls, v):
        """Basic URL validation for avatar."""
        if v is not None and v != "":
            if not (v.startswith('http://') or v.startswith('https://')):
                raise ValueError("Avatar must be a valid HTTP/HTTPS URL")
        return v
