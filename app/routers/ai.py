"""
AI router for card generation endpoints.
Provides endpoints for AI-powered flashcard generation using various providers.
"""
import os

from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client, Client

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


def get_admin_client() -> Client:
    """Get Supabase admin client with service role key."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_service_key:
        raise HTTPException(
            status_code=500,
            detail="Supabase admin credentials not configured"
        )
    
    return create_client(supabase_url, supabase_service_key)


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
    
    **Credits System:**
    - User must have credits > 0.0 to generate cards
    - Credits are automatically deducted based on actual cost after generation
    - Response includes remaining_credits after deduction
    
    **Supported Providers:** openai, anthropic, google, xai
    
    **Cost Tracking:**
    - Response includes token usage (input_tokens, output_tokens, total_tokens)
    - Response includes cost_usd with 6 decimal precision
    - If token data is unavailable, these fields will be null
    """
    try:
        # Get user info from JWT
        user_id = current_user["user_id"]
        user_role = current_user["role"]
        user_credits = current_user["credits"]
        user_total_spent = current_user["total_spent"]
        
        # Check if user has sufficient credits
        if user_credits <= 0.0:
            raise HTTPException(
                status_code=402,
                detail="Insufficient credits. Please contact an administrator to add credits to your account."
            )
        
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
        
        # Deduct credits if cost is available
        remaining_credits = user_credits
        if cost_usd is not None and cost_usd > 0:
            # Calculate new credits and total_spent (rounded to 6 decimals)
            remaining_credits = round(user_credits - cost_usd, 6)
            new_total_spent = round(user_total_spent + cost_usd, 6)
            
            # Update user_metadata with new credits and total_spent
            try:
                admin_client = get_admin_client()
                admin_client.auth.admin.update_user_by_id(
                    user_id,
                    {
                        "user_metadata": {
                            "credits": remaining_credits,
                            "total_spent": new_total_spent
                        }
                    }
                )
            except Exception as e:
                print(f"Warning: Failed to deduct credits: {str(e)}")
                # Continue with response even if credit deduction fails
        
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
            cost_usd=cost_usd,
            remaining_credits=remaining_credits
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate cards: {str(e)}"
        )
