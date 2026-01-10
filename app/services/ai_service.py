"""
AI Service module for calling various AI providers to generate flashcards.
Supports OpenAI, Anthropic, Google, and xAI providers.
"""
import json
import os
from typing import Tuple, Optional


import httpx
from fastapi import HTTPException

from app.config import get_provider_env_key, get_provider_display_name, get_model_cost


async def call_openai(
    system_prompt: str,
    user_message: str,
    model: str,
    api_key: str
) -> Tuple[str, int, int]:
    """Call OpenAI API to generate content. Returns (content, input_tokens, output_tokens)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=700.0,
        )

        if response.status_code == 401:
            raise HTTPException(
                status_code=400,
                detail="Invalid OpenAI API key. Please check your API key and try again."
            )
        
        if not response.is_success:
            error_data = response.json()
            message = error_data.get("error", {}).get("message", "OpenAI API error")
            raise HTTPException(status_code=400, detail=message)

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            raise HTTPException(status_code=500, detail="No response from OpenAI")
        
        # Extract token usage
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        return content, input_tokens, output_tokens


async def call_anthropic(
    system_prompt: str,
    user_message: str,
    model: str,
    api_key: str
) -> Tuple[str, int, int]:
    """Call Anthropic API to generate content. Returns (content, input_tokens, output_tokens)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_message},
                ],
            },
            timeout=60.0,
        )

        if response.status_code == 401:
            raise HTTPException(
                status_code=400,
                detail="Invalid Anthropic API key. Please check your API key and try again."
            )
        
        if not response.is_success:
            error_data = response.json()
            message = error_data.get("error", {}).get("message", "Anthropic API error")
            raise HTTPException(status_code=400, detail=message)

        data = response.json()
        content_list = data.get("content", [])
        content = ""
        for item in content_list:
            if item.get("type") == "text":
                content = item.get("text", "")
                break
        
        if not content:
            raise HTTPException(status_code=500, detail="No text response from Anthropic")
        
        # Extract token usage
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        
        return content, input_tokens, output_tokens


async def call_google(
    system_prompt: str,
    user_message: str,
    model: str,
    api_key: str
) -> Tuple[str, int, int]:
    """Call Google AI API to generate content. Returns (content, input_tokens, output_tokens)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": f"{system_prompt}\n\n{user_message}"},
                        ],
                    },
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                },
            },
            timeout=60.0,
        )

        if response.status_code in (400, 403):
            error_data = response.json()
            message = error_data.get("error", {}).get("message", "Google AI API error")
            if "API key" in message or response.status_code == 403:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid Google AI API key. Please check your API key and try again."
                )
            raise HTTPException(status_code=400, detail=message)
        
        if not response.is_success:
            error_data = response.json()
            message = error_data.get("error", {}).get("message", "Google AI API error")
            raise HTTPException(status_code=400, detail=message)

        data = response.json()
        content = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text")
        )
        if not content:
            raise HTTPException(status_code=500, detail="No response from Google AI")
        
        # Extract token usage
        usage_metadata = data.get("usageMetadata", {})
        input_tokens = usage_metadata.get("promptTokenCount", 0)
        output_tokens = usage_metadata.get("candidatesTokenCount", 0)
        
        return content, input_tokens, output_tokens


async def call_xai(
    system_prompt: str,
    user_message: str,
    model: str,
    api_key: str
) -> Tuple[str, int, int]:
    """Call xAI API to generate content. Returns (content, input_tokens, output_tokens)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=60.0,
        )

        if response.status_code == 401:
            raise HTTPException(
                status_code=400,
                detail="Invalid xAI API key. Please check your API key and try again."
            )
        
        if not response.is_success:
            error_data = response.json()
            message = error_data.get("error", {}).get("message", "xAI API error")
            raise HTTPException(status_code=400, detail=message)

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            raise HTTPException(status_code=500, detail="No response from xAI")
        
        # Extract token usage
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        return content, input_tokens, output_tokens


