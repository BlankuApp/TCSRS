"""
SRS (Spaced Repetition System) Engine.
Implements stability/difficulty updates and stochastic card sampling.
"""
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Constants
MIN_STABILITY = 2.4  # hours
MAX_STABILITY = 8760.0  # 365 days in hours
MIN_DIFFICULTY = 1.0
MAX_DIFFICULTY = 10.0
EXPECTED_SCORE = 2.0  # "Good" rating
DIFFICULTY_RATE = 0.3


def update_stability(current_stability: float, base_score: int, intrinsic_weight: float) -> float:
    """
    Update stability based on review performance.
    
    Args:
        current_stability: Current stability in hours
        base_score: Base score (0=Again, 1=Hard, 2=Good, 3=Easy)
        intrinsic_weight: Card's intrinsic weight (0.5-2.0)
    
    Returns:
        New stability in hours (bounded by MIN_STABILITY and MAX_STABILITY)
    
    Algorithm:
        If base_score == 0 (Again):
            S = max(2.4 hours, S × 0.5)
        Else:
            effective_score = base_score × intrinsic_weight
            S = S × (1 + effective_score × 0.15)
    """
    if base_score == 0:  # Again - penalize heavily
        new_stability = max(MIN_STABILITY, current_stability * 0.5)
    else:
        effective_score = base_score * intrinsic_weight
        growth_factor = 1 + (effective_score * 0.15)
        new_stability = current_stability * growth_factor
    
    # Apply bounds
    new_stability = max(MIN_STABILITY, min(MAX_STABILITY, new_stability))
    return new_stability


def update_difficulty(current_difficulty: float, base_score: int, intrinsic_weight: float) -> float:
    """
    Update difficulty based on review performance.
    
    Args:
        current_difficulty: Current difficulty (1-10)
        base_score: Base score (0=Again, 1=Hard, 2=Good, 3=Easy)
        intrinsic_weight: Card's intrinsic weight (0.5-2.0)
    
    Returns:
        New difficulty (bounded by MIN_DIFFICULTY and MAX_DIFFICULTY)
    
    Algorithm:
        effective_score = base_score × intrinsic_weight
        D = D - (effective_score - expected_score) × difficulty_rate
    """
    effective_score = base_score * intrinsic_weight
    difficulty_delta = (effective_score - EXPECTED_SCORE) * DIFFICULTY_RATE
    new_difficulty = current_difficulty - difficulty_delta
    
    # Apply bounds
    new_difficulty = max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, new_difficulty))
    return new_difficulty


def calculate_next_review(stability: float, difficulty: float, current_time: Optional[datetime] = None) -> datetime:
    """
    Calculate next review time based on stability and difficulty.
    
    Args:
        stability: Memory stability in hours
        difficulty: Topic difficulty (1-10)
        current_time: Current time (defaults to now)
    
    Returns:
        Next review datetime
    
    Algorithm:
        difficulty_modifier = 1 + (D - 5) × 0.12
        next_review = now + (stability × difficulty_modifier) hours
    """
    if current_time is None:
        current_time = datetime.now()
    
    difficulty_modifier = 1 + (difficulty - 5) * 0.12
    interval_hours = stability * difficulty_modifier
    
    next_review = current_time + timedelta(hours=interval_hours)
    return next_review


def sample_card(cards: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Stochastically sample a single card from a list based on intrinsic weights.
    Uses Python's random.choices() for weighted random selection.
    
    Args:
        cards: List of card dictionaries, each with 'intrinsic_weight' field
    
    Returns:
        A single randomly selected card, or None if cards list is empty
    
    Algorithm:
        Uses random.choices() with weights proportional to intrinsic_weight
    """
    if not cards:
        return None
    
    # Extract weights
    weights = [card.get('intrinsic_weight', 1.0) for card in cards]
    
    # Sample one card
    selected = random.choices(cards, weights=weights, k=1)
    return selected[0]


def process_review(
    topic: Dict[str, Any],
    base_score: int,
    intrinsic_weight: float,
    current_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Process a review and update topic SRS parameters.
    
    Args:
        topic: Topic dictionary with stability, difficulty, etc.
        base_score: Base score (0=Again, 1=Hard, 2=Good, 3=Easy)
        intrinsic_weight: Intrinsic weight of the reviewed card (0.5-2.0)
        current_time: Current time (defaults to now)
    
    Returns:
        Dictionary with updated SRS parameters:
        {
            'stability': float,
            'difficulty': float,
            'next_review': datetime,
            'last_reviewed': datetime
        }
    """
    if current_time is None:
        current_time = datetime.now()
    
    current_stability = topic.get('stability', 24.0)
    current_difficulty = topic.get('difficulty', 5.0)
    
    # Update stability and difficulty
    new_stability = update_stability(current_stability, base_score, intrinsic_weight)
    new_difficulty = update_difficulty(current_difficulty, base_score, intrinsic_weight)
    
    # Calculate next review time
    next_review = calculate_next_review(new_stability, new_difficulty, current_time)
    
    return {
        'stability': new_stability,
        'difficulty': new_difficulty,
        'next_review': next_review,
        'last_reviewed': current_time
    }


def get_effective_score(base_score: int, intrinsic_weight: float) -> float:
    """
    Calculate effective score from base score and intrinsic weight.
    
    Args:
        base_score: Base score (0=Again, 1=Hard, 2=Good, 3=Easy)
        intrinsic_weight: Card's intrinsic weight (0.5-2.0)
    
    Returns:
        Effective score (base_score × intrinsic_weight)
    """
    return base_score * intrinsic_weight
