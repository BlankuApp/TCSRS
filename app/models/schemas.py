"""
Pydantic models and schemas for the Topic-Centric SRS API.
All text fields in cards support Markdown formatting.
"""
from datetime import datetime
from typing import Optional, List, Union, Literal
from pydantic import BaseModel, Field, field_validator


class Deck(BaseModel):
    """Represents a deck containing topics."""
    id: str
    name: str
    description: Optional[str] = None
    user_id: str  # Owner of the deck
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DeckCreate(BaseModel):
    """Schema for creating a new deck."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    user_id: str = Field(..., min_length=1)


class DeckUpdate(BaseModel):
    """Schema for updating a deck."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class Topic(BaseModel):
    """Represents a topic with SRS parameters."""
    id: str
    deck_id: str
    name: str
    stability: float = Field(default=24.0, gt=0, description="Memory stability in hours")
    difficulty: float = Field(default=5.0, ge=1, le=10, description="Topic difficulty (1-10)")
    next_review: datetime
    last_reviewed: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TopicCreate(BaseModel):
    """Schema for creating a new topic."""
    deck_id: str
    name: str = Field(..., min_length=1, max_length=255)
    stability: float = Field(default=24.0, gt=0, description="Memory stability in hours")
    difficulty: float = Field(default=5.0, ge=1, le=10, description="Topic difficulty (1-10)")


class TopicUpdate(BaseModel):
    """Schema for updating a topic."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    stability: Optional[float] = Field(None, gt=0)
    difficulty: Optional[float] = Field(None, ge=1, le=10)


class CardBase(BaseModel):
    """Base class for all card types. All text fields render as Markdown in the UI."""
    id: str
    topic_id: str
    card_type: str
    intrinsic_weight: float = Field(
        default=1.0, 
        ge=0.5, 
        le=2.0, 
        description="Intrinsic weight representing card importance (0.5-2.0)"
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class QAHintCard(CardBase):
    """Question-Answer card with optional hint. All fields support Markdown formatting."""
    card_type: Literal["qa_hint"] = "qa_hint"
    question: str = Field(..., description="Question text (Markdown supported)")
    answer: str = Field(..., description="Answer text (Markdown supported)")
    hint: str = Field(default="", description="Optional hint text (Markdown supported)")


class MultipleChoiceCard(CardBase):
    """Multiple choice question card. All text fields support Markdown formatting."""
    card_type: Literal["multiple_choice"] = "multiple_choice"
    question: str = Field(..., description="Question text (Markdown supported)")
    choices: List[str] = Field(..., description="List of answer choices (Markdown supported)")
    correct_index: int = Field(..., description="Index of the correct answer (0-based)")
    
    @field_validator('correct_index')
    @classmethod
    def validate_correct_index(cls, v, info):
        """Ensure correct_index is within bounds of choices list."""
        if 'choices' in info.data:
            choices = info.data['choices']
            if v < 0 or v >= len(choices):
                raise ValueError(f"correct_index must be between 0 and {len(choices) - 1}")
        return v


# Discriminated union for Card types
Card = Union[QAHintCard, MultipleChoiceCard]


class QAHintCardCreate(BaseModel):
    """Schema for creating a QA Hint card."""
    topic_id: str
    card_type: Literal["qa_hint"] = "qa_hint"
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    hint: str = Field(default="")
    intrinsic_weight: float = Field(default=1.0, ge=0.5, le=2.0)


class MultipleChoiceCardCreate(BaseModel):
    """Schema for creating a Multiple Choice card."""
    topic_id: str
    card_type: Literal["multiple_choice"] = "multiple_choice"
    question: str = Field(..., min_length=1)
    choices: List[str] = Field(..., min_items=2)
    correct_index: int = Field(..., ge=0)
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
    """Schema for updating a card (type-agnostic fields only)."""
    intrinsic_weight: Optional[float] = Field(None, ge=0.5, le=2.0)


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
