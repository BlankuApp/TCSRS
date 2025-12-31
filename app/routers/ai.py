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
from app.dependencies.auth import get_current_user, get_jwt_token
from app.models.schemas import (
    AIModel,
    AIProviderInfo,
    AIProvidersResponse,
    GenerateCardsRequest,
    GenerateCardsResponse,
    GeneratedCard,
)
from app.services.ai_service import generate_cards_with_ai, resolve_api_key
from app.services.database import get_user_scoped_client

router = APIRouter(prefix="/ai", tags=["ai"])


async def get_user_role(user_id: str, jwt_token: str) -> str:
    """
    Fetch user role from user_profiles table.
    Returns 'user' as default if profile not found.
    """
    try:
        db = get_user_scoped_client(jwt_token)
        response = db.table("user_profiles").select("role").eq("user_id", user_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0].get("role", "user")
        return "user"
    except Exception:
        return "user"


@router.get("/providers", response_model=AIProvidersResponse)
async def get_providers(
    current_user: str = Depends(get_current_user)
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
    current_user: str = Depends(get_current_user),
    jwt_token: str = Depends(get_jwt_token)
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
    """
    try:
        # Get user role to determine API key resolution
        user_role = await get_user_role(current_user, jwt_token)
        
        # Resolve API key (user-provided or server-side for pro/admin)
        api_key = await resolve_api_key(
            provider=request.provider,
            provided_key=request.api_key,
            user_role=user_role
        )
        
        # Build prompts
        system_prompt = f"{request.deck_prompt}\n{CARD_FORMAT_PROMPT}"
        user_message = f"Generate flashcards for this topic based on the instructions.\n\n#Topic: \n{request.topic_name}"
        
        # Generate cards
        cards = await generate_cards_with_ai(
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
        
        return GenerateCardsResponse(cards=generated_cards)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate cards: {str(e)}"
        )