async def resolve_api_key(
    provider: str,
    provided_key: str,
    user_role: str
) -> str:
    """
    Resolve API key for a provider.
    
    - If provided_key is non-empty, use it directly.
    - If provided_key is empty and user is 'pro' or 'admin', use server-side env var.
    - Otherwise, raise 403 Forbidden.
    """
    if provided_key and provided_key.strip():
        return provided_key.strip()
    
    # Check if user can use server-side keys
    if user_role not in ("pro", "admin"):
        raise HTTPException(
            status_code=403,
            detail="API key is required. Pro or Admin subscription required for server-side AI keys."
        )
    
    # Get server-side key from environment
    env_key_name = get_provider_env_key(provider)
    if not env_key_name:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {provider}"
        )
    
    server_key = os.getenv(env_key_name)
    if not server_key:
        provider_name = get_provider_display_name(provider)
        raise HTTPException(
            status_code=500,
            detail=f"Server-side {provider_name} API key not configured. Please provide your own API key."
        )
    
    return server_key


def calculate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """
    Calculate the total cost of a generation request.
    
    Args:
        provider: Provider identifier
        model: Model identifier
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
    
    Returns:
        Total cost in USD with 6 decimal precision, or None if pricing not available
    """
    costs = get_model_cost(provider, model)
    if not costs:
        return None
    
    cost_per_input, cost_per_output = costs
    if cost_per_input is None or cost_per_output is None:
        return None
    
    # Costs are in USD per 1M tokens
    total_cost = (input_tokens * cost_per_input / 1_000_000) + (output_tokens * cost_per_output / 1_000_000)
    
    # Round to 6 decimal places
    return round(total_cost, 6)


def parse_ai_response(content: str, provider_name: str) -> dict:
    """
    Parse JSON response from AI, handling markdown code blocks if present.
    Returns parsed dict with 'cards' array.
    """
    json_content = content.strip()
    
    # Handle markdown code blocks
    if json_content.startswith("```json"):
        json_content = json_content[7:]
    elif json_content.startswith("```"):
        json_content = json_content[3:]
    
    if json_content.endswith("```"):
        json_content = json_content[:-3]
    
    json_content = json_content.strip()
    
    try:
        parsed = json.loads(json_content)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON response from {provider_name}: {str(e)}"
        )
    
    if not isinstance(parsed.get("cards"), list):
        raise HTTPException(
            status_code=500,
            detail=f"Invalid response format from {provider_name}: expected 'cards' array"
        )
    
    return parsed


# Provider dispatcher
PROVIDER_FUNCTIONS = {
    "openai": call_openai,
    "anthropic": call_anthropic,
    "google": call_google,
    "xai": call_xai,
}


async def generate_cards_with_ai(
    provider: str,
    model: str,
    api_key: str,
    system_prompt: str,
    user_message: str
) -> Tuple[list, Optional[int], Optional[int], Optional[float]]:
    """
    Generate cards using the specified AI provider.
    
    Returns:
        Tuple of (cards_list, input_tokens, output_tokens, cost_usd)
        Token counts and cost may be None if not available.
    """
    provider_name = get_provider_display_name(provider)
    
    if provider not in PROVIDER_FUNCTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: {provider}"
        )
    
    call_fn = PROVIDER_FUNCTIONS[provider]
    content, input_tokens, output_tokens = await call_fn(system_prompt, user_message, model, api_key)
    
    if not content:
        raise HTTPException(
            status_code=500,
            detail=f"No response from {provider_name}"
        )
    
    parsed = parse_ai_response(content, provider_name)
    
    # Calculate cost
    cost_usd = None
    if input_tokens and output_tokens:
        cost_usd = calculate_cost(provider, model, input_tokens, output_tokens)
    
    return parsed["cards"], input_tokens, output_tokens, cost_usd
