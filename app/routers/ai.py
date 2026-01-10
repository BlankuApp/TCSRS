"""
AI router for card generation endpoints.
Provides endpoints for AI-powered flashcard generation using various providers.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.config import (
    AI_PROVIDERS,
    CARD_FORMAT_PROMPT,
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
)
from app.dependencies.auth import get_current_user
from app.models.schemas import (
    AIModel,
    AIProviderInfo,
    AIProvidersResponse,
    GenerateCardsRequest,
    GenerateCardsResponse,
    GeneratedCard,
)
from app.services.ai_service import generate_cards_with_ai, resolve_api_key

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/providers", response_model=AIProvidersResponse)
async def get_providers(
    current_user: dict = Depends(get_current_user)
) -> AIProvidersResponse:
    """
    Get all available AI providers and their models.
    
    Returns a list of providers with their available models,
    along with default provider and model settings.
    """
    providers = []
    
    for provider_id, config in AI_PROVIDERS.items():
        models = [
            AIModel(id=model["id"], name=model["name"])
            for model in config["models"]
        ]
        providers.append(
            AIProviderInfo(
                id=provider_id,
                display_name=config["display_name"],
                models=models
            )
        )
    
    return AIProvidersResponse(
        providers=providers,
        default_provider=DEFAULT_PROVIDER,
        default_model=DEFAULT_MODEL
    )


@router.post("/generate-cards", response_model=GenerateCardsResponse, status_code=201)
async def generate_cards(
    request: GenerateCardsRequest,
    current_user: dict = Depends(get_current_user)
) -> GenerateCardsResponse:
    """
    Generate flashcards using AI.
    
    Uses the specified AI provider to generate flashcards for a topic.
    
    **API Key Behavior:**
    - If `api_key` is provided, it will be used for the request.
    - If `api_key` is empty and user role is 'pro' or 'admin', 
      the server-side API key from environment variables will be used.
    - If `api_key` is empty and user role is 'user', returns 403 Forbidden.
    
    **Supported Providers:** openai, anthropic, google, xai
    
    **Cost Tracking:**
    - Response includes token usage (input_tokens, output_tokens, total_tokens)
    - Response includes cost_usd with 6 decimal precision
    - If token data is unavailable, these fields will be null
    """
    try:
        # Get user role from JWT
        user_role = current_user["role"]
        
        # Resolve API key (user-provided or server-side for pro/admin)
        api_key = await resolve_api_key(
            provider=request.provider,
            provided_key=request.api_key,
            user_role=user_role
        )
        
        # Build prompts
        system_prompt = f"{request.deck_prompt}\n{CARD_FORMAT_PROMPT}"
        user_message = f"Generate flashcards for this topic based on the instructions.\n\n#Topic: \n{request.topic_name}"
        
        # Generate cards with token tracking
        cards, input_tokens, output_tokens, cost_usd = await generate_cards_with_ai(
            provider=request.provider,
            model=request.model,
            api_key=api_key,
            system_prompt=system_prompt,
            user_message=user_message
        )
        
        # Convert to response model
        generated_cards = []
        for card in cards:
            generated_cards.append(
                GeneratedCard(
                    card_type=card.get("card_type", "qa_hint"),
                    question=card.get("question", ""),
                    answer=card.get("answer"),
                    hint=card.get("hint", ""),
                    choices=card.get("choices"),
                    correct_index=card.get("correct_index"),
                    explanation=card.get("explanation", "")
                )
            )
        
        # Calculate total tokens
        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        
        return GenerateCardsResponse(
            cards=generated_cards,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate cards: {str(e)}"
        )
